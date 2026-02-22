"""
Main Orchestrator for the recommendation system.
Coordinates the flow between Module 1 (Sentiment) and Module 2 (Recommendation).
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.constants import ProductType
from src.modules.module1_sentiment import (
    SentimentAnalyzer,
    SentimentInput,
)
from src.modules.module2_recommendation import (
    RecommendationEngine,
    RecommendationRequest,
    CacheManager,
)

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestrator coordinating the recommendation workflow.

    Responsibilities:
    - Orchestrate Module 1 (sentiment) and Module 2 (recommendation)
    - Manage data flow between modules
    - Handle cache management
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
            self._recommendation_engine = RecommendationEngine()
        return self._recommendation_engine

    @property
    def cache_manager(self) -> CacheManager:
        if self._cache_manager is None:
            from src.modules.module2_recommendation.cache import get_cache_manager
            self._cache_manager = get_cache_manager()
        return self._cache_manager

    async def process_recommendation_request(
        self,
        product_id: str,
        client_id: str,
        commentaire: str,
        product_type: str,
        session: AsyncSession,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """
        Process a complete recommendation request.

        Flow:
        1. Analyze sentiment (Module 1)
        2. Generate recommendations (Module 2)
        3. Return combined results
        """
        logger.info(
            f"Processing recommendation request: "
            f"product={product_id}, client={client_id}"
        )

        start_time = datetime.utcnow()

        # Step 1: Sentiment Analysis (Module 1)
        sentiment_input = SentimentInput(
            product_id=product_id,
            client_id=client_id,
            commentaire=commentaire,
            product_type=product_type,
        )
        sentiment_result = self.sentiment_analyzer.analyze(sentiment_input)

        logger.info(
            f"Sentiment analysis completed: score={sentiment_result.sentiment_score:.2f}"
        )

        # Step 2: Recommendation (Module 2)
        rec_request = RecommendationRequest(
            client_id=client_id,
            product_id=product_id,
            sentiment_score=sentiment_result.sentiment_score,
            product_type=ProductType(product_type),
            top_k=top_k,
        )

        rec_result = await self.recommendation_engine.recommend(rec_request, session)

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return {
            "status": "completed",
            "processing_time_seconds": processing_time,
            "sentiment": {
                "score": sentiment_result.sentiment_score,
                "label": sentiment_result.sentiment_label,
                "confidence": sentiment_result.confidence,
            },
            "recommendations": rec_result.model_dump(),
        }

    async def invalidate_product_cache(
        self,
        product_id: str,
        product_type: str,
    ) -> int:
        return await self.cache_manager.invalidate(
            product_id=product_id,
            product_type=product_type,
        )

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
