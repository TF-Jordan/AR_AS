"""
Database session utilities for the multi-tenant RaaS platform.

Provides async session dependency injection and context managers
for use in services and API routes.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from .connection import AsyncSessionLocal, async_session_context


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.

    Usage in route handlers::

        @router.get("/tenants")
        async def list_tenants(db: AsyncSession = Depends(get_db)):
            ...

    The session auto-commits on success and rolls back on exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


__all__ = ["get_db", "async_session_context"]
