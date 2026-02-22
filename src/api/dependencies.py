"""
FastAPI dependencies for dependency injection.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_async_session
from src.modules.module3_orchestration import get_orchestrator, Orchestrator


async def get_db_session() -> AsyncSession:
    """Get database session dependency."""
    async for session in get_async_session():
        yield session


def get_orchestrator_dep() -> Orchestrator:
    """Get orchestrator dependency."""
    return get_orchestrator()
