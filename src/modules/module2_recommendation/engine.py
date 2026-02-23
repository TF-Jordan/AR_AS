"""
Main Recommendation Engine (Module 2).
Multi-tenant: uses tenant_slug for collection/cache isolation and tenant scoring config.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings

from .cache import CacheManager, get_cache_manager
from .embeddings import EmbeddingService, get_embedding_service
from .vector_store import VectorStore, get_vector_store
from .ranking import RankingService
from .schemas import SimilarProduct, RankedProduct

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Multi-tenant recommendation engine.

    Workflow:
    1. Check Redis cache (tenant-namespaced)
    2. Generate embedding from query text
    3. Search Qdrant for similar items (tenant collection)
    4. Retrieve item data from tenant schema
    5. Apply tenant-specific scoring criteria
    6. Store in cache
    7. Return results
    """

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None,
    ):
        self.cache = cache_manager or get_cache_manager()
        self.embeddings = embedding_service or get_embedding_service()
        self.vectors = vector_store or get_vector_store()

        logger.info("RecommendationEngine initialized")

    async def recommend(
        self,
        tenant_slug: str,
        query: str,
        scoring_criteria: List[Dict[str, Any]],
        session: AsyncSession,
        top_k: int = 10,
        sentiment_score: float = 0.0,
        client_id: str = "anonymous",
        location: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the recommendation workflow for a tenant.

        Args:
            tenant_slug: Tenant slug for data isolation
            query: User query text
            scoring_criteria: Tenant's scoring config
            session: DB session
            top_k: Number of results
            sentiment_score: Sentiment score of the query
            client_id: Client identifier
            location: Optional location {lat, lng}

        Returns:
            Recommendation result dict
        """
        start_time = datetime.utcnow()

        logger.info(
            f"Processing recommendation: tenant={tenant_slug}, query='{query[:50]}...', top_k={top_k}"
        )

        # Step 1: Check cache
        cached = await self.cache.get_cached_result(
            tenant_slug=tenant_slug,
            item_id=query[:100],  # Use query as cache key
            client_id=client_id,
            sentiment_score=sentiment_score,
        )
        if cached:
            logger.info("Returning cached result")
            return cached

        # Step 2: Generate embedding from query
        query_vector = self.embeddings.encode_for_qdrant(query)

        # Step 3: Search Qdrant for similar items
        similar_products = self.vectors.search(
            tenant_slug=tenant_slug,
            query_vector=query_vector,
            top_k=top_k * 2,  # Fetch extra for filtering
        )

        if not similar_products:
            logger.info("No similar items found")
            return self._empty_result(tenant_slug, query, sentiment_score)

        # Step 4: Retrieve item data from tenant schema
        from src.database.tenant_manager import get_tenant_manager
        tenant_manager = get_tenant_manager()

        items_data = {}
        for sp in similar_products:
            item = await tenant_manager.get_item(session, tenant_slug, sp.product_id)
            if item:
                items_data[sp.product_id] = item.get("data", {})

        # Step 5: Apply tenant-specific ranking
        ranking_service = RankingService(scoring_criteria)
        ranked_products = ranking_service.rank_products(
            similar_products, items_data
        )

        # Trim to top_k
        ranked_products = ranked_products[:top_k]

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        result = {
            "status": "success",
            "tenant": tenant_slug,
            "recommendations": [p.model_dump() for p in ranked_products],
            "total_results": len(ranked_products),
            "sentiment_query": sentiment_score,
            "temps_traitement_ms": round(processing_time * 1000, 2),
            "cached": False,
        }

        # Step 6: Store in cache
        await self.cache.store_result(
            tenant_slug=tenant_slug,
            item_id=query[:100],
            client_id=client_id,
            sentiment_score=sentiment_score,
            result=result,
        )

        logger.info(f"Recommendation completed: {len(ranked_products)} results")
        return result

    def _empty_result(self, tenant_slug: str, query: str, sentiment_score: float) -> Dict[str, Any]:
        return {
            "status": "success",
            "tenant": tenant_slug,
            "recommendations": [],
            "total_results": 0,
            "sentiment_query": sentiment_score,
            "temps_traitement_ms": 0,
            "cached": False,
        }

    async def health_check(self) -> Dict[str, bool]:
        return {
            "cache": await self.cache.health_check(),
            "embeddings": self.embeddings.health_check(),
            "vectors": self.vectors.health_check(),
        }


# Singleton instance
_engine_instance: Optional[RecommendationEngine] = None


def get_recommendation_engine() -> RecommendationEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RecommendationEngine()
    return _engine_instance
