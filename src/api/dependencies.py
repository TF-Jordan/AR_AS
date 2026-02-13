"""
FastAPI dependencies for dependency injection.

Provides database sessions, authentication (Keycloak OAuth2),
Redis clients, rate limiting, and multi-tenant service dependencies.
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.connection import get_async_session

# ---------------------------------------------------------------------------
# Re-export Keycloak auth dependencies for backward compatibility
# and convenience -- routes can import from here or from src.auth.
# ---------------------------------------------------------------------------
from src.auth.keycloak import (  # noqa: F401
    get_token_payload,
    get_current_tenant_id,
    get_current_client_id,
    require_admin,
    security,
)

# Re-export rate limiter dependency
from src.middleware.rate_limiter import (  # noqa: F401
    get_redis,
    rate_limit_dependency,
)


# ---------------------------------------------------------------------------
# Database session dependency
# ---------------------------------------------------------------------------

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database session."""
    async for session in get_async_session():
        yield session


# ---------------------------------------------------------------------------
# Multi-tenant recommendation engine dependency
# ---------------------------------------------------------------------------

async def get_recommendation_engine(
    db: AsyncSession = Depends(get_db_session),
):
    """
    Dependency that returns a MultiTenantRecommendationEngine wired
    with the current request's database session (needed to resolve
    the tenant's ScoringConfig).

    Usage in routes::

        engine = Depends(get_recommendation_engine)
    """
    from src.modules.module2_recommendation.engine import (
        MultiTenantRecommendationEngine,
    )
    from src.modules.module2_recommendation.vector_store import get_vector_store
    from src.modules.module2_recommendation.embeddings import get_embedding_service
    from src.modules.module2_recommendation.cache import get_cache_manager

    return MultiTenantRecommendationEngine(
        db=db,
        cache_manager=get_cache_manager(),
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store(),
    )


# ---------------------------------------------------------------------------
# Product service dependency
# ---------------------------------------------------------------------------

def get_product_service():
    """
    Dependency that returns a ProductService instance.

    Usage in routes::

        service = Depends(get_product_service)
    """
    from src.services.product_service import ProductService
    return ProductService()
