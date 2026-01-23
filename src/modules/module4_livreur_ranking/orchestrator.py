"""
Orchestrator - Main coordinator for Module 4

Coordinates the livreur ranking process:
1. Phase 1: AHP criteria weight calculation
2. Phase 2: TOPSIS multi-criteria ranking

Note: No spatial filtering - ALL livreurs are ranked and returned.
"""

import logging
from datetime import datetime
from typing import List, Optional

from .schemas import (
    RankingRequestSchema,
    RankingResponseSchema,
)
from .spatial_filter import SpatialFilter
from .ahp_calculator import AHPCalculator
from .topsis_ranker import TOPSISRanker

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Orchestrates the complete livreur ranking workflow.

    Workflow:
    1. Calculate distances for all livreurs
    2. Calculate criteria weights using AHP (based on delivery type)
    3. Rank ALL candidates using TOPSIS
    4. Return list of livreur IDs in ranked order
    """

    def __init__(self):
        """Initialize orchestrator with all required components."""
        self.spatial_filter = SpatialFilter()
        self.ahp_calculator = AHPCalculator()
        self.topsis_ranker = TOPSISRanker()

    def rank_livreurs(self, request: RankingRequestSchema) -> RankingResponseSchema:
        """
        Complete ranking workflow.

        Args:
            request: Ranking request containing annonce and candidates

        Returns:
            RankingResponseSchema with list of livreur IDs in ranked order
        """
        start_time = datetime.now()
        annonce = request.annonce
        livreurs = request.livreurs_candidats

        logger.info(
            f"Starting ranking for annonce {annonce.annonce_id} "
            f"with {len(livreurs)} candidates"
        )

        # ============================================================
        # PHASE 1: CALCULATE DISTANCES (for all livreurs)
        # ============================================================
        logger.info("Phase 1: Calculating distances")

        distances = self.spatial_filter.calculate_distances_for_livreurs(
            livreurs=livreurs,
            point_ramassage=annonce.point_ramassage,
            point_livraison=annonce.point_livraison
        )

        logger.info(f"Phase 1 complete: distances calculated for {len(livreurs)} livreurs")

        # ============================================================
        # PHASE 2: AHP WEIGHT CALCULATION
        # ============================================================
        logger.info("Phase 2: AHP weight calculation")

        weights_dict, consistency_info = self.ahp_calculator.calculate_criteria_weights(
            type_livraison=annonce.type_livraison
        )

        logger.info(f"Phase 2 complete: weights = {weights_dict}")

        # ============================================================
        # PHASE 3: TOPSIS RANKING
        # ============================================================
        logger.info("Phase 3: TOPSIS ranking")

        topsis_results = self.topsis_ranker.rank(
            livreurs=livreurs,
            distances=distances,
            weights=weights_dict
        )

        logger.info(f"Phase 3 complete: {len(topsis_results)} livreurs ranked")

        # ============================================================
        # FORMAT RESPONSE - Just the list of IDs in ranked order
        # ============================================================
        livreurs_ids = [result["livreur_id"] for result in topsis_results]

        # Calculate processing time
        end_time = datetime.now()
        processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"Ranking complete for {annonce.annonce_id}: "
            f"{len(livreurs_ids)} livreurs ranked in {processing_time_ms}ms"
        )

        return RankingResponseSchema(livreurs_ids=livreurs_ids)


# ============================================================
# DEPENDENCY INJECTION / FACTORY
# ============================================================

_orchestrator_instance: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """
    Get singleton instance of Orchestrator.

    Used for dependency injection in FastAPI routes.

    Returns:
        Orchestrator instance
    """
    global _orchestrator_instance

    if _orchestrator_instance is None:
        _orchestrator_instance = Orchestrator()
        logger.info("Orchestrator instance created")

    return _orchestrator_instance
