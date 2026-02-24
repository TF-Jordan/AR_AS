"""
Tenant provisioning and schema management.
Handles PostgreSQL schema creation/deletion and Qdrant collection management.
"""

import logging
import re
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.constants import TENANT_SCHEMA_PREFIX

logger = logging.getLogger(__name__)

# SQL templates for tenant schema provisioning
CREATE_SCHEMA_SQL = "CREATE SCHEMA IF NOT EXISTS {schema_name}"
DROP_SCHEMA_SQL = "DROP SCHEMA IF EXISTS {schema_name} CASCADE"

CREATE_ITEMS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {schema_name}.items (
    id VARCHAR(100) PRIMARY KEY,
    data JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    embedding_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
)
"""

CREATE_REVIEWS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {schema_name}.reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id VARCHAR(100) NOT NULL REFERENCES {schema_name}.items(id) ON DELETE CASCADE,
    client_id VARCHAR(100) NOT NULL,
    commentaire TEXT NOT NULL,
    sentiment_score FLOAT,
    sentiment_label VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
)
"""

CREATE_REVIEWS_INDEX_ITEM_SQL = """
CREATE INDEX IF NOT EXISTS idx_{safe_slug}_reviews_item ON {schema_name}.reviews(item_id)
"""

CREATE_REVIEWS_INDEX_CLIENT_SQL = """
CREATE INDEX IF NOT EXISTS idx_{safe_slug}_reviews_client ON {schema_name}.reviews(client_id)
"""


def _get_schema_name(tenant_slug: str) -> str:
    """Get PostgreSQL schema name for a tenant."""
    return f"{TENANT_SCHEMA_PREFIX}{tenant_slug}"


def _validate_slug(slug: str) -> bool:
    """Validate tenant slug is safe for use in SQL identifiers."""
    return bool(re.match(r'^[a-z0-9][a-z0-9_-]{1,98}$', slug))


def _safe_slug(slug: str) -> str:
    """Convert slug to safe SQL identifier part (replace hyphens with underscores)."""
    return slug.replace("-", "_")


