"""
FastAPI dependencies for dependency injection.

Provides database sessions, authentication (Keycloak OAuth2),
Redis clients, and rate limiting dependencies.
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
