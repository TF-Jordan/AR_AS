"""
Configurable Ranking Service for multi-tenant scoring.
Implements weighted scoring based on tenant-defined criteria.
"""

import logging
from typing import Any, Dict, List

from .schemas import SimilarProduct, RankedProduct

logger = logging.getLogger(__name__)


class RankingService:
    """
    Configurable ranking service that uses tenant-defined scoring criteria.

    Each tenant defines criteria like:
        [{"name": "similarite", "weight": 0.5}, {"name": "note", "weight": 0.3}, ...]

    The service computes:
        score_final = SUM(criterion_value_i * weight_i)
    """

    def __init__(self, scoring_criteria: List[Dict[str, Any]]):
        """
        Initialize with tenant-specific scoring criteria.

        Args:
            scoring_criteria: List of {"name": str, "weight": float} dicts
        """
        self.criteria = {c["name"]: c["weight"] for c in scoring_criteria}

        # Normalize weights to sum to 1.0
        total = sum(self.criteria.values())
        if total > 0 and abs(total - 1.0) > 0.01:
            self.criteria = {k: v / total for k, v in self.criteria.items()}

        logger.info(f"RankingService initialized with criteria: {self.criteria}")

    def compute_final_score(
        self,
        criterion_values: Dict[str, float],
    ) -> tuple[float, Dict[str, float]]:
        """
        Compute weighted final score.

        Args:
            criterion_values: Dict mapping criterion name to its value (0-1)

        Returns:
            Tuple of (final_score, score_details per criterion)
        """
        score_details = {}
        final_score = 0.0

        for name, weight in self.criteria.items():
            value = criterion_values.get(name, 0.0)
            contribution = weight * value
            score_details[name] = round(contribution, 4)
            final_score += contribution

        return round(final_score, 4), score_details

    def rank_products(
        self,
        similar_products: List[SimilarProduct],
        items_data: Dict[str, Dict[str, Any]],
    ) -> List[RankedProduct]:
        """
        Rank similar products using tenant-defined criteria.

        Args:
            similar_products: List of similar products from vector search
            items_data: Dict mapping item_id to its JSONB data

        Returns:
            Sorted list of RankedProduct objects
        """
        ranked_products = []

        for similar in similar_products:
            item_data = items_data.get(similar.product_id, {})

            # Build criterion values from item data
            criterion_values = {}
            for criterion_name in self.criteria:
                if criterion_name == "similarite":
                    criterion_values["similarite"] = similar.similarity_score
                else:
                    # Try to extract value from item data, normalize to 0-1
                    raw_value = item_data.get(criterion_name)
                    if raw_value is not None:
                        criterion_values[criterion_name] = self._normalize_value(
                            criterion_name, raw_value
                        )
                    else:
                        criterion_values[criterion_name] = 0.0

            final_score, score_details = self.compute_final_score(criterion_values)

            ranked_product = RankedProduct(
                product_id=similar.product_id,
                similarity_score=round(similar.similarity_score, 4),
                final_score=final_score,
                rank=0,  # Will be set after sorting
                score_details=score_details,
                metadata=item_data,
            )
            ranked_products.append(ranked_product)

        # Sort by final score descending
        ranked_products.sort(key=lambda x: x.final_score, reverse=True)

        # Assign 1-based ranks
        for i, product in enumerate(ranked_products):
            product.rank = i + 1

        logger.info(f"Ranked {len(ranked_products)} products")
        return ranked_products

    @staticmethod
    def _normalize_value(criterion_name: str, value: Any) -> float:
        """
        Normalize a raw value to 0-1 range.
        Handles common criterion types.
        """
        if isinstance(value, bool):
            return 1.0 if value else 0.0

        if isinstance(value, (int, float)):
            # Common patterns: note (0-5), prix (higher=worse), etc.
            if "note" in criterion_name or "rating" in criterion_name:
                return min(float(value) / 5.0, 1.0)
            if "disponibilite" in criterion_name or "disponible" in criterion_name:
                return 1.0 if value else 0.0
            # Default: assume 0-1 already or cap at 1
            return min(max(float(value), 0.0), 1.0)

        return 0.0
