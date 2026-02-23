"""
Redis Cache Manager for recommendation results.
Implements cache verification with sentiment score tolerance.
Multi-tenant: keys are namespaced per tenant (tenant:{slug}:...).
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

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Redis cache manager for recommendation results.
    Multi-tenant: all keys are namespaced with tenant:{slug}: prefix.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.redis_url
        self._client: Optional[redis.Redis] = None
        self.ttl_seconds = CACHE_TTL_SECONDS
        self.sentiment_tolerance = SENTIMENT_SCORE_TOLERANCE

    async def connect(self) -> None:
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Redis cache connection established")

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")
        return self._client

    def _generate_cache_key(
        self,
        tenant_slug: str,
        item_id: str,
        client_id: str,
        sentiment_score: float,
    ) -> str:
        """Generate tenant-namespaced cache key."""
        score_bucket = round(sentiment_score / self.sentiment_tolerance) * self.sentiment_tolerance
        key_data = f"{item_id}:{client_id}:{score_bucket:.2f}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:16]
        return f"{CacheKeyPrefix.TENANT.value}:{tenant_slug}:{CacheKeyPrefix.RECOMMENDATION.value}:{key_hash}"

    def _generate_product_key(self, tenant_slug: str, item_id: str) -> str:
        """Generate tenant-namespaced product key."""
        return f"{CacheKeyPrefix.TENANT.value}:{tenant_slug}:{CacheKeyPrefix.PRODUCT.value}:{item_id}"

    async def get_cached_result(
        self, tenant_slug: str, item_id: str, client_id: str, sentiment_score: float
    ) -> Optional[dict]:
        """
        Check cache for existing recommendation result.

        Args:
            tenant_slug: Tenant slug for namespace isolation
            item_id: Item/product ID
            client_id: Client ID
            sentiment_score: Sentiment score

        Returns:
            Cached result dict if found, None otherwise
        """
        start_time = time.time()
        await self.connect()

        try:
            # Try exact match
            cache_key = self._generate_cache_key(tenant_slug, item_id, client_id, sentiment_score)
            cached_data = await self.client.get(cache_key)
            if cached_data:
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    "Cache hit (exact)",
                    extra={
                        "event": "cache_get",
                        "cache_hit": True,
                        "cache_hit_type": "exact",
                        "duration_ms": round(duration_ms, 2),
                        "tenant_slug": tenant_slug,
                        "correlation_id": get_correlation_id(),
                    }
                )
                result = json.loads(cached_data)
                result["cached"] = True
                return result

            # Try fuzzy match
            for delta in [-self.sentiment_tolerance, self.sentiment_tolerance]:
                nearby_score = sentiment_score + delta
                if -1.0 <= nearby_score <= 1.0:
                    fuzzy_key = self._generate_cache_key(tenant_slug, item_id, client_id, nearby_score)
                    cached_data = await self.client.get(fuzzy_key)
                    if cached_data:
                        duration_ms = (time.time() - start_time) * 1000
                        logger.info(
                            "Cache hit (fuzzy)",
                            extra={
                                "event": "cache_get",
                                "cache_hit": True,
                                "cache_hit_type": "fuzzy",
                                "duration_ms": round(duration_ms, 2),
                                "tenant_slug": tenant_slug,
                                "correlation_id": get_correlation_id(),
                            }
                        )
                        result = json.loads(cached_data)
                        result["cached"] = True
                        return result

            # Try product-only match
            product_key = self._generate_product_key(tenant_slug, item_id)
            product_cache = await self.client.get(product_key)
            if product_cache:
                cached_result = json.loads(product_cache)
                cached_sentiment = cached_result.get("sentiment_query", 0)
                if abs(cached_sentiment - sentiment_score) <= self.sentiment_tolerance:
                    duration_ms = (time.time() - start_time) * 1000
                    logger.info(
                        "Cache hit (product)",
                        extra={
                            "event": "cache_get",
                            "cache_hit": True,
                            "cache_hit_type": "product",
                            "duration_ms": round(duration_ms, 2),
                            "tenant_slug": tenant_slug,
                            "correlation_id": get_correlation_id(),
                        }
                    )
                    cached_result["cached"] = True
                    return cached_result

            # Cache miss
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "Cache miss",
                extra={
                    "event": "cache_get",
                    "cache_hit": False,
                    "duration_ms": round(duration_ms, 2),
                    "tenant_slug": tenant_slug,
                    "correlation_id": get_correlation_id(),
                }
            )
            return None

        except Exception as e:
            logger.error(f"Cache lookup error: {e}")
            return None

    async def store_result(
        self,
        tenant_slug: str,
        item_id: str,
        client_id: str,
        sentiment_score: float,
        result: dict,
    ) -> bool:
        """
        Store recommendation result in cache.

        Args:
            tenant_slug: Tenant slug
            item_id: Item ID
            client_id: Client ID
            sentiment_score: Sentiment score
            result: Result dict to cache

        Returns:
            True if stored successfully
        """
        await self.connect()

        try:
            result_json = json.dumps(result, ensure_ascii=False, default=str)

            # Store with full key
            cache_key = self._generate_cache_key(tenant_slug, item_id, client_id, sentiment_score)
            await self.client.setex(cache_key, self.ttl_seconds, result_json)

            # Also store product-level cache
            product_key = self._generate_product_key(tenant_slug, item_id)
            await self.client.setex(product_key, self.ttl_seconds, result_json)

            logger.info(f"Cache stored: {cache_key}")
            return True

        except Exception as e:
            logger.error(f"Cache store error: {e}")
            return False

    async def invalidate_tenant(self, tenant_slug: str) -> int:
        """Invalidate all cache entries for a tenant."""
        await self.connect()
        try:
            pattern = f"{CacheKeyPrefix.TENANT.value}:{tenant_slug}:*"
            keys_deleted = 0
            async for key in self.client.scan_iter(match=pattern):
                await self.client.delete(key)
                keys_deleted += 1
            logger.info(f"Invalidated {keys_deleted} cache entries for tenant {tenant_slug}")
            return keys_deleted
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return 0

    async def invalidate_item(self, tenant_slug: str, item_id: str) -> int:
        """Invalidate cache entries for a specific item."""
        await self.connect()
        try:
            product_key = self._generate_product_key(tenant_slug, item_id)
            await self.client.delete(product_key)
            return 1
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return 0

    async def health_check(self) -> bool:
        try:
            await self.connect()
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Singleton instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
