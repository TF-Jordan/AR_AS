"""
Database connection and session management.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.engine import Engine

from src.config import settings
from src.utils.context import get_correlation_id

logger = logging.getLogger(__name__)

# Slow query threshold in seconds
SLOW_QUERY_THRESHOLD = 0.1  # 100ms

# Create async engine
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


# ============================================================
# DATABASE QUERY LOGGING
# ============================================================

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    query_start_times = conn.info.get('query_start_time', [])
    if not query_start_times:
        return

    start_time = query_start_times.pop()
    duration_seconds = time.time() - start_time
    duration_ms = duration_seconds * 1000

    query_type = statement.strip().split()[0].upper() if statement else "UNKNOWN"
    is_slow = duration_seconds > SLOW_QUERY_THRESHOLD
    log_level = logging.WARNING if is_slow else logging.DEBUG

    logger.log(
        log_level,
        f"Query executed: {query_type} ({duration_ms:.2f}ms)",
        extra={
            "event": "database_query",
            "query_type": query_type,
            "duration_ms": round(duration_ms, 2),
            "is_slow_query": is_slow,
            "correlation_id": get_correlation_id(),
        },
    )


# ============================================================
# SESSION MANAGEMENT
# ============================================================

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def async_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database() -> None:
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    """Close database connections."""
    await async_engine.dispose()