class TenantManager:
    """Manages tenant provisioning: PostgreSQL schemas and Qdrant collections."""

    async def create_tenant_schema(self, session: AsyncSession, tenant_slug: str) -> bool:
        """
        Create PostgreSQL schema and tables for a new tenant.

        Args:
            session: Database session
            tenant_slug: Tenant slug identifier

        Returns:
            True if created successfully
        """
        if not _validate_slug(tenant_slug):
            raise ValueError(f"Invalid tenant slug: {tenant_slug}")

        schema_name = _get_schema_name(tenant_slug)
        safe_slug = _safe_slug(tenant_slug)

        try:
            await session.execute(text(CREATE_SCHEMA_SQL.format(schema_name=schema_name)))
            await session.execute(text(CREATE_ITEMS_TABLE_SQL.format(schema_name=schema_name)))
            await session.execute(text(CREATE_REVIEWS_TABLE_SQL.format(schema_name=schema_name)))
            await session.execute(text(CREATE_REVIEWS_INDEX_ITEM_SQL.format(
                schema_name=schema_name, safe_slug=safe_slug
            )))
            await session.execute(text(CREATE_REVIEWS_INDEX_CLIENT_SQL.format(
                schema_name=schema_name, safe_slug=safe_slug
            )))
            await session.flush()

            logger.info(f"Created tenant schema: {schema_name}")
            return True

        except Exception as e:
            logger.error(f"Error creating tenant schema {schema_name}: {e}")
            raise

    async def drop_tenant_schema(self, session: AsyncSession, tenant_slug: str) -> bool:
        """
        Drop PostgreSQL schema for a tenant (CASCADE).

        Args:
            session: Database session
            tenant_slug: Tenant slug identifier

        Returns:
            True if dropped successfully
        """
        if not _validate_slug(tenant_slug):
            raise ValueError(f"Invalid tenant slug: {tenant_slug}")

        schema_name = _get_schema_name(tenant_slug)

        try:
            await session.execute(text(DROP_SCHEMA_SQL.format(schema_name=schema_name)))
            await session.flush()
            logger.info(f"Dropped tenant schema: {schema_name}")
            return True

        except Exception as e:
            logger.error(f"Error dropping tenant schema {schema_name}: {e}")
            raise

    async def create_qdrant_collection(self, tenant_slug: str) -> bool:
        """
        Create a Qdrant collection for a tenant.

        Args:
            tenant_slug: Tenant slug identifier

        Returns:
            True if created successfully
        """
        from src.modules.module2_recommendation.vector_store import get_vector_store

        vector_store = get_vector_store()
        collection_name = f"{TENANT_SCHEMA_PREFIX}{tenant_slug}"

        try:
            vector_store.connect()
            collections = vector_store.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)

            if not exists:
                from qdrant_client.http.models import (
                    Distance,
                    VectorParams,
                    HnswConfigDiff,
                )
                from src.config import settings

                vector_store.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=settings.embedding_dimension,
                        distance=Distance.COSINE,
                    ),
                    hnsw_config=HnswConfigDiff(
                        m=16,
                        ef_construct=100,
                        full_scan_threshold=10000,
                    ),
                )
                logger.info(f"Created Qdrant collection: {collection_name}")

            return True

        except Exception as e:
            logger.error(f"Error creating Qdrant collection {collection_name}: {e}")
            raise

    async def delete_qdrant_collection(self, tenant_slug: str) -> bool:
        """Delete a Qdrant collection for a tenant."""
        from src.modules.module2_recommendation.vector_store import get_vector_store

        vector_store = get_vector_store()
        collection_name = f"{TENANT_SCHEMA_PREFIX}{tenant_slug}"

        try:
            vector_store.connect()
            vector_store.client.delete_collection(collection_name)
            logger.info(f"Deleted Qdrant collection: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting Qdrant collection {collection_name}: {e}")
            return False

    async def provision_tenant(self, session: AsyncSession, tenant_slug: str) -> bool:
        """
        Full tenant provisioning: PostgreSQL schema + Qdrant collection.

        Args:
            session: Database session
            tenant_slug: Tenant slug identifier

        Returns:
            True if all provisioning succeeded
        """
        await self.create_tenant_schema(session, tenant_slug)
        await self.create_qdrant_collection(tenant_slug)
        logger.info(f"Tenant fully provisioned: {tenant_slug}")
        return True

    async def deprovision_tenant(self, session: AsyncSession, tenant_slug: str) -> bool:
        """
        Full tenant deprovisioning: drop schema + delete collection.

        Args:
            session: Database session
            tenant_slug: Tenant slug identifier

        Returns:
            True if all deprovisioning succeeded
        """
        await self.drop_tenant_schema(session, tenant_slug)
        await self.delete_qdrant_collection(tenant_slug)
        logger.info(f"Tenant fully deprovisioned: {tenant_slug}")
        return True

    async def insert_items(
        self, session: AsyncSession, tenant_slug: str, items: list[dict]
    ) -> int:
        """
        Insert items into a tenant's schema.

        Args:
            session: Database session
            tenant_slug: Tenant slug
            items: List of item dicts with 'id', 'data' (JSONB), 'embedding_text'

        Returns:
            Number of items inserted
        """
        import json

        if not _validate_slug(tenant_slug):
            raise ValueError(f"Invalid tenant slug: {tenant_slug}")

        schema_name = _get_schema_name(tenant_slug)
        count = 0

        for item in items:
            item_id = str(item.get("id", ""))
            data = item.get("data", item)
            # Remove 'id' from data to avoid duplication
            if isinstance(data, dict):
                data = {k: v for k, v in data.items() if k != "id"}

            # Build embedding text from all string values
            embedding_text = item.get("embedding_text")
            if not embedding_text:
                text_parts = []
                for k, v in data.items():
                    if isinstance(v, str):
                        text_parts.append(f"{k}: {v}")
                embedding_text = ". ".join(text_parts)

            await session.execute(
                text(
                    f"INSERT INTO {schema_name}.items (id, data, embedding_text) "
                    f"VALUES (:id, :data::jsonb, :embedding_text) "
                    f"ON CONFLICT (id) DO UPDATE SET data = :data::jsonb, embedding_text = :embedding_text"
                ),
                {
                    "id": item_id,
                    "data": json.dumps(data, ensure_ascii=False),
                    "embedding_text": embedding_text,
                },
            )
            count += 1

        await session.flush()
        logger.info(f"Inserted {count} items into {schema_name}")
        return count

    async def get_items(
        self, session: AsyncSession, tenant_slug: str, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        """Fetch items from a tenant's schema."""
        if not _validate_slug(tenant_slug):
            raise ValueError(f"Invalid tenant slug: {tenant_slug}")

        schema_name = _get_schema_name(tenant_slug)
        result = await session.execute(
            text(f"SELECT id, data, embedding_text, created_at FROM {schema_name}.items ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
            {"limit": limit, "offset": offset},
        )
        rows = result.fetchall()
        return [
            {"id": row[0], "data": row[1], "embedding_text": row[2], "created_at": str(row[3])}
            for row in rows
        ]

    async def get_item(self, session: AsyncSession, tenant_slug: str, item_id: str) -> Optional[dict]:
        """Fetch a single item from a tenant's schema."""
        if not _validate_slug(tenant_slug):
            raise ValueError(f"Invalid tenant slug: {tenant_slug}")

        schema_name = _get_schema_name(tenant_slug)
        result = await session.execute(
            text(f"SELECT id, data, embedding_text, created_at FROM {schema_name}.items WHERE id = :item_id"),
            {"item_id": item_id},
        )
        row = result.fetchone()
        if row:
            return {"id": row[0], "data": row[1], "embedding_text": row[2], "created_at": str(row[3])}
        return None

    async def delete_item(self, session: AsyncSession, tenant_slug: str, item_id: str) -> bool:
        """Delete an item from a tenant's schema."""
        if not _validate_slug(tenant_slug):
            raise ValueError(f"Invalid tenant slug: {tenant_slug}")

        schema_name = _get_schema_name(tenant_slug)
        result = await session.execute(
            text(f"DELETE FROM {schema_name}.items WHERE id = :item_id"),
            {"item_id": item_id},
        )
        await session.flush()
        return result.rowcount > 0

    async def count_items(self, session: AsyncSession, tenant_slug: str) -> int:
        """Count items in a tenant's schema."""
        if not _validate_slug(tenant_slug):
            raise ValueError(f"Invalid tenant slug: {tenant_slug}")

        schema_name = _get_schema_name(tenant_slug)
        result = await session.execute(
            text(f"SELECT COUNT(*) FROM {schema_name}.items")
        )
        return result.scalar() or 0


# Singleton
_tenant_manager: Optional[TenantManager] = None


def get_tenant_manager() -> TenantManager:
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager()
    return _tenant_manager
