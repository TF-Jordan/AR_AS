"""
Redis Cache Manager for recommendation results.
Implements cache verification with sentiment score tolerance.

Updated for multi-tenant architecture:
- Cache keys are tenant-scoped
- Works with MultiTenantRecommendationResult
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import redis.asyncio as redis

from src.config import settings, SENTIMENT_SCORE_TOLERANCE, CACHE_TTL_SECONDS
from src.config.constants import CacheKeyPrefix
from src.utils.context import get_correlation_id
from .schemas import MultiTenantRecommendationResult

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Redis cache manager for recommendation results.

    Implements:
    1. Tenant-scoped cache keys
    2. Exact match lookup by tenant_id, product_id, client_id, sentiment_score
    3. Cache storage with configurable TTL
    """

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize cache manager with Redis connection."""
        self.redis_url = redis_url or settings.redis_url
        self._client: Optional[redis.Redis] = None
        self.ttl_seconds = CACHE_TTL_SECONDS
        self.sentiment_tolerance = SENTIMENT_SCORE_TOLERANCE

    async def connect(self) -> None:
        """Establish Redis connection (idempotent - only connects once)."""
        if self._client is not None:
            return
        self._client = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("Redis cache connection established")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis cache connection closed")

    @property
    def client(self) -> redis.Redis:
        """Get Redis client, ensuring connection."""
        if self._client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")
        return self._client

    def _generate_cache_key(
        self,
        tenant_id: str,
        product_id: str,
        client_id: str,
        sentiment_score: float,
    ) -> str:
        """
        Generate tenant-scoped cache key from request parameters.

        Uses sentiment score interval for fuzzy matching.
        """
        score_bucket = round(
            sentiment_score / self.sentiment_tolerance
        ) * self.sentiment_tolerance

        key_data = f"{tenant_id}:{product_id}:{client_id}:{score_bucket:.2f}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:16]

        return f"{CacheKeyPrefix.RECOMMENDATION.value}:{tenant_id}:{key_hash}"

    def _generate_product_key(self, tenant_id: str, product_id: str) -> str:
        """Generate key for product-only lookup (tenant-scoped)."""
        return f"{CacheKeyPrefix.PRODUCT.value}:{tenant_id}:{product_id}"

    async def get_cached_result(
        self,
        tenant_id: str,
        product_id: str,
        client_id: str,
        sentiment_score: float,
    ) -> Optional[MultiTenantRecommendationResult]:
        """
        Check cache for existing recommendation result.

        Args:
            tenant_id: Tenant identifier.
            product_id: Product identifier.
            client_id: Client identifier.
            sentiment_score: Sentiment score for bucketing.

        Returns:
            Cached result if found, None otherwise.
        """
        start_time = time.time()
        await self.connect()

        try:
            cache_key = self._generate_cache_key(
                tenant_id, product_id, client_id, sentiment_score
            )

            cached_data = await self.client.get(cache_key)
            if cached_data:
                logger.info("Cache hit (exact): %s", cache_key)
                result = MultiTenantRecommendationResult.model_validate_json(
                    cached_data
                )
                result.cached = True
                result.cache_key = cache_key

                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    "Cache operation completed",
                    extra={
                        "event": "cache_get",
                        "metric_type": "cache_operation",
                        "operation": "get",
                        "cache_hit": True,
                        "cache_hit_type": "exact",
                        "duration_ms": round(duration_ms, 2),
                        "tenant_id": tenant_id,
                        "product_id": product_id,
                        "correlation_id": get_correlation_id(),
                    },
                )
                return result

            # Cache miss
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "Cache miss",
                extra={
                    "event": "cache_get",
                    "metric_type": "cache_operation",
                    "operation": "get",
                    "cache_hit": False,
                    "duration_ms": round(duration_ms, 2),
                    "tenant_id": tenant_id,
                    "product_id": product_id,
                    "correlation_id": get_correlation_id(),
                },
            )
            return None

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Cache lookup error: %s",
                e,
                extra={
                    "event": "cache_error",
                    "metric_type": "cache_operation",
                    "operation": "get",
                    "error": str(e),
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": get_correlation_id(),
                },
            )
            return None

    async def store_result(
        self,
        tenant_id: str,
        product_id: str,
        client_id: str,
        sentiment_score: float,
        result: MultiTenantRecommendationResult,
    ) -> bool:
        """
        Store recommendation result in cache.

        Args:
            tenant_id: Tenant identifier.
            product_id: Product identifier.
            client_id: Client identifier.
            sentiment_score: Sentiment score for bucketing.
            result: Recommendation result to cache.

        Returns:
            True if stored successfully.
        """
        start_time = time.time()
        await self.connect()

        try:
            cache_key = self._generate_cache_key(
                tenant_id, product_id, client_id, sentiment_score
            )

            result_json = result.model_dump_json()
            data_size_bytes = len(result_json.encode("utf-8"))

            await self.client.setex(
                cache_key,
                self.ttl_seconds,
                result_json,
            )

            # Also store product-level cache
            product_key = self._generate_product_key(tenant_id, product_id)
            await self.client.setex(
                product_key,
                self.ttl_seconds,
                result_json,
            )

            duration_ms = (time.time() - start_time) * 1000

            logger.info(
                "Cache store completed: %s",
                cache_key,
                extra={
                    "event": "cache_set",
                    "metric_type": "cache_operation",
                    "operation": "set",
                    "duration_ms": round(duration_ms, 2),
                    "data_size_bytes": data_size_bytes,
                    "ttl_seconds": self.ttl_seconds,
                    "tenant_id": tenant_id,
                    "product_id": product_id,
                    "correlation_id": get_correlation_id(),
                },
            )
            return True

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Cache store error: %s",
                e,
                extra={
                    "event": "cache_error",
                    "metric_type": "cache_operation",
                    "operation": "set",
                    "error": str(e),
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": get_correlation_id(),
                },
            )
            return False

    async def invalidate(
        self,
        product_id: str,
        product_type: str,
        client_id: Optional[str] = None,
    ) -> int:
        """
        Invalidate cache entries for a product.

        In multi-tenant mode, product_type is typically the tenant_id.

        Args:
            product_id: Product to invalidate.
            product_type: Tenant ID (used as namespace).
            client_id: Optional specific client to invalidate.

        Returns:
            Number of keys deleted.
        """
        await self.connect()

        try:
            pattern = f"{CacheKeyPrefix.RECOMMENDATION.value}:{product_type}:*"
            keys_deleted = 0

            async for key in self.client.scan_iter(match=pattern):
                await self.client.delete(key)
                keys_deleted += 1

            # Also invalidate product key
            product_key = self._generate_product_key(product_type, product_id)
            await self.client.delete(product_key)
            keys_deleted += 1

            logger.info("Invalidated %d cache entries", keys_deleted)
            return keys_deleted

        except Exception as e:
            logger.error("Cache invalidation error: %s", e)
            return 0

    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            await self.connect()
            await self.client.ping()
            return True
        except Exception as e:
            logger.error("Redis health check failed: %s", e)
            return False


# Singleton instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create singleton cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
