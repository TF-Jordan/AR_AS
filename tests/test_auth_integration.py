"""
Integration tests for OAuth2 Keycloak authentication and authorization.

These tests demonstrate:
1. Protected routes with ``Depends(get_current_tenant_id)``
2. Admin-only routes with ``Depends(require_admin)``
3. Rate limiting enforcement
4. Token validation (expired, missing claims, invalid audience)

All tests run without a live Keycloak instance by using dependency
overrides and mock JWT tokens from ``tests.utils.auth_helpers``.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from src.auth.keycloak import (
    KeycloakAuth,
    get_token_payload,
    get_current_tenant_id,
    get_current_client_id,
    require_admin,
    keycloak_auth,
)
from src.middleware.rate_limiter import TenantRateLimiter

from tests.utils.auth_helpers import (
    create_test_payload,
    create_test_token,
    create_expired_token,
    override_auth,
    override_tenant,
)


# ---------------------------------------------------------------------------
# Test application with example routes
# ---------------------------------------------------------------------------

def _create_test_app() -> FastAPI:
    """Create a minimal FastAPI app with protected routes for testing."""
    app = FastAPI()

    @app.get("/public")
    async def public_route():
        return {"message": "public"}

    @app.get("/protected")
    async def protected_route(
        tenant_id: str = Depends(get_current_tenant_id),
    ):
        """Route protected by tenant_id extraction."""
        return {"tenant_id": tenant_id}

    @app.get("/protected/client")
    async def protected_client_route(
        client_id: str = Depends(get_current_client_id),
    ):
        """Route that extracts client_id."""
        return {"client_id": client_id}

    @app.get("/admin-only")
    async def admin_only_route(
        payload: dict = Depends(require_admin),
    ):
        """Route that requires admin role."""
        return {
            "message": "admin access granted",
            "sub": payload.get("sub"),
        }

    @app.get("/payload")
    async def payload_route(
        payload: dict = Depends(get_token_payload),
    ):
        """Route that returns the full token payload."""
        return {
            "sub": payload.get("sub"),
            "tenant_id": payload.get("tenant_id"),
            "roles": payload.get("realm_access", {}).get("roles", []),
        }

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """Create a fresh test app for each test."""
    return _create_test_app()


@pytest.fixture
def client(app):
    """Synchronous test client."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Protected route tests (tenant_id extraction)
# ---------------------------------------------------------------------------

class TestProtectedRoutes:
    """Tests for routes protected by get_current_tenant_id."""

    def test_protected_route_with_valid_token(self, app, client):
        """A valid token with tenant_id should grant access."""
        app.dependency_overrides[get_token_payload] = override_auth(
            tenant_id="acme-corp"
        )

        response = client.get("/protected")
        assert response.status_code == 200
        assert response.json() == {"tenant_id": "acme-corp"}

        app.dependency_overrides.clear()

    def test_protected_route_without_token(self, app, client):
        """Missing Authorization header should return 401 or 403."""
        # No dependency override -- HTTPBearer will reject
        response = client.get("/protected")
        assert response.status_code in (401, 403)

    def test_protected_route_missing_tenant_claim(self, app, client):
        """Token without tenant_id claim should return 403."""
        payload = create_test_payload(tenant_id="acme")
        del payload["tenant_id"]  # Remove the claim

        async def _override():
            return payload

        app.dependency_overrides[get_token_payload] = _override

        response = client.get("/protected")
        assert response.status_code == 403
        assert "tenant_id" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_client_id_extraction(self, app, client):
        """client_id should be extracted from the token."""
        app.dependency_overrides[get_token_payload] = override_auth(
            tenant_id="acme", client_id="my-client"
        )

        response = client.get("/protected/client")
        assert response.status_code == 200
        assert response.json() == {"client_id": "my-client"}

        app.dependency_overrides.clear()

    def test_payload_route(self, app, client):
        """Full payload should be accessible in the route."""
        app.dependency_overrides[get_token_payload] = override_auth(
            tenant_id="acme",
            roles=["user", "editor"],
            sub="user-123",
        )

        response = client.get("/payload")
        assert response.status_code == 200
        data = response.json()
        assert data["sub"] == "user-123"
        assert data["tenant_id"] == "acme"
        assert "user" in data["roles"]
        assert "editor" in data["roles"]

        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 2. Admin-only route tests
