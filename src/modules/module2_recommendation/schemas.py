"""
Schemas for the multi-tenant recommendation module.
Defines data structures for the recommendation workflow.

All vehicle-specific and PostgreSQL-specific schemas have been removed.
Product details are now sourced from Qdrant payload.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProductScore(BaseModel):
    """Score breakdown for a single product after dynamic scoring."""

    product_id: str = Field(..., description="Product identifier from Qdrant payload")
    total_score: float = Field(..., description="Weighted total score")
    criterion_scores: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Per-criterion breakdown: {name: {value, weight, contribution}}",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Full Qdrant payload metadata for this product",
    )
    rank: int = Field(default=0, description="Position in ranking (1-based)")


class MultiTenantRecommendationResult(BaseModel):
    """Final output from the multi-tenant recommendation engine."""

    tenant_id: str = Field(..., description="Tenant that owns these recommendations")
    client_id: str = Field(..., description="Client who requested recommendations")
    reference_product_id: str = Field(
        ..., description="Original product used as reference"
    )
    sentiment_label: str = Field(
        ..., description="Sentiment label from analysis (positive/negative/neutral)"
    )
    sentiment_score: float = Field(
        ..., description="Sentiment score from the original analysis"
    )
    recommendations: List[ProductScore] = Field(
        ..., description="Ranked list of recommendations with dynamic scoring"
    )
    total_results: int = Field(..., description="Total number of results")
    scoring_config_version: int = Field(
        default=1, description="Version of the scoring config used"
    )
    cached: bool = Field(default=False, description="Whether result was from cache")
    cache_key: Optional[str] = Field(None, description="Cache key if cached")
    processed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Processing timestamp"
    )
