"""
API schemas for request/response validation.
Multi-tenant RaaS platform.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==============================================================================
# Tenant API Request Schemas
# ==============================================================================

class ImportItemsRequest(BaseModel):
    """Import items into tenant's data store."""

    items: List[Dict[str, Any]] = Field(
        ..., min_length=1, max_length=1000,
        description="List of items. Each item must have an 'id' field.",
    )
    vectorize: bool = Field(
        default=True,
        description="Whether to generate embeddings and index in Qdrant",
    )


class RecommendationRequest(BaseModel):
    """Recommendation request for a tenant."""

    query: str = Field(
        ..., min_length=1, max_length=2000,
        description="User query / description of what they are looking for",
    )
    top_k: int = Field(
        default=10, ge=1, le=100,
        description="Number of recommendations to return",
    )
    client_id: str = Field(
        default="anonymous",
        description="Client identifier for tracking",
    )


class SentimentOnlyRequest(BaseModel):
    """Sentiment analysis request."""

    commentaire: str = Field(
        ..., min_length=1, description="Comment text to analyze"
    )
    product_id: str = Field(default="", description="Optional product identifier")
    client_id: str = Field(default="anonymous", description="Client identifier")


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
    similarity_score: float
    final_score: float
    rank: int
    score_details: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecommendationResponse(BaseModel):
    """Recommendation results."""

    status: str
    tenant: str
    recommendations: List[RankedProductResponse]
    total_results: int
    sentiment_query: float = 0.0
    sentiment_label: Optional[str] = None
    temps_traitement_ms: float = 0.0
    cached: bool = False


class ImportResponse(BaseModel):
    """Import items response."""

    status: str
    items_imported: int
    vectors_indexed: int
    tenant: str


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
