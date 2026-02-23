"""
Schemas for the recommendation module.
Defines data structures for the multi-tenant recommendations workflow.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SimilarProduct(BaseModel):
    """Intermediate structure for similar products from vector search."""

    product_id: str = Field(..., description="Product identifier from PostgreSQL")
    similarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Cosine similarity score"
    )
    vector_id: Optional[str] = Field(None, description="Vector ID in Qdrant")


class RankedProduct(BaseModel):
    """Final ranked product in recommendation result."""

    product_id: str = Field(..., description="Product/item identifier")
    similarity_score: float = Field(..., description="Semantic similarity score")
    final_score: float = Field(..., description="Weighted final score")
    rank: int = Field(..., description="Position in ranking (1-based)")
    score_details: Dict[str, float] = Field(
        default_factory=dict, description="Per-criterion score breakdown"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional item info from JSONB data"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "1",
                "similarity_score": 0.92,
                "final_score": 0.85,
                "rank": 1,
                "score_details": {
                    "similarite": 0.46,
                    "note": 0.28,
                    "disponibilite": 0.20,
                },
                "metadata": {"nom": "Le Bouchon Lyonnais", "note": 4.7},
            }
        }
