"""
FastAPI application factory.
Creates and configures the main API application.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import settings
from src.logging_config import configure_logging
from src.database.connection import init_database, close_database
from .routes import api_router
from .middleware import CorrelationIdMiddleware, RequestLoggingMiddleware

# Initialize logging before anything else
configure_logging()

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting application...")

    # Initialize database
    try:
        await init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Initialize Redis connection
    try:
        from src.modules.module2_recommendation import get_cache_manager
        cache = get_cache_manager()
        await cache.connect()
        logger.info("Redis cache connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Close database connections
    await close_database()

    # Close Redis connection
    try:
        from src.modules.module2_recommendation import get_cache_manager
        cache = get_cache_manager()
        await cache.disconnect()
    except Exception:
        pass

    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        description="""
        # Multi-Tenant RaaS Platform

        A modular Recommendation-as-a-Service platform with sentiment analysis.

        ## Features

        - **Sentiment Analysis (Module 1)**: Analyzes customer comments using fine-tuned distil-camembert
        - **Recommendation Engine (Module 2)**: Generates semantic similarity-based recommendations
        - **Livreur Ranking (Module 4)**: Multi-criteria ranking of delivery persons using AHP + TOPSIS

        ## Architecture

        - FastAPI for API
        - PostgreSQL for data storage
        - Redis for caching
        - Qdrant for vector similarity search
        - Keycloak for authentication
        """,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure properly in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Correlation ID middleware (must be early to propagate to all logs)
    app.add_middleware(CorrelationIdMiddleware)
    logger.info("CorrelationIdMiddleware registered")

    # Request logging middleware (logs all HTTP requests/responses)
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("RequestLoggingMiddleware registered")

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.debug else "An error occurred",
            },
        )

    # Include API router
    app.include_router(api_router, prefix=settings.api_prefix)

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/health",
        }

    # Health endpoint (root level for Docker healthcheck)
    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "healthy"}

    return app


# Application instance
app = create_app()
