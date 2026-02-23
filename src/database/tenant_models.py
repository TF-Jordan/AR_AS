"""
SQLAlchemy models for multi-tenant RaaS platform.
"""

import secrets
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .connection import Base


def generate_api_key() -> str:
    """Generate a unique API key with sk_live_ prefix."""
    return f"sk_live_{secrets.token_urlsafe(32)}"


class Tenant(Base):
    """
    Tenant model - represents a client platform of the RaaS system.
    Stored in the public schema.
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
        default=generate_api_key,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    scoring_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False,
        default=lambda: {
            "criteria": [
                {"name": "similarite", "weight": 0.5},
                {"name": "note", "weight": 0.3},
                {"name": "disponibilite", "weight": 0.2},
            ]
        },
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Tenant(slug={self.slug}, domain={self.domain}, status={self.status})>"


class TenantItem(Base):
    """
    Generic item model for tenant data.
    Uses JSONB for flexible domain-specific attributes.
    This table is created per-tenant schema via raw SQL in tenant_manager.
    This class is used for type reference only.
    """

    __tablename__ = "items"
    __table_args__ = {"schema": "public"}  # Placeholder, actual tables are per-schema

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    embedding_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<TenantItem(id={self.id})>"


class TenantReview(Base):
    """
    Review/comment model for tenant data.
    This table is created per-tenant schema via raw SQL in tenant_manager.
    This class is used for type reference only.
    """

    __tablename__ = "reviews"
    __table_args__ = {"schema": "public"}  # Placeholder, actual tables are per-schema

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    item_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    commentaire: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<TenantReview(id={self.id}, item_id={self.item_id})>"
