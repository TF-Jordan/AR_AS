"""
API schemas for request/response validation.

Updated for multi-tenant architecture:
- RecommendationRequestSchema now uses tenant_id instead of product_type
- New ProductUpload / ProductBatchUpload schemas for product management
- New multi-tenant recommendation response schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Sentiment schemas (Module 1 -- unchanged)
# =============================================================================

class SentimentOnlyRequest(BaseModel):
    """Schema for sentiment-only analysis."""

    product_id: str = Field(..., description="Product identifier")
    client_id: str = Field(..., description="Client identifier")
    commentaire: str = Field(..., description="Comment text")
    product_type: Optional[str] = Field(None, description="Product type")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "product_001",
                "client_id": "client_123",
                "commentaire": "Service rapide et efficace",
            }
        }


class SentimentResponse(BaseModel):
    """Response schema for sentiment analysis."""

    client_id: str
    product_id: str
    sentiment_score: float
    sentiment_label: str
    confidence: Optional[float] = None


# =============================================================================
# Multi-tenant Recommendation schemas
# =============================================================================

class RecommendationRequest(BaseModel):
    """
    Multi-tenant recommendation request.

    The tenant_id is typically injected from the OAuth2 token,
    so it may not appear in the request body.
    """

    client_id: str = Field(..., description="Client identifier")
    product_id: str = Field(..., description="Reference product ID")
    comment: str = Field(..., description="Comment text for sentiment analysis")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results")
    filters: Optional[Dict[str, Any]] = Field(
        None, description="Optional Qdrant payload filters"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "client_123",
                "product_id": "product_001",
                "comment": "Excellent produit, tres satisfait!",
                "top_k": 10,
                "filters": None,
            }
        }


class ProductScoreResponse(BaseModel):
    """Response schema for a dynamically scored product."""

    product_id: str
    total_score: float
    criterion_scores: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    rank: int


class RecommendationResponse(BaseModel):
    """
    Multi-tenant recommendation response.

    Returns the client_id and an ordered list of recommended product_ids.
    For detailed score breakdowns, use RecommendationDetailedResponse.
    """

    client_id: str
    product_ids: List[str]


class RecommendationDetailedResponse(BaseModel):
    """Multi-tenant recommendation response with full scoring details."""

    tenant_id: str
    client_id: str
    reference_product_id: str
    sentiment_label: str
    sentiment_score: float
    recommendations: List[ProductScoreResponse]
    total_results: int
    scoring_config_version: int
    cached: bool
    processed_at: datetime


class FullWorkflowResponse(BaseModel):
    """Response schema for complete workflow (sentiment + recommendation)."""

    status: str
    processing_time_seconds: float
    sentiment: SentimentResponse
    recommendations: RecommendationDetailedResponse


# =============================================================================
# Product Upload schemas
# =============================================================================

class ProductUpload(BaseModel):
    """Schema for a single product upload."""

    product_id: str = Field(..., description="Product identifier")
    description: str = Field(..., description="Product description for vectorization")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Custom fields for scoring"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "product_001",
                "description": "Appartement 3 pieces, centre-ville, lumineux",
                "metadata": {"price_match": 0.8, "location_proximity": 0.9},
            }
        }


class ProductBatchUpload(BaseModel):
    """Schema for batch product upload."""

    products: List[ProductUpload] = Field(
        ..., min_length=1, description="List of products to upload"
    )


class ProductUploadResponse(BaseModel):
    """Response schema for product upload."""

    tenant_id: str
    uploaded: int
    errors: int
    error_details: Optional[List[str]] = None


class ProductDeleteResponse(BaseModel):
    """Response schema for product deletion."""

    tenant_id: str
    product_id: str
    deleted: bool


class ProductStatsResponse(BaseModel):
    """Response schema for product collection statistics."""

    tenant_id: str
    collection_name: str
    vectors_count: Optional[int] = None
    points_count: Optional[int] = None
    status: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# Health / Error schemas (unchanged)
# =============================================================================

class HealthResponse(BaseModel):
    """Response for health check."""

    status: str
    timestamp: datetime
    services: Dict[str, bool]
    version: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    status_code: int