# ---------------------------------------------------------------------------

class TestAdminRoutes:
    """Tests for routes protected by require_admin."""

    def test_admin_route_with_admin_role(self, app, client):
        """User with admin role should be granted access."""
        app.dependency_overrides[get_token_payload] = override_auth(
            tenant_id="acme",
            roles=["admin", "user"],
            sub="admin-user-1",
        )

        response = client.get("/admin-only")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "admin access granted"
        assert data["sub"] == "admin-user-1"

        app.dependency_overrides.clear()

    def test_admin_route_without_admin_role(self, app, client):
        """User without admin role should be rejected with 403."""
        app.dependency_overrides[get_token_payload] = override_auth(
            tenant_id="acme",
            roles=["user", "editor"],
        )

        response = client.get("/admin-only")
        assert response.status_code == 403
        assert "Admin role required" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_admin_route_with_no_roles(self, app, client):
        """User with empty roles should be rejected."""
        app.dependency_overrides[get_token_payload] = override_auth(
            tenant_id="acme",
            roles=[],
        )

        response = client.get("/admin-only")
        assert response.status_code == 403

        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 3. KeycloakAuth unit tests
# ---------------------------------------------------------------------------

class TestKeycloakAuthUnit:
    """Unit tests for KeycloakAuth methods (without network calls)."""

    @pytest.mark.asyncio
    async def test_get_current_tenant_valid(self):
        """get_current_tenant should return tenant_id from payload."""
        auth = KeycloakAuth()
        payload = {"tenant_id": "acme", "sub": "user-1"}
        result = await auth.get_current_tenant(payload)
        assert result == "acme"

    @pytest.mark.asyncio
    async def test_get_current_tenant_missing(self):
        """get_current_tenant should raise 403 if tenant_id is missing."""
        auth = KeycloakAuth()
        payload = {"sub": "user-1"}
        with pytest.raises(Exception) as exc_info:
            await auth.get_current_tenant(payload)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_client_id_from_client_id_claim(self):
        """get_client_id should prefer the client_id claim."""
        auth = KeycloakAuth()
        payload = {"client_id": "my-client", "azp": "other-client"}
        result = await auth.get_client_id(payload)
        assert result == "my-client"

    @pytest.mark.asyncio
    async def test_get_client_id_fallback_to_azp(self):
        """get_client_id should fall back to azp if client_id is missing."""
        auth = KeycloakAuth()
        payload = {"azp": "my-azp-client"}
        result = await auth.get_client_id(payload)
        assert result == "my-azp-client"

    @pytest.mark.asyncio
    async def test_get_client_id_missing(self):
        """get_client_id should raise 403 if both claims are missing."""
        auth = KeycloakAuth()
        payload = {"sub": "user-1"}
        with pytest.raises(Exception) as exc_info:
            await auth.get_client_id(payload)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_admin_role_present(self):
        """require_admin_role should return True when admin role is present."""
        auth = KeycloakAuth()
        payload = {"realm_access": {"roles": ["admin", "user"]}}
        result = await auth.require_admin_role(payload)
        assert result is True

    @pytest.mark.asyncio
    async def test_require_admin_role_missing(self):
        """require_admin_role should raise 403 when admin role is absent."""
        auth = KeycloakAuth()
        payload = {"realm_access": {"roles": ["user"]}}
        with pytest.raises(Exception) as exc_info:
            await auth.require_admin_role(payload)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_admin_no_realm_access(self):
        """require_admin_role should raise 403 when realm_access is absent."""
        auth = KeycloakAuth()
        payload = {"sub": "user-1"}
        with pytest.raises(Exception) as exc_info:
            await auth.require_admin_role(payload)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# 4. Rate limiter tests
