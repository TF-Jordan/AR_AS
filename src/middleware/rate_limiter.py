"""
Per-tenant rate limiting using Redis.

Implements a sliding-window counter (fixed window with atomic increment)
algorithm backed by Redis. Each tenant has its own rate limit configuration
stored in the database (Tenant.rate_limit_requests, Tenant.rate_limit_window_seconds).

Rate limit headers are attached to responses:
- X-RateLimit-Limit: maximum requests allowed in the window
- X-RateLimit-Remaining: requests remaining in the current window
- X-RateLimit-Reset: seconds until the current window resets
"""

import logging
import time
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response, status
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError, RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.keycloak import get_current_tenant_id
from src.config import settings
from src.database.connection import get_async_session
from src.database.models_multitenant import Tenant

logger = logging.getLogger(__name__)


class TenantRateLimiter:
    """
    Per-tenant rate limiting using Redis fixed-window counters.

    Each tenant gets a Redis key ``rate_limit:{tenant_id}`` whose value
    is atomically incremented on every request. A TTL equal to the
    configured window size is set on key creation, so the counter
    resets automatically when the window expires.

    Args:
        redis_client: An async Redis client instance.
    """

    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client

    async def check_rate_limit(
        self,
        tenant_id: str,
        max_requests: int,
        window_seconds: int,
    ) -> dict:
        """
        Check whether the current request is within the tenant's rate limit.

        Algorithm:
            1. Build the Redis key: ``rate_limit:{tenant_id}``
            2. INCR the counter atomically.
            3. If this is the first request (count == 1), set TTL.
            4. If count exceeds max_requests, raise 429.
            5. Return rate-limit metadata for response headers.

        Args:
            tenant_id: The tenant identifier.
            max_requests: Maximum number of requests allowed per window.
            window_seconds: Length of the rate-limit window in seconds.

        Returns:
            Dictionary with keys:
                - allowed (bool): Whether the request is permitted.
                - limit (int): Maximum requests per window.
                - remaining (int): Requests remaining.
                - reset (int): Seconds until the window resets.

        Raises:
            HTTPException(429): If the rate limit has been exceeded.
        """
        key = f"rate_limit:{tenant_id}"

        try:
            # Atomic increment
            current_count = await self.redis.incr(key)

            # Set TTL on first request in the window
            if current_count == 1:
                await self.redis.expire(key, window_seconds)

            # Get TTL for reset header
            ttl = await self.redis.ttl(key)
            # ttl can be -1 if no expiry set (race condition fallback)
            if ttl < 0:
                await self.redis.expire(key, window_seconds)
                ttl = window_seconds

            remaining = max(0, max_requests - current_count)

            result = {
                "allowed": current_count <= max_requests,
                "limit": max_requests,
                "remaining": remaining,
                "reset": ttl,
            }

            if not result["allowed"]:
                logger.warning(
                    "Rate limit exceeded for tenant %s: %d/%d requests",
                    tenant_id,
                    current_count,
                    max_requests,
                    extra={
                        "event": "rate_limit_exceeded",
                        "tenant_id": tenant_id,
                        "current_count": current_count,
                        "max_requests": max_requests,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "tenant_id": tenant_id,
                        "limit": max_requests,
                        "window_seconds": window_seconds,
                        "retry_after": ttl,
                    },
                    headers={
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(ttl),
                        "Retry-After": str(ttl),
                    },
                )

            return result

        except HTTPException:
            # Re-raise HTTP exceptions (rate limit exceeded)
            raise
        except (RedisConnectionError, RedisError) as exc:
            # If Redis is down, log and allow the request (fail-open)
            logger.error(
                "Redis error during rate limit check for tenant %s: %s. "
                "Failing open -- request allowed.",
                tenant_id,
                exc,
                extra={
                    "event": "rate_limit_redis_error",
                    "tenant_id": tenant_id,
                },
            )
            return {
                "allowed": True,
                "limit": max_requests,
                "remaining": max_requests,
                "reset": window_seconds,
            }


# ---------------------------------------------------------------------------
# Redis dependency
# ---------------------------------------------------------------------------

_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """
    Get or create the async Redis client singleton.

    Uses the Redis connection settings from the application configuration.

    Returns:
        An async Redis client instance.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        logger.info(
            "Redis client initialized for rate limiting",
            extra={
                "redis_host": settings.redis_host,
                "redis_port": settings.redis_port,
            },
        )
    return _redis_client


async def close_redis() -> None:
    """Close the Redis client connection if it exists."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis rate-limit client closed")


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def rate_limit_dependency(
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
) -> None:
    """
    FastAPI dependency for per-tenant rate limiting.

    Steps:
        1. Look up the tenant in the database to get rate limit config.
        2. If tenant not found or inactive, reject with 403.
        3. Check the rate limit via TenantRateLimiter.
        4. Attach rate limit headers to the request state for the
           response middleware to pick up.

    Usage::

        @router.get("/data", dependencies=[Depends(rate_limit_dependency)])
        async def get_data(...):
            ...

    Args:
        request: The incoming FastAPI request.
        tenant_id: Extracted from the JWT token.
        db: Async database session.
        redis: Async Redis client.
    """
    # Fetch tenant rate-limit configuration from database
    result = await db.execute(
        select(Tenant).where(
            Tenant.tenant_id == tenant_id,
            Tenant.is_active.is_(True),
        )
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        logger.warning(
            "Tenant not found or inactive: %s",
            tenant_id,
            extra={"event": "tenant_not_found", "tenant_id": tenant_id},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant '{tenant_id}' not found or inactive.",
        )

    max_requests = tenant.rate_limit_requests
    window_seconds = tenant.rate_limit_window_seconds

    # Check rate limit
    limiter = TenantRateLimiter(redis)
    rate_info = await limiter.check_rate_limit(
        tenant_id=tenant_id,
        max_requests=max_requests,
        window_seconds=window_seconds,
    )

    # Store rate limit info on request state so it can be added to
    # response headers by middleware or afterware
    request.state.rate_limit_info = rate_info
