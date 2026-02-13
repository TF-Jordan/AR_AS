"""
Multi-Tenant Recommendation Engine (Module 2).

Orchestrates the complete recommendation workflow with:
- Per-tenant Qdrant collections (format: tenant_{tenant_id})
- Dynamic scoring based on ScoringConfig JSON criteria
- Product data from Qdrant payload only (no PostgreSQL product tables)
- Sentiment boost from Module 1 results
- Internal ScoringConfig resolution via database session
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models_multitenant import ScoringConfig
from src.modules.module1_sentiment.schemas import SentimentResult
from src.services.scoring_service import ScoringConfigService

from .cache import CacheManager, get_cache_manager
from .embeddings import EmbeddingService, get_embedding_service
from .vector_store import MultiTenantVectorStore, get_vector_store
from .schemas import ProductScore, MultiTenantRecommendationResult

logger = logging.getLogger(__name__)


class MultiTenantRecommendationEngine:
    """
    Multi-tenant recommendation engine.

    Accepts a database session so it can resolve the active ScoringConfig
    for a tenant internally.  Product data comes exclusively from Qdrant
    payloads -- there is **no** Vehicle model or PostgreSQL product query.

    Workflow (inside ``recommend``):
    1. Build collection name ``tenant_{tenant_id}``
    2. Vectorize the product description via the embedding service
    3. Search the tenant's Qdrant collection for similar products
    4. Fetch the active ScoringConfig for the tenant from PostgreSQL
    5. Apply dynamic scoring formula (system + custom criteria)
    6. Return the top-k product IDs as ``List[str]``
    """

    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        cache_manager: Optional[CacheManager] = None,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[MultiTenantVectorStore] = None,
    ):
        self.db = db
        self.cache = cache_manager or get_cache_manager()
        self.embeddings = embedding_service or get_embedding_service()
        self.vectors = vector_store or get_vector_store()

        logger.info("MultiTenantRecommendationEngine initialized (db=%s)", "yes" if db else "no")

    # ------------------------------------------------------------------
    # Main entry-point
    # ------------------------------------------------------------------

    async def recommend(
        self,
        tenant_id: str,
        product_id: str,
        product_description: str,
        sentiment_result: SentimentResult,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Execute the multi-tenant recommendation workflow.

        Args:
            tenant_id: Tenant identifier (determines Qdrant collection).
            product_id: Reference product ID (excluded from results).
            product_description: Text description for embedding generation.
            sentiment_result: Sentiment analysis result from Module 1.
            top_k: Number of recommendations to return.
            filters: Optional payload filters forwarded to Qdrant.

        Returns:
            Ordered list of recommended product_id strings.

        Raises:
            ValueError: If no active ScoringConfig exists for the tenant.
        """
        logger.info(
            "recommend() start: tenant=%s product=%s client=%s sentiment=%s (%.2f) top_k=%d",
            tenant_id,
            product_id,
            sentiment_result.client_id,
            sentiment_result.sentiment_label,
            sentiment_result.sentiment_score,
            top_k,
        )

        # 1. Collection name
        collection_name = f"tenant_{tenant_id}"
        logger.debug("Target Qdrant collection: %s", collection_name)

        # 2. Vectorize product description
        query_vector = self.embeddings.encode_for_qdrant(product_description)
        logger.debug(
            "Embedding generated for product %s (dim=%d)",
            product_id,
            len(query_vector),
        )

        # 3. Search tenant's Qdrant collection (fetch extra for filtering)
        search_results = self.vectors.search_similar(
            tenant_id=tenant_id,
            query_vector=query_vector,
            limit=top_k * 2,
            filters=filters,
        )

        # Exclude the reference product from results
        search_results = [
            r for r in search_results
            if r.payload.get("product_id") != product_id
        ]

        if not search_results:
            logger.info(
                "No similar products found for tenant=%s product=%s",
                tenant_id,
                product_id,
            )
            return []

        # 4. Fetch active ScoringConfig for tenant
        scoring_config = await self._get_scoring_config(tenant_id)

        # 5. Apply dynamic scoring
        scored_products = self._apply_dynamic_scoring(
            search_results=search_results[:top_k],
            scoring_config=scoring_config,
            sentiment_result=sentiment_result,
        )

        # 6. Return ordered product IDs
        product_ids = [p.product_id for p in scored_products]

        logger.info(
            "recommend() done: tenant=%s returned %d product_ids (scoring_config v%d)",
            tenant_id,
            len(product_ids),
            scoring_config.version,
        )
        return product_ids

    # ------------------------------------------------------------------
    # Rich result variant (used by routes that need full breakdown)
    # ------------------------------------------------------------------

    async def recommend_detailed(
        self,
        tenant_id: str,
        product_id: str,
        product_description: str,
        sentiment_result: SentimentResult,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> MultiTenantRecommendationResult:
        """
        Same workflow as ``recommend()`` but returns a rich result object
        including per-criterion score breakdowns and metadata.

        Used by API routes that need to expose full scoring details.
        """
        logger.info(
            "recommend_detailed() start: tenant=%s product=%s client=%s",
            tenant_id,
            product_id,
            sentiment_result.client_id,
        )

        collection_name = f"tenant_{tenant_id}"

        # Vectorize
        query_vector = self.embeddings.encode_for_qdrant(product_description)

        # Search
        search_results = self.vectors.search_similar(
            tenant_id=tenant_id,
            query_vector=query_vector,
            limit=top_k * 2,
            filters=filters,
        )

        # Filter self
        search_results = [
            r for r in search_results
            if r.payload.get("product_id") != product_id
        ]

        # Scoring config
        scoring_config = await self._get_scoring_config(tenant_id)

        if not search_results:
            logger.info(
                "No similar products found for tenant=%s product=%s",
                tenant_id,
                product_id,
            )
            return self._empty_result(
                tenant_id, product_id, sentiment_result, scoring_config
            )

        # Dynamic scoring
        scored_products = self._apply_dynamic_scoring(
            search_results=search_results[:top_k],
            scoring_config=scoring_config,
            sentiment_result=sentiment_result,
        )

        result = MultiTenantRecommendationResult(
            tenant_id=tenant_id,
            client_id=sentiment_result.client_id,
            reference_product_id=product_id,
            sentiment_label=sentiment_result.sentiment_label or "unknown",
            sentiment_score=sentiment_result.sentiment_score,
            recommendations=scored_products,
            total_results=len(scored_products),
            scoring_config_version=scoring_config.version,
            cached=False,
            processed_at=datetime.utcnow(),
        )

        logger.info(
            "recommend_detailed() done: tenant=%s %d results (scoring_config v%d)",
            tenant_id,
            len(scored_products),
            scoring_config.version,
        )
        return result

    # ------------------------------------------------------------------
    # ScoringConfig resolution
    # ------------------------------------------------------------------

    async def _get_scoring_config(self, tenant_id: str) -> ScoringConfig:
        """
        Fetch the active ScoringConfig for *tenant_id* from PostgreSQL.

        Raises:
            ValueError: If no database session is available or no active
                        config exists.
        """
        if self.db is None:
            raise ValueError(
                "MultiTenantRecommendationEngine requires a database session "
                "to resolve the ScoringConfig.  Pass db= at construction time."
            )

        scoring_service = ScoringConfigService(self.db)
        config = await scoring_service.get_active_config(tenant_id)

        if config is None:
            logger.error("No active ScoringConfig for tenant=%s", tenant_id)
            raise ValueError(
                f"No active scoring configuration found for tenant '{tenant_id}'"
            )

        logger.debug(
            "Loaded ScoringConfig for tenant=%s (version=%d, criteria=%d)",
            tenant_id,
            config.version,
            len(config.scoring_criteria),
        )
        return config

    # ------------------------------------------------------------------
    # Dynamic scoring
    # ------------------------------------------------------------------

    def _apply_dynamic_scoring(
        self,
        search_results: List,
        scoring_config: ScoringConfig,
        sentiment_result: SentimentResult,
    ) -> List[ProductScore]:
        """
        Apply dynamic scoring based on the tenant's ScoringConfig JSON.

        Supports two criterion types:

        * **system** -- built-in criteria:
          - ``similarity``: the Qdrant cosine similarity score
          - ``sentiment_boost``: 1.0 for positive, 0.7 for neutral, 0.5 for negative

        * **custom** -- values extracted from the Qdrant payload metadata.
          Missing fields default to 0.0.

        The total score for each product is::

            total_score = sum(weight * value  for each criterion)

        Products are returned sorted by ``total_score`` descending with
        1-based rank assignments.
        """
        scored_products: List[ProductScore] = []

        for result in search_results:
            total_score = 0.0
            criterion_scores: Dict[str, Dict[str, float]] = {}

            for criterion in scoring_config.scoring_criteria:
                criterion_name = criterion["name"]
                weight = float(criterion["weight"])
                criterion_type = criterion["type"]

                if criterion_type == "system":
                    value = self._resolve_system_criterion(
                        criterion_name, result, sentiment_result
                    )
                elif criterion_type == "custom":
                    value = self._resolve_custom_criterion(
                        criterion_name, result.payload
                    )
                else:
                    logger.warning(
                        "Unknown criterion type '%s' for '%s', skipping",
                        criterion_type,
                        criterion_name,
                    )
                    continue

                score_contribution = weight * value
                total_score += score_contribution
                criterion_scores[criterion_name] = {
                    "value": round(value, 4),
                    "weight": weight,
                    "contribution": round(score_contribution, 4),
                }

            # Collect payload metadata (excluding internal vector field)
            payload_metadata = {
                k: v
                for k, v in (result.payload or {}).items()
                if k != "vector"
            }

            scored_products.append(
                ProductScore(
                    product_id=result.payload.get("product_id", str(result.id)),
                    total_score=round(total_score, 4),
                    criterion_scores=criterion_scores,
                    metadata=payload_metadata,
                    rank=0,
                )
            )

        # Sort descending by total_score
        scored_products.sort(key=lambda p: p.total_score, reverse=True)

        # Assign 1-based ranks
        for i, product in enumerate(scored_products):
            product.rank = i + 1

        return scored_products

    # ------------------------------------------------------------------
    # Criterion resolvers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_system_criterion(
        name: str,
        search_result,
        sentiment_result: SentimentResult,
    ) -> float:
        """Resolve a built-in system criterion to a numeric value."""
        if name == "similarity":
            return float(search_result.score)

        if name == "sentiment_boost":
            label = (sentiment_result.sentiment_label or "").lower()
            if label == "positive":
                return 1.0
            if label == "neutral":
                return 0.7
            return 0.5  # negative or unknown

        logger.warning(
            "Unknown system criterion '%s', defaulting to 0.0", name
        )
        return 0.0

    @staticmethod
    def _resolve_custom_criterion(name: str, payload: dict) -> float:
        """Extract a custom criterion value from the Qdrant payload."""
        raw_value = payload.get(name, 0.0)
        try:
            return float(raw_value)
        except (TypeError, ValueError):
            logger.warning(
                "Cannot convert payload field '%s' to float (value=%r), "
                "defaulting to 0.0",
                name,
                raw_value,
            )
            return 0.0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _empty_result(
        self,
        tenant_id: str,
        product_id: str,
        sentiment_result: SentimentResult,
        scoring_config: ScoringConfig,
    ) -> MultiTenantRecommendationResult:
        """Return an empty result when no recommendations are found."""
        return MultiTenantRecommendationResult(
            tenant_id=tenant_id,
            client_id=sentiment_result.client_id,
            reference_product_id=product_id,
            sentiment_label=sentiment_result.sentiment_label or "unknown",
            sentiment_score=sentiment_result.sentiment_score,
            recommendations=[],
            total_results=0,
            scoring_config_version=scoring_config.version,
            cached=False,
            processed_at=datetime.utcnow(),
        )

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all backing services."""
        return {
            "cache": await self.cache.health_check(),
            "embeddings": self.embeddings.health_check(),
            "vectors": self.vectors.health_check(),
        }
