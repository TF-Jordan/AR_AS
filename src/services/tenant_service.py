"""
Tenant management service for the multi-tenant RaaS platform.

Handles CRUD operations for tenants, including Qdrant collection
provisioning and default scoring configuration setup.
"""

import logging
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models_multitenant import ProductDescription, ScoringConfig, Tenant
from src.api.schemas_multitenant import TenantCreate, TenantUpdate

logger = logging.getLogger(__name__)

# Default scoring criteria applied when a tenant is created without specifying one
DEFAULT_SCORING_CRITERIA = [
    {"name": "similarity", "weight": 0.70, "type": "system"},
    {"name": "price_match", "weight": 0.20, "type": "custom"},
    {"name": "location_proximity", "weight": 0.10, "type": "custom"},
]


class TenantService:
    """Service for managing tenant lifecycle and data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_tenant(self, tenant_data: TenantCreate) -> Tenant:
        """
        Create a new tenant with Qdrant collection and default scoring config.

        Steps:
        1. Validate tenant_id uniqueness.
        2. Create the Tenant record.
        3. Create the Qdrant collection (``tenant_{tenant_id}``).
        4. Create a default (or user-supplied) scoring config.
        5. Return the persisted tenant.

        Args:
            tenant_data: Validated tenant creation payload.

        Returns:
            The newly created ``Tenant`` ORM instance.

        Raises:
            ValueError: If tenant_id is already taken.
        """
        # 1. Check uniqueness
        existing = await self._get_by_tenant_id(tenant_data.tenant_id)
        if existing is not None:
            raise ValueError(f"Tenant with tenant_id '{tenant_data.tenant_id}' already exists")

        # 2. Build Tenant record
        collection_name = f"tenant_{tenant_data.tenant_id}"
        tenant = Tenant(
            tenant_id=tenant_data.tenant_id,
            name=tenant_data.name,
            domain=tenant_data.domain,
            keycloak_client_id=tenant_data.keycloak_client_id,
            qdrant_collection_name=collection_name,
            rate_limit_requests=tenant_data.rate_limit_requests,
            rate_limit_window_seconds=tenant_data.rate_limit_window_seconds,
        )
        self.db.add(tenant)
        await self.db.flush()  # get the ID without committing

        # 3. Create Qdrant collection
        await self._create_qdrant_collection(collection_name)

        # 4. Create default scoring config
        criteria = (
            [c.model_dump() for c in tenant_data.initial_scoring_criteria]
            if tenant_data.initial_scoring_criteria
            else DEFAULT_SCORING_CRITERIA
        )
        scoring_config = ScoringConfig(
            tenant_id=tenant_data.tenant_id,
            scoring_criteria=criteria,
            version=1,
            is_active=True,
        )
        self.db.add(scoring_config)
        await self.db.flush()

        logger.info(
            "Tenant created: %s (collection=%s)",
            tenant_data.tenant_id,
            collection_name,
        )
        return tenant

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_tenant(self, tenant_id: str) -> Tenant:
        """
        Get a tenant by its external tenant_id.

        Args:
            tenant_id: External tenant identifier.

        Returns:
            Tenant ORM instance.

        Raises:
            ValueError: If not found.
        """
        tenant = await self._get_by_tenant_id(tenant_id)
        if tenant is None:
            raise ValueError(f"Tenant '{tenant_id}' not found")
        return tenant

    async def get_tenant_by_keycloak_client(self, client_id: str) -> Tenant:
        """
        Look up a tenant by its Keycloak client_id.

        Args:
            client_id: The Keycloak OAuth2 client ID.

        Returns:
            Tenant ORM instance.

        Raises:
            ValueError: If no matching tenant exists.
        """
        stmt = select(Tenant).where(Tenant.keycloak_client_id == client_id)
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()
        if tenant is None:
            raise ValueError(f"No tenant found for keycloak_client_id '{client_id}'")
        return tenant

    async def list_tenants(
        self, skip: int = 0, limit: int = 100, active_only: bool = True,
    ) -> tuple[List[Tenant], int]:
        """
        List tenants with pagination.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            active_only: If True, only return active tenants.

        Returns:
            Tuple of (list of tenants, total count).
        """
        base = select(Tenant)
        count_base = select(func.count(Tenant.id))

        if active_only:
            base = base.where(Tenant.is_active.is_(True))
            count_base = count_base.where(Tenant.is_active.is_(True))

        # Total count
        total_result = await self.db.execute(count_base)
        total = total_result.scalar_one()

        # Paginated results
        stmt = base.order_by(Tenant.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        tenants = list(result.scalars().all())

        return tenants, total

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_tenant(self, tenant_id: str, updates: TenantUpdate) -> Tenant:
        """
        Update tenant metadata.

        Args:
            tenant_id: External tenant identifier.
            updates: Fields to update (only non-None values are applied).

        Returns:
            Updated Tenant ORM instance.

        Raises:
            ValueError: If tenant not found.
        """
        tenant = await self.get_tenant(tenant_id)

        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)

        await self.db.flush()
        logger.info("Tenant updated: %s (fields=%s)", tenant_id, list(update_data.keys()))
        return tenant

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_tenant(self, tenant_id: str) -> bool:
        """
        Delete a tenant and clean up associated resources.

        Steps:
        1. Deactivate all scoring configs.
        2. Delete Qdrant collection.
        3. Delete product descriptions.
        4. Delete tenant record.

        Args:
            tenant_id: External tenant identifier.

        Returns:
            True if deletion was successful.

        Raises:
            ValueError: If tenant not found.
        """
        tenant = await self.get_tenant(tenant_id)

        # Delete Qdrant collection
        await self._delete_qdrant_collection(tenant.qdrant_collection_name)

        # Delete tenant (cascading deletes scoring_configs and products)
        await self.db.delete(tenant)
        await self.db.flush()

        logger.info("Tenant deleted: %s", tenant_id)
        return True

    # ------------------------------------------------------------------
    # Qdrant helpers
    # ------------------------------------------------------------------

    async def _create_qdrant_collection(self, collection_name: str) -> None:
        """
        Create a Qdrant collection for the tenant.

        This is a placeholder that should be replaced with actual
        Qdrant client calls when the vector store module is integrated.

        Args:
            collection_name: Name of the Qdrant collection to create.
        """
        # TODO: Integrate with Qdrant client
        # from qdrant_client import QdrantClient
        # client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        # client.create_collection(
        #     collection_name=collection_name,
        #     vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        # )
        logger.info("Qdrant collection creation requested: %s", collection_name)

    async def _delete_qdrant_collection(self, collection_name: str) -> None:
        """
        Delete a Qdrant collection.

        Args:
            collection_name: Name of the Qdrant collection to delete.
        """
        # TODO: Integrate with Qdrant client
        # client.delete_collection(collection_name=collection_name)
        logger.info("Qdrant collection deletion requested: %s", collection_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_by_tenant_id(self, tenant_id: str) -> Optional[Tenant]:
        """Look up tenant by tenant_id, returning None if not found."""
        stmt = select(Tenant).where(Tenant.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
