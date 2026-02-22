"""
Main Recommendation Engine (Module 2).
Orchestrates the complete recommendation workflow.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.config.constants import ProductType

from .cache import CacheManager, get_cache_manager
from .embeddings import EmbeddingService, get_embedding_service
from .vector_store import VectorStore, get_vector_store
from .ranking import RankingService, get_ranking_service
from .schemas import (
    RecommendationRequest,
    RecommendationResult,
    SimilarProduct,
    ProductDetails,
    RankedProduct,
    IntermediateResult,
)

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Main recommendation engine implementing the complete workflow:

    1. Check Redis cache
    2. Build textual description from product data
    3. Generate embedding
    4. Search Qdrant for similar products
    5. Retrieve top-K results
    6. Apply final ranking
    7. Store in cache
    8. Return results
    """

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None,
        ranking_service: Optional[RankingService] = None,
    ):
        self.cache = cache_manager or get_cache_manager()
        self.embeddings = embedding_service or get_embedding_service()
        self.vectors = vector_store or get_vector_store()
        self.ranking = ranking_service or get_ranking_service()

        logger.info("RecommendationEngine initialized")

    async def recommend(
        self,
        request: RecommendationRequest,
        session: AsyncSession,
    ) -> RecommendationResult:
        """
        Execute the complete recommendation workflow.
        """
        logger.info(
            f"Processing recommendation for product={request.product_id}, "
            f"client={request.client_id}, sentiment={request.sentiment_score:.2f}"
        )

        # Step 1: Check cache
        cached_result = await self.cache.get_cached_result(request)
        if cached_result:
            logger.info("Returning cached result")
            return cached_result

        # Step 2: Generate embedding from product_id description
        # In the multi-tenant RaaS version, product details will come from
        # the tenant's data store. For now, use product_id as query.
        query_text = request.product_id
        query_vector = self.embeddings.encode_for_qdrant(query_text)

        # Step 3: Search Qdrant for similar products
        similar_products = self.vectors.search(
            product_type=request.product_type,
            query_vector=query_vector,
            top_k=request.top_k * 2,
        )

        # Filter out the reference product itself
        similar_products = [
            p for p in similar_products if p.product_id != request.product_id
        ]

        if not similar_products:
            logger.info("No similar products found")
            return self._empty_result(request)

        # Step 4: Build ranked results
        ranked_products = []
        for i, similar in enumerate(similar_products[:request.top_k]):
            ranked_product = RankedProduct(
                product_id=similar.product_id,
                product_type=request.product_type,
                similarity_score=round(similar.similarity_score, 4),
                availability_score=1.0,
                reputation_score=0.0,
                final_score=round(similar.similarity_score, 4),
                rank=i + 1,
                metadata={},
            )
            ranked_products.append(ranked_product)

        # Build final result
        result = RecommendationResult(
            client_id=request.client_id,
            reference_product_id=request.product_id,
            sentiment_score=request.sentiment_score,
            product_type=request.product_type,
            recommendations=ranked_products,
            total_results=len(ranked_products),
            cached=False,
            processed_at=datetime.utcnow(),
        )

        # Step 5: Store in cache
        await self.cache.store_result(request, result)

        logger.info(f"Recommendation completed: {len(ranked_products)} results")
        return result

    def _empty_result(self, request: RecommendationRequest) -> RecommendationResult:
        return RecommendationResult(
            client_id=request.client_id,
            reference_product_id=request.product_id,
            sentiment_score=request.sentiment_score,
            product_type=request.product_type,
            recommendations=[],
            total_results=0,
            cached=False,
            processed_at=datetime.utcnow(),
        )

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
