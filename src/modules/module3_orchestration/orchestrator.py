"""
Main Orchestrator for the RaaS recommendation system.
Coordinates the flow between Module 1 (Sentiment) and Module 2 (Recommendation).
Multi-tenant aware.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.module1_sentiment import (
    SentimentAnalyzer,
    SentimentInput,
)
from src.modules.module2_recommendation import (
    RecommendationEngine,
    get_recommendation_engine,
    CacheManager,
    get_cache_manager,
)

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestrator coordinating the multi-tenant recommendation workflow.

    Responsibilities:
    - Orchestrate Module 1 (sentiment) and Module 2 (recommendation)
    - Route requests to correct tenant data stores
    - Manage cache per tenant
    """

    def __init__(
        self,
        sentiment_analyzer: Optional[SentimentAnalyzer] = None,
        recommendation_engine: Optional[RecommendationEngine] = None,
        cache_manager: Optional[CacheManager] = None,
    ):
        self._sentiment_analyzer = sentiment_analyzer
        self._recommendation_engine = recommendation_engine
        self._cache_manager = cache_manager

        logger.info("Orchestrator initialized")

    @property
    def sentiment_analyzer(self) -> SentimentAnalyzer:
        if self._sentiment_analyzer is None:
            self._sentiment_analyzer = SentimentAnalyzer()
        return self._sentiment_analyzer

    @property
    def recommendation_engine(self) -> RecommendationEngine:
        if self._recommendation_engine is None:
            self._recommendation_engine = get_recommendation_engine()
        return self._recommendation_engine

    @property
    def cache_manager(self) -> CacheManager:
        if self._cache_manager is None:
            self._cache_manager = get_cache_manager()
        return self._cache_manager

    async def process_recommendation(
        self,
        tenant_slug: str,
        query: str,
        scoring_criteria: List[Dict[str, Any]],
        session: AsyncSession,
        top_k: int = 10,
        client_id: str = "anonymous",
        location: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Process a complete recommendation request for a tenant.

        Flow:
        1. Analyze sentiment of query (Module 1)
        2. Generate recommendations (Module 2) with tenant-specific scoring
        3. Return combined results
        """
        logger.info(f"Processing recommendation: tenant={tenant_slug}")

        start_time = datetime.utcnow()

        # Step 1: Sentiment Analysis
        sentiment_input = SentimentInput(
            product_id="query",
            client_id=client_id,
            commentaire=query,
        )
        sentiment_result = self.sentiment_analyzer.analyze(sentiment_input)
        sentiment_score = sentiment_result.sentiment_score

        logger.info(f"Sentiment analysis: score={sentiment_score:.2f}")

        # Step 2: Recommendation with tenant scoring
        rec_result = await self.recommendation_engine.recommend(
            tenant_slug=tenant_slug,
            query=query,
            scoring_criteria=scoring_criteria,
            session=session,
            top_k=top_k,
            sentiment_score=sentiment_score,
            client_id=client_id,
            location=location,
        )

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        rec_result["sentiment_query"] = sentiment_score
        rec_result["sentiment_label"] = sentiment_result.sentiment_label
        rec_result["temps_traitement_ms"] = round(processing_time * 1000, 2)

        return rec_result

    async def invalidate_tenant_cache(self, tenant_slug: str) -> int:
        return await self.cache_manager.invalidate_tenant(tenant_slug)

    async def health_check(self) -> Dict[str, Any]:
        from src.modules.module2_recommendation.vector_store import get_vector_store
        from src.modules.module2_recommendation.embeddings import get_embedding_service
        from src.modules.module2_recommendation.cache import get_cache_manager

        cache = get_cache_manager()
        embeddings = get_embedding_service()
        vectors = get_vector_store()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "sentiment_analyzer": self.sentiment_analyzer.health_check(),
                "redis": await cache.health_check(),
                "embeddings": embeddings.health_check(),
                "qdrant": vectors.health_check(),
            },
        }


# Singleton instance
_orchestrator_instance: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = Orchestrator()
    return _orchestrator_instance
