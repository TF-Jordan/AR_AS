"""
Pydantic schemas for multi-tenant API request/response validation.

Covers:
- Tenant CRUD operations
- Scoring configuration management
- Product description management
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Scoring Criterion
# =============================================================================

class ScoringCriterion(BaseModel):
    """A single scoring criterion with name, weight, and type."""

    name: str = Field(..., min_length=1, max_length=100, description="Criterion name")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight (0.0 to 1.0)")
    type: str = Field(..., pattern=r"^(system|custom)$", description="Either 'system' or 'custom'")


# =============================================================================
# Tenant Schemas
# =============================================================================

class TenantCreate(BaseModel):
    """Request schema for creating a new tenant."""

    tenant_id: str = Field(
        ..., min_length=1, max_length=100,
        description="Unique external tenant identifier",
    )
    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    domain: Optional[str] = Field(
        None, max_length=100,
        description="Business domain (e.g., 'real-estate', 'automotive')",
    )
    keycloak_client_id: Optional[str] = Field(
        None, max_length=100, description="Keycloak OAuth2 client ID",
    )
    rate_limit_requests: int = Field(100, ge=1, description="Max requests per window")
    rate_limit_window_seconds: int = Field(60, ge=1, description="Rate limit window in seconds")

    # Optional: initial scoring criteria (defaults will be created if omitted)
    initial_scoring_criteria: Optional[List[ScoringCriterion]] = Field(
        None,
        description="Initial scoring configuration. If omitted, a default config is created.",
    )


class TenantUpdate(BaseModel):
    """Request schema for updating an existing tenant."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = Field(None, max_length=100)
    keycloak_client_id: Optional[str] = Field(None, max_length=100)
    rate_limit_requests: Optional[int] = Field(None, ge=1)
    rate_limit_window_seconds: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    """Response schema for tenant data."""

    id: uuid.UUID
    tenant_id: str
    name: str
    domain: Optional[str] = None
    keycloak_client_id: Optional[str] = None
    qdrant_collection_name: str
    rate_limit_requests: int
    rate_limit_window_seconds: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantListResponse(BaseModel):
    """Paginated list of tenants."""

    tenants: List[TenantResponse]
    total: int
    skip: int
    limit: int


# =============================================================================
# Scoring Config Schemas
# =============================================================================

class ScoringConfigCreate(BaseModel):
    """Request schema for creating a scoring configuration."""

    criteria: List[ScoringCriterion] = Field(
        ..., min_length=1, description="List of scoring criteria",
    )
    created_by: Optional[str] = Field(
        None, max_length=255, description="Admin user who created the config",
    )

    @field_validator("criteria")
    @classmethod
    def validate_weights_sum(cls, v: List[ScoringCriterion]) -> List[ScoringCriterion]:
        """Ensure scoring weights sum to 1.0 (with 0.01 tolerance)."""
        total = sum(c.weight for c in v)
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Scoring criteria weights must sum to 1.0 (got {total:.4f})"
            )
        return v


class ScoringConfigResponse(BaseModel):
    """Response schema for scoring configuration."""

    id: uuid.UUID
    tenant_id: str
    scoring_criteria: list
    version: int
    is_active: bool
    created_at: datetime
    created_by: Optional[str] = None

    model_config = {"from_attributes": True}


class ScoringConfigHistoryResponse(BaseModel):
    """List of scoring config versions for a tenant."""

    configs: List[ScoringConfigResponse]
    tenant_id: str


# =============================================================================
# Product Description Schemas
# =============================================================================

class ProductDescriptionCreate(BaseModel):
    """Request schema for creating a product description."""

    product_id: str = Field(
        ..., min_length=1, max_length=255,
        description="External product ID from client system",
    )
    description: str = Field(
        ..., min_length=1, description="Product description for vectorization",
    )
    embedding_model: Optional[str] = Field(
        None, max_length=255,
        description="Embedding model name (e.g., 'paraphrase-multilingual-mpnet-base-v2')",
    )


class ProductDescriptionUpdate(BaseModel):
    """Request schema for updating a product description."""

    description: Optional[str] = Field(None, min_length=1)
    embedding_model: Optional[str] = Field(None, max_length=255)


class ProductDescriptionResponse(BaseModel):
    """Response schema for product description."""

    id: uuid.UUID
    tenant_id: str
    product_id: str
    description: str
    embedding_model: Optional[str] = None
    has_vector: bool = Field(description="Whether a cached vector embedding exists")
    created_at: datetime
    updated_at: datetime
    last_vectorized_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, obj) -> "ProductDescriptionResponse":
        """Build response from ORM model, computing has_vector."""
        return cls(
            id=obj.id,
            tenant_id=obj.tenant_id,
            product_id=obj.product_id,
            description=obj.description,
            embedding_model=obj.embedding_model,
            has_vector=obj.vector_embedding is not None,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            last_vectorized_at=obj.last_vectorized_at,
        )
