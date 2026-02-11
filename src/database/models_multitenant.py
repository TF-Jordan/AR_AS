"""
Multi-tenant SQLAlchemy models for the RaaS platform.

Defines the core multi-tenant schema:
- Tenant: Organization/client that uses the platform
- ScoringConfig: Per-tenant dynamic scoring criteria with versioning
- ProductDescription: Per-tenant product data with optional vector cache
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .connection import Base


def _utcnow() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


# =============================================================================
# Tenant Model
# =============================================================================

class Tenant(Base):
    """
    Represents a tenant (organization/client) on the RaaS platform.

    Each tenant has its own Qdrant collection, scoring configuration,
    and set of product descriptions. Tenants are identified externally
    by their ``tenant_id`` string and authenticated via Keycloak.
    """

    __tablename__ = "tenants"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # External tenant identifier (used in APIs and Qdrant collection names)
    tenant_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False,
    )

    # Display name
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Business domain (e.g., "real-estate", "automotive", "e-commerce")
    domain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # OAuth2 / Keycloak configuration
    keycloak_client_id: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, nullable=True,
    )

    # Qdrant collection name — format: "tenant_{tenant_id}"
    qdrant_collection_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )

    # Rate limiting
    rate_limit_requests: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False,
    )
    rate_limit_window_seconds: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False,
    )

    # ----- Relationships -----
    scoring_configs: Mapped[List["ScoringConfig"]] = relationship(
        "ScoringConfig",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    products: Mapped[List["ProductDescription"]] = relationship(
        "ProductDescription",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Tenant(tenant_id={self.tenant_id!r}, name={self.name!r})>"


# =============================================================================
# ScoringConfig Model
# =============================================================================

class ScoringConfig(Base):
    """
    Per-tenant dynamic scoring configuration with versioning.

    Each tenant can define weighted scoring criteria (e.g., similarity,
    price_match, location_proximity). Only one configuration is active
    at a time per tenant; updating creates a new version.

    ``scoring_criteria`` JSON format::

        [
            {"name": "similarity", "weight": 0.70, "type": "system"},
            {"name": "price_match", "weight": 0.20, "type": "custom"},
            {"name": "location_proximity", "weight": 0.10, "type": "custom"}
        ]
    """

    __tablename__ = "scoring_configs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Foreign key to Tenant
    tenant_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Dynamic scoring criteria stored as JSON array
    scoring_criteria: Mapped[dict] = mapped_column(
        JSON, nullable=False,
    )

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Only one active config per tenant at a time
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True,
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False,
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
    )

    # ----- Relationships -----
    tenant: Mapped["Tenant"] = relationship(
        "Tenant", back_populates="scoring_configs",
    )

    __table_args__ = (
        # Partial unique index: only one active config per tenant
        Index(
            "ix_scoring_configs_active_tenant",
            "tenant_id",
            unique=True,
            postgresql_where=(is_active.is_(True)),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ScoringConfig(tenant_id={self.tenant_id!r}, "
            f"version={self.version}, active={self.is_active})>"
        )


# =============================================================================
# ProductDescription Model
# =============================================================================

class ProductDescription(Base):
    """
    Per-tenant product description with optional cached vector embedding.

    Products belong to a tenant and are uniquely identified by the
    combination of ``tenant_id`` and ``product_id``. The vector
    embedding can be cached to avoid repeated computation.
    """

    __tablename__ = "product_descriptions"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Foreign key to Tenant
    tenant_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # External product ID from the client's system
    product_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
    )

    # Product description text (used for vectorization)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional: cached vector embedding to avoid re-computation
    vector_embedding: Mapped[Optional[list]] = mapped_column(
        ARRAY(Float), nullable=True,
    )

    # Model used to produce the embedding
    embedding_model: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False,
    )
    last_vectorized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # ----- Relationships -----
    tenant: Mapped["Tenant"] = relationship(
        "Tenant", back_populates="products",
    )

    __table_args__ = (
        # Unique product per tenant
        UniqueConstraint("tenant_id", "product_id", name="uq_tenant_product"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProductDescription(tenant_id={self.tenant_id!r}, "
            f"product_id={self.product_id!r})>"
        )