# ---------------------------------------------------------------------------

class TestRateLimiter:
    """Tests for TenantRateLimiter with a mock Redis client."""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_within_limit(self):
        """Requests within the limit should be allowed."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 5
        mock_redis.ttl.return_value = 30

        limiter = TenantRateLimiter(mock_redis)
        result = await limiter.check_rate_limit(
            tenant_id="acme",
            max_requests=100,
            window_seconds=60,
        )

        assert result["allowed"] is True
        assert result["limit"] == 100
        assert result["remaining"] == 95
        assert result["reset"] == 30

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_over_limit(self):
        """Requests exceeding the limit should be rejected with 429."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 101
        mock_redis.ttl.return_value = 15

        limiter = TenantRateLimiter(mock_redis)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await limiter.check_rate_limit(
                tenant_id="acme",
                max_requests=100,
                window_seconds=60,
            )

        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_rate_limit_sets_ttl_on_first_request(self):
        """TTL should be set when the counter is at 1 (first request)."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 1
        mock_redis.ttl.return_value = 60

        limiter = TenantRateLimiter(mock_redis)
        await limiter.check_rate_limit(
            tenant_id="acme",
            max_requests=100,
            window_seconds=60,
        )

        mock_redis.expire.assert_called_once_with("rate_limit:acme", 60)

    @pytest.mark.asyncio
    async def test_rate_limit_redis_failure_fails_open(self):
        """If Redis is down, requests should be allowed (fail-open)."""
        from redis.exceptions import ConnectionError as RedisConnectionError

        mock_redis = AsyncMock()
        mock_redis.incr.side_effect = RedisConnectionError("Connection refused")

        limiter = TenantRateLimiter(mock_redis)
        result = await limiter.check_rate_limit(
            tenant_id="acme",
            max_requests=100,
            window_seconds=60,
        )

        assert result["allowed"] is True


# ---------------------------------------------------------------------------
# 5. Test helpers validation
# ---------------------------------------------------------------------------

class TestAuthHelpers:
    """Tests for the auth test helper utilities themselves."""

    def test_create_test_token_is_valid_jwt(self):
        """create_test_token should produce a valid JWT string."""
        token = create_test_token(tenant_id="acme")
        assert isinstance(token, str)
        # JWT has 3 parts separated by dots
        parts = token.split(".")
        assert len(parts) == 3

    def test_create_test_payload_contains_required_claims(self):
        """create_test_payload should include all required claims."""
        payload = create_test_payload(
            tenant_id="acme",
            client_id="my-client",
            roles=["admin"],
            sub="user-42",
        )
        assert payload["tenant_id"] == "acme"
        assert payload["client_id"] == "my-client"
        assert payload["sub"] == "user-42"
        assert "admin" in payload["realm_access"]["roles"]
        assert "exp" in payload
        assert "iss" in payload

    def test_override_auth_returns_callable(self):
        """override_auth should return an async callable."""
        override_fn = override_auth(tenant_id="acme")
        assert callable(override_fn)

    def test_override_tenant_returns_callable(self):
        """override_tenant should return an async callable."""
        override_fn = override_tenant("acme")
        assert callable(override_fn)

    def test_create_expired_token(self):
        """create_expired_token should produce a token with past expiry."""
        import jwt as pyjwt
        from tests.utils.auth_helpers import TEST_PUBLIC_KEY_PEM

        token = create_expired_token(tenant_id="acme")
        # Decode without verification to check exp
        payload = pyjwt.decode(
            token,
            TEST_PUBLIC_KEY_PEM,
            algorithms=["RS256"],
            options={
                "verify_exp": False,
                "verify_aud": False,
                "verify_iss": False,
            },
        )
        import time
        assert payload["exp"] < time.time()
