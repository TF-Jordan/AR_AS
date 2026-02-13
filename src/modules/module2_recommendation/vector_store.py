"""
Multi-tenant Qdrant Vector Store for semantic search.
Implements per-tenant collections with HNSW-based similarity search.

Each tenant gets its own Qdrant collection named "tenant_{tenant_id}".
Product data is stored entirely in the Qdrant payload (no PostgreSQL dependency).
"""

import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.models import (
    Distance,
    PointStruct,
    VectorParams,
    SearchParams,
    HnswConfigDiff,
    ScoredPoint,
)

from src.config import settings
from src.utils.context import get_correlation_id

logger = logging.getLogger(__name__)


class MultiTenantVectorStore:
    """
    Multi-tenant Qdrant vector store.

    Each tenant has its own collection ("tenant_{tenant_id}").
    Product details are stored entirely in the Qdrant payload:
        {product_id, description, ...custom_metadata}

    No Vehicle model dependency.  No hardcoded collection names.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self._client: Optional[QdrantClient] = None
        self.dimension = settings.embedding_dimension

    def connect(self) -> None:
        """Establish Qdrant connection."""
        if self._client is None:
            self._client = QdrantClient(host=self.host, port=self.port)
            logger.info(
                "Qdrant connection established: %s:%s", self.host, self.port
            )

    @property
    def client(self) -> QdrantClient:
        """Get Qdrant client, connecting lazily if needed."""
        if self._client is None:
            self.connect()
        return self._client

    # ------------------------------------------------------------------
    # Collection name helpers
    # ------------------------------------------------------------------

    @staticmethod
    def collection_name_for_tenant(tenant_id: str) -> str:
        """Return the Qdrant collection name for a given tenant."""
        return f"tenant_{tenant_id}"

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def ensure_collection_exists(
        self,
        collection_name: str,
        vector_size: int = 768,
    ) -> bool:
        """
        Create a collection if it does not already exist.

        Args:
            collection_name: Qdrant collection name.
            vector_size: Embedding dimension.

        Returns:
            True if the collection exists (or was created successfully).
        """
        self.connect()
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)

            if not exists:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE,
                    ),
                    hnsw_config=HnswConfigDiff(
                        m=16,
                        ef_construct=100,
                        full_scan_threshold=10000,
                    ),
                )
                logger.info("Created Qdrant collection: %s", collection_name)
            else:
                logger.debug(
                    "Qdrant collection already exists: %s", collection_name
                )

            return True

        except Exception as e:
            logger.error(
                "Error ensuring collection %s: %s", collection_name, e
            )
            return False

    def delete_collection(self, tenant_id: str) -> bool:
        """
        Delete the Qdrant collection for a tenant.

        Args:
            tenant_id: External tenant identifier.

        Returns:
            True if deleted successfully (or collection did not exist).
        """
        self.connect()
        collection_name = self.collection_name_for_tenant(tenant_id)

        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)

            if exists:
                self.client.delete_collection(collection_name)
                logger.info(
                    "Deleted Qdrant collection: %s", collection_name
                )
            else:
                logger.debug(
                    "Collection does not exist, nothing to delete: %s",
                    collection_name,
                )
            return True

        except Exception as e:
            logger.error(
                "Error deleting collection %s: %s", collection_name, e
            )
            return False

    def get_collection_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        Return collection statistics for a tenant.

        Args:
            tenant_id: External tenant identifier.

        Returns:
            Dict with collection info or error description.
        """
        self.connect()
        collection_name = self.collection_name_for_tenant(tenant_id)

        try:
            info = self.client.get_collection(collection_name)
            return {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "vectors_count": info.points_count,
                "points_count": info.points_count,
                "status": str(info.status),
            }
        except Exception as e:
            logger.error(
                "Error getting collection stats for %s: %s",
                collection_name,
                e,
            )
            return {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "error": str(e),
            }

    # ------------------------------------------------------------------
    # Product upload (batch upsert with vectors)
    # ------------------------------------------------------------------

    def add_products(
        self,
        tenant_id: str,
        products: List[Dict[str, Any]],
    ) -> int:
        """
        Batch upsert products into the tenant's Qdrant collection.

        Each product dict must contain:
            - product_id: str
            - vector: List[float]  (embedding)
            - description: str
            - metadata: dict (optional custom fields for scoring)

        The full payload stored in Qdrant is:
            {product_id, description, **metadata}

        Args:
            tenant_id: External tenant identifier.
            products: List of product dicts with vectors.

        Returns:
            Number of points upserted.
        """
        self.connect()
        collection_name = self.collection_name_for_tenant(tenant_id)

        # Ensure collection exists
        self.ensure_collection_exists(collection_name, self.dimension)

        points = []
        for item in products:
            point_id = str(uuid4())
            payload = {
                "product_id": item["product_id"],
                "description": item.get("description", ""),
                **(item.get("metadata", {})),
            }
            points.append(
                PointStruct(
                    id=point_id,
                    vector=item["vector"],
                    payload=payload,
                )
            )

        if points:
            # Batch in chunks of 100
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                self.client.upsert(
                    collection_name=collection_name,
                    points=batch,
                    wait=True,
                )
            logger.info(
                "Batch upserted %d products to collection %s",
                len(points),
                collection_name,
            )

        return len(points)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_similar(
        self,
        tenant_id: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ScoredPoint]:
        """
        Search for similar products in a tenant's collection.

        Returns raw ScoredPoint objects so the engine can access
        both the score and the full payload for dynamic scoring.

        Args:
            tenant_id: External tenant identifier.
            query_vector: Query embedding vector.
            limit: Max number of results.
            score_threshold: Minimum similarity score.
            filters: Optional Qdrant payload filters.

        Returns:
            List of ScoredPoint from Qdrant.
        """
        start_time = time.time()
        self.connect()
        collection_name = self.collection_name_for_tenant(tenant_id)

        # Build Qdrant filter from dict if provided
        qdrant_filter = None
        if filters:
            must_conditions = []
            for key, value in filters.items():
                must_conditions.append(
                    qdrant_models.FieldCondition(
                        key=key,
                        match=qdrant_models.MatchValue(value=value),
                    )
                )
            qdrant_filter = qdrant_models.Filter(must=must_conditions)

        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=qdrant_filter,
                search_params=SearchParams(
                    hnsw_ef=128,
                    exact=False,
                ),
            )

            duration_ms = (time.time() - start_time) * 1000
            scores = [r.score for r in results]

            logger.info(
                "Vector search completed: %d results in %.2fms",
                len(results),
                duration_ms,
                extra={
                    "event": "vector_search",
                    "metric_type": "vector_search",
                    "operation": "search",
                    "collection": collection_name,
                    "tenant_id": tenant_id,
                    "query_limit": limit,
                    "results_count": len(results),
                    "score_threshold": score_threshold,
                    "duration_ms": round(duration_ms, 2),
                    "avg_score": round(sum(scores) / len(scores), 3) if scores else 0,
                    "max_score": round(max(scores), 3) if scores else 0,
                    "min_score": round(min(scores), 3) if scores else 0,
                    "vector_dim": len(query_vector),
                    "has_filters": filters is not None,
                    "correlation_id": get_correlation_id(),
                },
            )

            return results

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Vector search error for tenant %s: %s",
                tenant_id,
                e,
                extra={
                    "event": "vector_search_error",
                    "metric_type": "vector_search",
                    "operation": "search",
                    "collection": collection_name,
                    "tenant_id": tenant_id,
                    "error": str(e),
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": get_correlation_id(),
                },
            )
            return []

    # ------------------------------------------------------------------
    # Delete single product
    # ------------------------------------------------------------------

    def delete_product(self, tenant_id: str, product_id: str) -> bool:
        """
        Delete vectors for a specific product from a tenant's collection.

        Args:
            tenant_id: External tenant identifier.
            product_id: Product ID to delete.

        Returns:
            True if deletion succeeded.
        """
        self.connect()
        collection_name = self.collection_name_for_tenant(tenant_id)

        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=qdrant_models.FilterSelector(
                    filter=qdrant_models.Filter(
                        must=[
                            qdrant_models.FieldCondition(
                                key="product_id",
                                match=qdrant_models.MatchValue(value=product_id),
                            )
                        ]
                    )
                ),
            )
            logger.info(
                "Deleted product %s from tenant %s collection",
                product_id,
                tenant_id,
            )
            return True

        except Exception as e:
            logger.error(
                "Delete error for product %s in tenant %s: %s",
                product_id,
                tenant_id,
                e,
            )
            return False

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """Check Qdrant connection health."""
        try:
            self.connect()
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error("Qdrant health check failed: %s", e)
            return False


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_vector_store: Optional[MultiTenantVectorStore] = None


def get_vector_store() -> MultiTenantVectorStore:
    """Get or create singleton multi-tenant vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = MultiTenantVectorStore()
    return _vector_store
