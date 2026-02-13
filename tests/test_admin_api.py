"""
Integration tests for Admin API routes (Phase 5).

Tests the full admin API workflow:
1. Admin creates a tenant
2. Admin retrieves and lists tenants
3. Admin updates tenant configuration
4. Admin manages scoring configuration
5. Tenant views own scoring config (self-service)
6. Admin views tenant statistics
7. Admin deletes tenant

All tests run without a live Keycloak, PostgreSQL, Redis, or Qdrant
by using dependency overrides and mock services.
"""

import sys
import types
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Pre-mock heavy ML modules to avoid ImportError in CI/test environments
# that do not have torch/transformers installed.
_MOCK_MODULES = [
    "torch", "torch.nn", "torch.nn.functional",
    "torch.cuda", "torch.utils", "torch.utils.data",
    "transformers",
    "sentence_transformers",
    "numpy", "numpy.linalg",
    "scipy", "scipy.spatial", "scipy.spatial.distance",
    "qdrant_client", "qdrant_client.http", "qdrant_client.http.models",
    "qdrant_client.models",
]
for _mod_name in _MOCK_MODULES:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = MagicMock()

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.auth.keycloak import get_token_payload, get_current_tenant_id
from src.api.dependencies import get_db_session
from tests.utils.auth_helpers import override_auth, override_tenant


# ---------------------------------------------------------------------------
# Mock ORM models (simulate SQLAlchemy model instances)
# ---------------------------------------------------------------------------

class MockTenant:
    """Simulates a Tenant ORM instance."""

    def __init__(
        self,
        tenant_id: str = "acme-corp",
        name: str = "Acme Corporation",
        domain: str = "e-commerce",
        keycloak_client_id: str = "acme-client",
        qdrant_collection_name: str = "tenant_acme-corp",
        rate_limit_requests: int = 100,
        rate_limit_window_seconds: int = 60,
        is_active: bool = True,
    ):
        self.id = uuid.uuid4()
        self.tenant_id = tenant_id
        self.name = name
        self.domain = domain
        self.keycloak_client_id = keycloak_client_id
        self.qdrant_collection_name = qdrant_collection_name
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window_seconds = rate_limit_window_seconds
        self.is_active = is_active
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


class MockScoringConfig:
    """Simulates a ScoringConfig ORM instance."""

    def __init__(
        self,
        tenant_id: str = "acme-corp",
        version: int = 1,
        is_active: bool = True,
        scoring_criteria: Optional[list] = None,
        created_by: str = "admin",
    ):
        self.id = uuid.uuid4()
        self.tenant_id = tenant_id
        self.scoring_criteria = scoring_criteria or [
            {"name": "similarity", "weight": 0.7, "type": "system"},
            {"name": "price_match", "weight": 0.2, "type": "custom"},
            {"name": "location_proximity", "weight": 0.1, "type": "custom"},
        ]
        self.version = version
        self.is_active = is_active
        self.created_at = datetime.now(timezone.utc)
        self.created_by = created_by


# ---------------------------------------------------------------------------
# App factory with dependency overrides
# ---------------------------------------------------------------------------

def _create_test_app() -> FastAPI:
    """Create the real app and apply dependency overrides."""
    from src.api.routes.tenants import router as tenants_router
    from src.api.routes.scoring import router as scoring_router

    app = FastAPI()
    app.include_router(tenants_router)
    app.include_router(scoring_router)

    # Override DB session with a no-op mock
    async def _mock_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = _mock_db

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """Create a fresh test app for each test."""
    return _create_test_app()


@pytest.fixture
def admin_client(app):
    """Test client authenticated as an admin."""
    app.dependency_overrides[get_token_payload] = override_auth(
        tenant_id="platform-admin",
        roles=["admin", "user"],
        sub="admin-user-1",
    )
    return TestClient(app)


@pytest.fixture
def tenant_client(app):
    """Test client authenticated as a regular tenant (no admin role)."""
    app.dependency_overrides[get_token_payload] = override_auth(
        tenant_id="acme-corp",
        roles=["user"],
        sub="tenant-user-1",
    )
    return TestClient(app)


