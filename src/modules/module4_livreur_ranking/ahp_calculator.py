"""
AHP Calculator - Phase 2 of Module 4

Implements Analytic Hierarchy Process (AHP) for calculating criteria weights.

Ordre des critères:
1. Proximité géographique (le plus important)
2. Capacité de transport
3. Type de véhicule
4. Réputation
"""

import logging
import numpy as np
from typing import Any, Dict, Tuple

from .constants import (
    AHP_MATRICES,
    RANDOM_INDEX,
    AHP_CONSISTENCY_THRESHOLD,
    TypeLivraison,
    CRITERIA_NAMES,
)

logger = logging.getLogger(__name__)


class AHPCalculator:
    """
    Implements the Analytic Hierarchy Process (AHP) for criteria weighting.

    Based on Thomas Saaty's method:
    1. Build pairwise comparison matrix
    2. Calculate weights (eigenvector method or column averaging)
    3. Check consistency (CR < 0.1)

    Ordre des critères: [proximité, capacité, type_véhicule, réputation]
    """

    def __init__(self):
        """Initialize AHP calculator."""
        self.n_criteria = len(CRITERIA_NAMES)

    def build_comparison_matrix(
        self,
        type_livraison: TypeLivraison
    ) -> np.ndarray:
        """
        Build the pairwise comparison matrix for the given delivery type.

        Args:
            type_livraison: Type of delivery (standard/express/sameday)

        Returns:
            4x4 comparison matrix A where A[i,j] represents the importance
            of criterion i relative to criterion j

        Matrix structure (ordre: proximité, capacité, type_véhicule, réputation):
                    Prox    Cap     Type    Rep
            Prox    1       a12     a13     a14
            Cap     1/a12   1       a23     a24
            Type    1/a13   1/a23   1       a34
            Rep     1/a14   1/a24   1/a34   1
        """
        # Get predefined comparisons for this delivery type
        comparisons = AHP_MATRICES[type_livraison]

        # Initialize matrix with ones on diagonal
        matrix = np.ones((4, 4))

        # Fill upper triangle
        # Row 0: Proximité vs autres
        matrix[0, 1] = comparisons["proximite_vs_capacite"]
        matrix[0, 2] = comparisons["proximite_vs_type_vehicule"]
        matrix[0, 3] = comparisons["proximite_vs_reputation"]

        # Row 1: Capacité vs autres
        matrix[1, 2] = comparisons["capacite_vs_type_vehicule"]
        matrix[1, 3] = comparisons["capacite_vs_reputation"]

        # Row 2: Type véhicule vs réputation
        matrix[2, 3] = comparisons["type_vehicule_vs_reputation"]

        # Fill lower triangle (reciprocal values)
        for i in range(4):
            for j in range(i + 1, 4):
                matrix[j, i] = 1.0 / matrix[i, j]

        logger.debug(f"Comparison matrix for {type_livraison}:\n{matrix}")

        return matrix

    def calculate_weights(
        self,
        matrix: np.ndarray
    ) -> np.ndarray:
        """
        Calculate criteria weights using column averaging method.

        Method:
        1. Normalize each column (divide by column sum)
        2. Average across rows to get weights

        Args:
            matrix: Pairwise comparison matrix

        Returns:
            Array of weights (length = n_criteria)
        """
        # Calculate column sums
        column_sums = matrix.sum(axis=0)

        # Normalize matrix
        normalized_matrix = matrix / column_sums

        # Calculate weights (row averages)
        weights = normalized_matrix.mean(axis=1)

        # Ensure weights sum to 1
        weights = weights / weights.sum()

        logger.debug(f"Calculated weights: {weights}")

        return weights

    def check_consistency(
        self,
        matrix: np.ndarray,
        weights: np.ndarray
    ) -> Tuple[float, bool]:
        """
        Check consistency of the pairwise comparison matrix.

        Consistency Ratio (CR) = CI / RI

        where:
        - CI (Consistency Index) = (λmax - n) / (n - 1)
        - RI (Random Index) = value from lookup table
        - λmax = maximum eigenvalue

        A matrix is considered consistent if CR < 0.1

        Args:
            matrix: Pairwise comparison matrix
            weights: Calculated weights

        Returns:
            Tuple of (CR, is_consistent)
        """
        n = len(weights)

        # Calculate λmax
        weighted_sum = matrix @ weights
        lambda_values = weighted_sum / weights
        lambda_max = lambda_values.mean()

        # Calculate CI
        ci = (lambda_max - n) / (n - 1)

        # Get RI from lookup table
        ri = RANDOM_INDEX.get(n, 1.0)

        # Calculate CR
        cr = ci / ri if ri > 0 else 0

        is_consistent = cr < AHP_CONSISTENCY_THRESHOLD

        logger.info(
            f"Consistency check: λmax={lambda_max:.4f}, "
            f"CI={ci:.4f}, RI={ri:.2f}, CR={cr:.4f}, "
            f"consistent={is_consistent}"
        )

        return cr, is_consistent

    def calculate_criteria_weights(
        self,
        type_livraison: TypeLivraison
    ) -> Tuple[Dict[str, float], Dict[str, Any]]:
        """
        Complete AHP process: build matrix, calculate weights, check consistency.

        Args:
            type_livraison: Type of delivery

        Returns:
            Tuple of:
            - Dict mapping criterion name to weight
            - Dict with consistency information
        """
        logger.info(f"Calculating criteria weights for {type_livraison}")

        # Build comparison matrix
        matrix = self.build_comparison_matrix(type_livraison)

        # Calculate weights
        weights_array = self.calculate_weights(matrix)

        # Check consistency
        cr, is_consistent = self.check_consistency(matrix, weights_array)

        # Map to criterion names (ordre: proximité, capacité, type_véhicule, réputation)
        weights_dict = {
            "proximite_geographique": float(weights_array[0]),
            "capacite": float(weights_array[1]),
            "type_vehicule": float(weights_array[2]),
            "reputation": float(weights_array[3]),
        }

        # Consistency info
        consistency_info = {
            "CR": float(cr),
            "est_coherent": bool(is_consistent),
            "seuil": AHP_CONSISTENCY_THRESHOLD,
        }

        if not is_consistent:
            logger.warning(
                f"AHP matrix is NOT consistent (CR={cr:.4f} > {AHP_CONSISTENCY_THRESHOLD}). "
                "Results may be unreliable."
            )

        logger.info(f"Final weights: {weights_dict}")

        return weights_dict, consistency_info
