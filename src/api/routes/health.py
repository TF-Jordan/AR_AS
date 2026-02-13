"""
Health Check API endpoints.

Provides:
- Comprehensive health check of all services
- Kubernetes liveness probe
- Kubernetes readiness probe (with database, Redis, Qdrant checks)
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.api.schemas import HealthResponse
from src.api.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health status of all services.",
)
async def health_check():
    """
    Comprehensive health check of all system components.

    Checks:
    - Redis cache
    - Qdrant vector database
    - Embedding service
    - Sentiment analyzer
    - Database connection
    """
    from src.modules.module2_recommendation.cache import get_cache_manager
    from src.modules.module2_recommendation.embeddings import get_embedding_service
    from src.modules.module2_recommendation.vector_store import get_vector_store
    from src.modules.module1_sentiment.analyzer import get_sentiment_analyzer
    from sqlalchemy import text
    services = {}

    # Check Redis
    try:
        cache = get_cache_manager()
        services["redis"] = await cache.health_check()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        services["redis"] = False

    # Check Qdrant
    try:
        vectors = get_vector_store()
        services["qdrant"] = vectors.health_check()
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        services["qdrant"] = False

    # Check Embeddings
    try:
        embeddings = get_embedding_service()
        services["embeddings"] = embeddings.health_check()
    except Exception as e:
        logger.error(f"Embeddings health check failed: {e}")
        services["embeddings"] = False

    # Check Sentiment Analyzer
    try:
        analyzer = get_sentiment_analyzer()
        services["sentiment_analyzer"] = analyzer.health_check()
    except Exception as e:
        logger.error(f"Sentiment analyzer health check failed: {e}")
        services["sentiment_analyzer"] = False

    # Check Database
    try:
        from src.database.connection import async_engine
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        services["database"] = False

    overall_status = "healthy" if all(services.values()) else "degraded"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        services=services,
        version=settings.app_version,
    )


@router.get(
    "/live",
    summary="Liveness probe",
    description="Simple liveness check for Kubernetes.",
)
async def liveness():
    """
    Liveness probe -- returns 200 if the process is alive.

    This endpoint performs no dependency checks. If the HTTP server
    can respond, the process is alive.
    """
    return {"status": "alive"}


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Readiness check for Kubernetes with dependency verification.",
)
async def readiness(db: AsyncSession = Depends(get_db_session)):
    """
    Readiness probe -- checks if the application is ready to serve traffic.

    Verifies critical dependencies:
    - **PostgreSQL**: Database connection via SQLAlchemy
    - **Redis**: Cache connection for rate limiting and recommendations
    - **Qdrant**: Vector database connection for similarity search

    Returns 200 if all services are ready, 503 otherwise.
    """
    checks = {}

    # Check PostgreSQL
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        checks["postgresql"] = True
    except Exception as exc:
        logger.error("Readiness: PostgreSQL check failed: %s", exc)
        checks["postgresql"] = False

    # Check Redis
    try:
        from src.modules.module2_recommendation.cache import get_cache_manager
        cache = get_cache_manager()
        checks["redis"] = await cache.health_check()
    except Exception as exc:
        logger.error("Readiness: Redis check failed: %s", exc)
        checks["redis"] = False

    # Check Qdrant
    try:
        from src.modules.module2_recommendation.vector_store import get_vector_store
        vector_store = get_vector_store()
        checks["qdrant"] = vector_store.health_check()
    except Exception as exc:
        logger.error("Readiness: Qdrant check failed: %s", exc)
        checks["qdrant"] = False

    all_ready = all(checks.values())

    if all_ready:
        return {"status": "ready", "checks": checks}

    # Return 503 Service Unavailable if any check fails
    failed = [name for name, ok in checks.items() if not ok]
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "not_ready",
            "checks": checks,
            "failed": failed,
        },
    )