@pytest.fixture
def unauthenticated_client(app):
    """Test client with no authentication."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Tenant CRUD tests
# ---------------------------------------------------------------------------

class TestTenantCreate:
    """Tests for POST /admin/tenants/"""

    @patch("src.api.routes.tenants.TenantService")
    def test_create_tenant_success(self, mock_service_cls, admin_client):
        """Admin can create a new tenant."""
        mock_tenant = MockTenant()
        mock_service = AsyncMock()
        mock_service.create_tenant.return_value = mock_tenant
        mock_service_cls.return_value = mock_service

        response = admin_client.post(
            "/admin/tenants/",
            json={
                "tenant_id": "acme-corp",
                "name": "Acme Corporation",
                "domain": "e-commerce",
                "rate_limit_requests": 100,
                "rate_limit_window_seconds": 60,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tenant_id"] == "acme-corp"
        assert data["name"] == "Acme Corporation"
        assert data["is_active"] is True
        mock_service.create_tenant.assert_called_once()

    @patch("src.api.routes.tenants.TenantService")
    def test_create_tenant_duplicate(self, mock_service_cls, admin_client):
        """Creating a tenant with duplicate tenant_id returns 409."""
        mock_service = AsyncMock()
        mock_service.create_tenant.side_effect = ValueError(
            "Tenant with tenant_id 'acme-corp' already exists"
        )
        mock_service_cls.return_value = mock_service

        response = admin_client.post(
            "/admin/tenants/",
            json={
                "tenant_id": "acme-corp",
                "name": "Acme Corporation",
            },
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_tenant_no_auth(self, unauthenticated_client):
        """Unauthenticated requests are rejected."""
        response = unauthenticated_client.post(
            "/admin/tenants/",
            json={"tenant_id": "test", "name": "Test"},
        )
        assert response.status_code in (401, 403)

    @patch("src.api.routes.tenants.TenantService")
    def test_create_tenant_non_admin_rejected(self, mock_service_cls, app):
        """Non-admin users cannot create tenants."""
        app.dependency_overrides[get_token_payload] = override_auth(
            tenant_id="acme", roles=["user"]
        )
        client = TestClient(app)

        response = client.post(
            "/admin/tenants/",
            json={"tenant_id": "test", "name": "Test"},
        )
        assert response.status_code == 403

    def test_create_tenant_validation_error(self, admin_client):
        """Missing required fields return 422."""
        response = admin_client.post(
            "/admin/tenants/",
            json={"name": "Missing tenant_id"},
        )
        assert response.status_code == 422


class TestTenantList:
    """Tests for GET /admin/tenants/"""

    @patch("src.api.routes.tenants.TenantService")
    def test_list_tenants(self, mock_service_cls, admin_client):
        """Admin can list tenants."""
        tenants = [MockTenant(tenant_id="t1", name="Tenant 1"),
                    MockTenant(tenant_id="t2", name="Tenant 2")]
        mock_service = AsyncMock()
        mock_service.list_tenants.return_value = (tenants, 2)
        mock_service_cls.return_value = mock_service

        response = admin_client.get("/admin/tenants/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["tenants"]) == 2
        assert data["skip"] == 0
        assert data["limit"] == 100

    @patch("src.api.routes.tenants.TenantService")
    def test_list_tenants_with_pagination(self, mock_service_cls, admin_client):
        """Admin can paginate tenant list."""
        mock_service = AsyncMock()
        mock_service.list_tenants.return_value = ([], 0)
        mock_service_cls.return_value = mock_service

        response = admin_client.get("/admin/tenants/?skip=10&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 10
        assert data["limit"] == 5

    @patch("src.api.routes.tenants.TenantService")
    def test_list_tenants_filter_active(self, mock_service_cls, admin_client):
        """Admin can filter by active status."""
        mock_service = AsyncMock()
        mock_service.list_tenants.return_value = ([], 0)
        mock_service_cls.return_value = mock_service

        response = admin_client.get("/admin/tenants/?is_active=true")
        assert response.status_code == 200


class TestTenantGet:
    """Tests for GET /admin/tenants/{tenant_id}"""

    @patch("src.api.routes.tenants.TenantService")
    def test_get_tenant(self, mock_service_cls, admin_client):
        """Admin can get tenant details."""
        mock_tenant = MockTenant()
        mock_service = AsyncMock()
        mock_service.get_tenant.return_value = mock_tenant
        mock_service_cls.return_value = mock_service

        response = admin_client.get("/admin/tenants/acme-corp")

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "acme-corp"
        assert data["name"] == "Acme Corporation"

    @patch("src.api.routes.tenants.TenantService")
    def test_get_tenant_not_found(self, mock_service_cls, admin_client):
        """Requesting non-existent tenant returns 404."""
        mock_service = AsyncMock()
        mock_service.get_tenant.side_effect = ValueError("Not found")
        mock_service_cls.return_value = mock_service

        response = admin_client.get("/admin/tenants/nonexistent")
        assert response.status_code == 404


class TestTenantUpdate:
    """Tests for PATCH /admin/tenants/{tenant_id}"""

    @patch("src.api.routes.tenants.TenantService")
    def test_update_tenant(self, mock_service_cls, admin_client):
        """Admin can update tenant configuration."""
        updated = MockTenant(name="Acme Corp Updated")
        mock_service = AsyncMock()
        mock_service.update_tenant.return_value = updated
        mock_service_cls.return_value = mock_service

        response = admin_client.patch(
            "/admin/tenants/acme-corp",
            json={"name": "Acme Corp Updated"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Acme Corp Updated"

    @patch("src.api.routes.tenants.TenantService")
    def test_update_tenant_deactivate(self, mock_service_cls, admin_client):
        """Admin can deactivate a tenant."""
        deactivated = MockTenant(is_active=False)
        mock_service = AsyncMock()
        mock_service.update_tenant.return_value = deactivated
        mock_service_cls.return_value = mock_service

        response = admin_client.patch(
            "/admin/tenants/acme-corp",
            json={"is_active": False},
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @patch("src.api.routes.tenants.TenantService")
    def test_update_tenant_not_found(self, mock_service_cls, admin_client):
        """Updating non-existent tenant returns 404."""
        mock_service = AsyncMock()
        mock_service.update_tenant.side_effect = ValueError("Not found")
        mock_service_cls.return_value = mock_service

        response = admin_client.patch(
            "/admin/tenants/nonexistent",
            json={"name": "Updated"},
        )
        assert response.status_code == 404


class TestTenantDelete:
    """Tests for DELETE /admin/tenants/{tenant_id}"""

    @patch("src.api.routes.tenants.TenantService")
    def test_delete_tenant(self, mock_service_cls, admin_client):
        """Admin can delete a tenant."""
        mock_service = AsyncMock()
        mock_service.delete_tenant.return_value = True
        mock_service_cls.return_value = mock_service

        response = admin_client.delete("/admin/tenants/acme-corp")
        assert response.status_code == 204

    @patch("src.api.routes.tenants.TenantService")
    def test_delete_tenant_not_found(self, mock_service_cls, admin_client):
        """Deleting non-existent tenant returns 404."""
        mock_service = AsyncMock()
        mock_service.delete_tenant.side_effect = ValueError("Not found")
        mock_service_cls.return_value = mock_service

        response = admin_client.delete("/admin/tenants/nonexistent")
        assert response.status_code == 404


class TestTenantStats:
    """Tests for GET /admin/tenants/{tenant_id}/stats"""

    @patch("src.api.routes.tenants.TenantService")
    def test_get_tenant_stats(self, mock_service_cls, admin_client, app):
        """Admin can get tenant statistics."""
        mock_tenant = MockTenant()
        mock_service = AsyncMock()
        mock_service.get_tenant.return_value = mock_tenant
        mock_service_cls.return_value = mock_service

        # Mock the DB queries for product count and scoring version
        mock_db = AsyncMock()
        mock_product_count = MagicMock()
        mock_product_count.scalar_one.return_value = 42
        mock_scoring_version = MagicMock()
        mock_scoring_version.scalar_one_or_none.return_value = 3

        mock_db.execute = AsyncMock(
            side_effect=[mock_product_count, mock_scoring_version]
        )

        async def _mock_db():
            yield mock_db

        app.dependency_overrides[get_db_session] = _mock_db

        with patch(
            "src.modules.module2_recommendation.vector_store.get_vector_store"
        ) as mock_vs:
            mock_vs.return_value.get_collection_stats.return_value = {
                "vectors_count": 100,
            }

            response = admin_client.get("/admin/tenants/acme-corp/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "acme-corp"
        assert data["total_products"] == 42
        assert data["active_scoring_version"] == 3
        assert data["is_active"] is True


# ---------------------------------------------------------------------------
# 2. Scoring Config tests (admin routes)
# ---------------------------------------------------------------------------

class TestScoringConfigAdmin:
    """Tests for admin scoring configuration management."""

    @patch("src.api.routes.scoring.ScoringConfigService")
    @patch("src.api.routes.scoring.TenantService")
    def test_get_tenant_scoring_config(
        self, mock_tenant_cls, mock_scoring_cls, admin_client
    ):
        """Admin can get a tenant's active scoring config."""
        mock_tenant_svc = AsyncMock()
        mock_tenant_svc.get_tenant.return_value = MockTenant()
        mock_tenant_cls.return_value = mock_tenant_svc

        mock_config = MockScoringConfig()
        mock_scoring_svc = AsyncMock()
        mock_scoring_svc.get_active_config.return_value = mock_config
        mock_scoring_cls.return_value = mock_scoring_svc

        response = admin_client.get(
            "/admin/scoring/tenants/acme-corp/config"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "acme-corp"
        assert data["version"] == 1
        assert data["is_active"] is True
        assert len(data["scoring_criteria"]) == 3

    @patch("src.api.routes.scoring.ScoringConfigService")
    @patch("src.api.routes.scoring.TenantService")
    def test_get_scoring_config_not_found(
        self, mock_tenant_cls, mock_scoring_cls, admin_client
    ):
        """Returns 404 when no active scoring config exists."""
        mock_tenant_svc = AsyncMock()
        mock_tenant_svc.get_tenant.return_value = MockTenant()
        mock_tenant_cls.return_value = mock_tenant_svc

        mock_scoring_svc = AsyncMock()
        mock_scoring_svc.get_active_config.return_value = None
        mock_scoring_cls.return_value = mock_scoring_svc

        response = admin_client.get(
            "/admin/scoring/tenants/acme-corp/config"
        )
        assert response.status_code == 404

    @patch("src.api.routes.scoring.ScoringConfigService")
    @patch("src.api.routes.scoring.TenantService")
    def test_update_tenant_scoring_config(
        self, mock_tenant_cls, mock_scoring_cls, admin_client
    ):
        """Admin can update a tenant's scoring config."""
        mock_tenant_svc = AsyncMock()
        mock_tenant_svc.get_tenant.return_value = MockTenant()
        mock_tenant_cls.return_value = mock_tenant_svc

        updated_config = MockScoringConfig(
            version=2,
            scoring_criteria=[
                {"name": "similarity", "weight": 0.5, "type": "system"},
                {"name": "price_match", "weight": 0.3, "type": "custom"},
                {"name": "freshness", "weight": 0.2, "type": "custom"},
            ],
        )
        mock_scoring_svc = AsyncMock()
        mock_scoring_svc.update_config.return_value = updated_config
        mock_scoring_cls.return_value = mock_scoring_svc

        response = admin_client.put(
            "/admin/scoring/tenants/acme-corp/config",
            json={
                "criteria": [
                    {"name": "similarity", "weight": 0.5, "type": "system"},
                    {"name": "price_match", "weight": 0.3, "type": "custom"},
                    {"name": "freshness", "weight": 0.2, "type": "custom"},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == 2
        assert len(data["scoring_criteria"]) == 3
        mock_scoring_svc.update_config.assert_called_once()

    @patch("src.api.routes.scoring.ScoringConfigService")
    @patch("src.api.routes.scoring.TenantService")
    def test_update_scoring_config_invalid_weights(
        self, mock_tenant_cls, mock_scoring_cls, admin_client
    ):
        """Scoring criteria weights that don't sum to 1.0 are rejected."""
        response = admin_client.put(
            "/admin/scoring/tenants/acme-corp/config",
            json={
                "criteria": [
                    {"name": "similarity", "weight": 0.5, "type": "system"},
                    {"name": "price_match", "weight": 0.1, "type": "custom"},
                ],
            },
        )

        # Pydantic validation should catch this before reaching the service
        assert response.status_code == 422

    @patch("src.api.routes.scoring.ScoringConfigService")
    @patch("src.api.routes.scoring.TenantService")
    def test_scoring_config_tenant_not_found(
        self, mock_tenant_cls, mock_scoring_cls, admin_client
    ):
        """Returns 404 when tenant does not exist."""
        mock_tenant_svc = AsyncMock()
        mock_tenant_svc.get_tenant.side_effect = ValueError("Not found")
        mock_tenant_cls.return_value = mock_tenant_svc

        response = admin_client.get(
            "/admin/scoring/tenants/nonexistent/config"
        )
        assert response.status_code == 404

    @patch("src.api.routes.scoring.ScoringConfigService")
    @patch("src.api.routes.scoring.TenantService")
    def test_get_scoring_config_history(
        self, mock_tenant_cls, mock_scoring_cls, admin_client
    ):
        """Admin can get scoring config version history."""
        mock_tenant_svc = AsyncMock()
        mock_tenant_svc.get_tenant.return_value = MockTenant()
        mock_tenant_cls.return_value = mock_tenant_svc

        configs = [
            MockScoringConfig(version=3, is_active=True),
            MockScoringConfig(version=2, is_active=False),
            MockScoringConfig(version=1, is_active=False),
        ]
        mock_scoring_svc = AsyncMock()
        mock_scoring_svc.get_config_history.return_value = configs
        mock_scoring_cls.return_value = mock_scoring_svc

        response = admin_client.get(
            "/admin/scoring/tenants/acme-corp/config/history"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["version"] == 3
        assert data[0]["is_active"] is True
        assert data[1]["is_active"] is False


# ---------------------------------------------------------------------------
# 3. Scoring Config tests (tenant self-service)
# ---------------------------------------------------------------------------

class TestScoringConfigSelfService:
    """Tests for tenant self-service scoring configuration."""

    @patch("src.api.routes.scoring.ScoringConfigService")
    def test_tenant_get_own_config(self, mock_scoring_cls, app, tenant_client):
        """Authenticated tenant can view their own scoring config."""
        mock_config = MockScoringConfig(tenant_id="acme-corp")
        mock_scoring_svc = AsyncMock()
        mock_scoring_svc.get_active_config.return_value = mock_config
        mock_scoring_cls.return_value = mock_scoring_svc

        response = tenant_client.get("/admin/scoring/config")

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "acme-corp"
        assert data["is_active"] is True

    @patch("src.api.routes.scoring.ScoringConfigService")
    def test_tenant_get_config_not_found(self, mock_scoring_cls, app, tenant_client):
        """Returns 404 when tenant has no active config."""
        mock_scoring_svc = AsyncMock()
        mock_scoring_svc.get_active_config.return_value = None
        mock_scoring_cls.return_value = mock_scoring_svc

        response = tenant_client.get("/admin/scoring/config")
        assert response.status_code == 404

    @patch("src.api.routes.scoring.ScoringConfigService")
    def test_tenant_update_own_config(self, mock_scoring_cls, app, tenant_client):
        """Authenticated tenant can update their own scoring config."""
        updated_config = MockScoringConfig(
            tenant_id="acme-corp",
            version=2,
        )
        mock_scoring_svc = AsyncMock()
        mock_scoring_svc.update_config.return_value = updated_config
        mock_scoring_cls.return_value = mock_scoring_svc

        response = tenant_client.put(
            "/admin/scoring/config",
            json={
                "criteria": [
                    {"name": "similarity", "weight": 0.6, "type": "system"},
                    {"name": "freshness", "weight": 0.4, "type": "custom"},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == 2


# ---------------------------------------------------------------------------
# 4. End-to-end workflow test
# ---------------------------------------------------------------------------

class TestAdminWorkflow:
    """End-to-end workflow simulating the full admin lifecycle."""

    @patch("src.api.routes.tenants.TenantService")
    @patch("src.api.routes.scoring.ScoringConfigService")
    @patch("src.api.routes.scoring.TenantService")
    def test_full_lifecycle(
        self,
        mock_scoring_tenant_cls,
        mock_scoring_cls,
        mock_tenant_cls,
        admin_client,
    ):
        """
        Simulates the full admin workflow:
        1. Admin creates tenant
        2. Admin updates scoring config
        3. Admin views tenant stats
        4. Admin deletes tenant
        """
        # --- Step 1: Create tenant ---
        mock_tenant = MockTenant()
        mock_tenant_svc = AsyncMock()
        mock_tenant_svc.create_tenant.return_value = mock_tenant
        mock_tenant_cls.return_value = mock_tenant_svc

        response = admin_client.post(
            "/admin/tenants/",
            json={
                "tenant_id": "acme-corp",
                "name": "Acme Corporation",
                "domain": "e-commerce",
            },
        )
        assert response.status_code == 201

        # --- Step 2: Update scoring config ---
        mock_scoring_tenant_svc = AsyncMock()
        mock_scoring_tenant_svc.get_tenant.return_value = mock_tenant
        mock_scoring_tenant_cls.return_value = mock_scoring_tenant_svc

        updated_config = MockScoringConfig(version=2)
        mock_scoring_svc = AsyncMock()
        mock_scoring_svc.update_config.return_value = updated_config
        mock_scoring_cls.return_value = mock_scoring_svc

        response = admin_client.put(
            "/admin/scoring/tenants/acme-corp/config",
            json={
                "criteria": [
                    {"name": "similarity", "weight": 0.5, "type": "system"},
                    {"name": "price_match", "weight": 0.3, "type": "custom"},
                    {"name": "freshness", "weight": 0.2, "type": "custom"},
                ],
            },
        )
        assert response.status_code == 200
        assert response.json()["version"] == 2

        # --- Step 3: Delete tenant ---
        mock_tenant_svc.delete_tenant.return_value = True
        mock_tenant_cls.return_value = mock_tenant_svc

        response = admin_client.delete("/admin/tenants/acme-corp")
        assert response.status_code == 204


# ---------------------------------------------------------------------------
# 5. Authorization enforcement tests
# ---------------------------------------------------------------------------

class TestAuthorizationEnforcement:
    """Verify that admin routes reject non-admin users."""

    def test_list_tenants_requires_admin(self, app):
        """Non-admin user cannot list tenants."""
        app.dependency_overrides[get_token_payload] = override_auth(
            tenant_id="acme", roles=["user"]
        )
        client = TestClient(app)

        response = client.get("/admin/tenants/")
        assert response.status_code == 403

    def test_delete_tenant_requires_admin(self, app):
        """Non-admin user cannot delete tenants."""
        app.dependency_overrides[get_token_payload] = override_auth(
            tenant_id="acme", roles=["user"]
        )
        client = TestClient(app)

        response = client.delete("/admin/tenants/acme-corp")
        assert response.status_code == 403

    def test_admin_scoring_config_requires_admin(self, app):
        """Non-admin user cannot access admin scoring routes."""
        app.dependency_overrides[get_token_payload] = override_auth(
            tenant_id="acme", roles=["user"]
        )
        client = TestClient(app)

        response = client.get("/admin/scoring/tenants/acme-corp/config")
        assert response.status_code == 403

    def test_scoring_history_requires_admin(self, app):
        """Non-admin user cannot access scoring history."""
        app.dependency_overrides[get_token_payload] = override_auth(
            tenant_id="acme", roles=["user"]
        )
        client = TestClient(app)

        response = client.get(
            "/admin/scoring/tenants/acme-corp/config/history"
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# 6. Input validation tests
# ---------------------------------------------------------------------------

class TestInputValidation:
    """Test request validation for admin endpoints."""

    def test_create_tenant_empty_name(self, admin_client):
        """Empty tenant name is rejected."""
        response = admin_client.post(
            "/admin/tenants/",
            json={"tenant_id": "test", "name": ""},
        )
        assert response.status_code == 422

    def test_create_tenant_name_too_long(self, admin_client):
        """Tenant name exceeding max length is rejected."""
        response = admin_client.post(
            "/admin/tenants/",
            json={"tenant_id": "test", "name": "x" * 300},
        )
        assert response.status_code == 422

    def test_scoring_config_empty_criteria(self, admin_client):
        """Empty criteria list is rejected."""
        response = admin_client.put(
            "/admin/scoring/tenants/acme-corp/config",
            json={"criteria": []},
        )
        assert response.status_code == 422

    def test_scoring_config_invalid_weight(self, admin_client):
        """Weight outside [0, 1] range is rejected."""
        response = admin_client.put(
            "/admin/scoring/tenants/acme-corp/config",
            json={
                "criteria": [
                    {"name": "similarity", "weight": 1.5, "type": "system"},
                ],
            },
        )
        assert response.status_code == 422

    def test_scoring_config_invalid_type(self, admin_client):
        """Invalid criterion type is rejected."""
        response = admin_client.put(
            "/admin/scoring/tenants/acme-corp/config",
            json={
                "criteria": [
                    {"name": "similarity", "weight": 1.0, "type": "invalid"},
                ],
            },
        )
        assert response.status_code == 422

    def test_create_tenant_negative_rate_limit(self, admin_client):
        """Negative rate limit value is rejected."""
        response = admin_client.post(
            "/admin/tenants/",
            json={
                "tenant_id": "test",
                "name": "Test",
                "rate_limit_requests": -1,
            },
        )
        assert response.status_code == 422
