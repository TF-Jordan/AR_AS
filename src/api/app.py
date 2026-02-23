"""
FastAPI application factory.
Creates and configures the main API application.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api.routes import api_router
from src.api.middleware import CorrelationIdMiddleware
from src.database.connection import close_database, async_engine, Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Create public tables (tenants) if they don't exist
    from src.database.tenant_models import Tenant  # noqa: F401 - register model
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified/created")

    yield
    logger.info("Shutting down application...")
    await close_database()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AR_AS - Recommendation-as-a-Service Platform",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Correlation ID middleware
    application.add_middleware(CorrelationIdMiddleware)

    # Register API routes
    application.include_router(api_router, prefix=settings.api_prefix)

    # Root health check
    @application.get("/health")
    async def root_health():
        return {"status": "healthy", "service": settings.app_name}

    return application


app = create_app()
