"""
API schemas for request/response validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.config.constants import ProductType


# ==============================================================================
# Request Schemas
# ==============================================================================

class RecommendationRequestSchema(BaseModel):
    """Full recommendation request (sentiment + recommendation)."""

    product_id: str = Field(..., description="Product identifier")
    client_id: str = Field(..., description="Client identifier")
    commentaire: str = Field(
        ..., min_length=1, description="Comment text to analyze"
    )
    product_type: ProductType = Field(
        ..., description="Type of product"
    )
    top_k: int = Field(
        default=10, ge=1, le=100, description="Number of recommendations"
    )


class RecommendationOnlyRequest(BaseModel):
    """Recommendation request with pre-computed sentiment score."""

    product_id: str = Field(..., description="Product identifier")
    client_id: str = Field(..., description="Client identifier")
    sentiment_score: float = Field(
        ..., ge=-1.0, le=1.0, description="Pre-computed sentiment score"
    )
    product_type: ProductType = Field(
        ..., description="Type of product"
    )
    top_k: int = Field(
        default=10, ge=1, le=100, description="Number of recommendations"
    )


class SentimentOnlyRequest(BaseModel):
    """Sentiment analysis request."""

    product_id: str = Field(..., description="Product identifier")
    client_id: str = Field(..., description="Client identifier")
    commentaire: str = Field(
        ..., min_length=1, description="Comment text to analyze"
    )
    product_type: Optional[str] = Field(
        default=None, description="Type of product (optional)"
    )


# ==============================================================================
# Response Schemas
# ==============================================================================

class SentimentResponse(BaseModel):
    """Sentiment analysis result."""

    client_id: str
    product_id: str
    sentiment_score: float
    sentiment_label: str
    confidence: float


class RankedProductResponse(BaseModel):
    """Individual ranked product in recommendation results."""

    product_id: str
    product_type: str
    similarity_score: float
    availability_score: float
    reputation_score: float
    final_score: float
    rank: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecommendationResponse(BaseModel):
    """Recommendation results."""

    client_id: str
    reference_product_id: str
    sentiment_score: float
    product_type: str
    recommendations: List[RankedProductResponse]
    total_results: int
    cached: bool = False
    processed_at: Optional[datetime] = None


class FullWorkflowResponse(BaseModel):
    """Complete workflow response (sentiment + recommendations)."""

    status: str
    processing_time_seconds: Optional[float] = None
    sentiment: Optional[Dict[str, Any]] = None
    recommendations: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: Optional[datetime] = None
    services: Dict[str, Any] = Field(default_factory=dict)
    version: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str
    status_code: Optional[int] = None
