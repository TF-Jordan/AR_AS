"""
Repository pattern implementation for database operations.
"""

from typing import List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Base, Comment

T = TypeVar("T", bound=Base)


class BaseRepository:
    """Base repository with common CRUD operations."""

    def __init__(self, model: Type[T]):
        self.model = model

    async def get_by_id(
        self, session: AsyncSession, id_value: UUID
    ) -> Optional[T]:
        result = await session.execute(
            select(self.model).where(self.model.id == id_value)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        result = await session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def create(self, session: AsyncSession, entity: T) -> T:
        session.add(entity)
        await session.flush()
        await session.refresh(entity)
        return entity

    async def delete(self, session: AsyncSession, entity: T) -> bool:
        await session.delete(entity)
        await session.flush()
        return True


class CommentRepository(BaseRepository):
    """Repository for Comment operations."""

    def __init__(self):
        super().__init__(Comment)

    async def get_by_product(
        self, session: AsyncSession, product_id: str, product_type: str
    ) -> List[Comment]:
        result = await session.execute(
            select(Comment)
            .where(Comment.product_id == product_id)
            .where(Comment.product_type == product_type)
            .order_by(Comment.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_client(
        self, session: AsyncSession, client_id: str
    ) -> List[Comment]:
        result = await session.execute(
            select(Comment)
            .where(Comment.client_id == client_id)
            .order_by(Comment.created_at.desc())
        )
        return list(result.scalars().all())


# Repository instances
comment_repository = CommentRepository()
