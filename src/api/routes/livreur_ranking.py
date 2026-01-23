"""
Livreur Ranking API endpoints (Module 4).

This module provides a stateless ranking service for delivery persons
based on multi-criteria decision making (AHP + TOPSIS).
"""

import logging
from fastapi import APIRouter, HTTPException, status

from src.modules.module4_livreur_ranking import (
    RankingRequestSchema,
    RankingResponseSchema,
    get_orchestrator,
)
from src.api.schemas import ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/rank",
    response_model=RankingResponseSchema,
    responses={
        200: {"description": "Successful ranking"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
    summary="Rank delivery persons for an announcement",
    description="""
    Ranks delivery persons (livreurs) for a delivery announcement using
    multi-criteria decision making.

    **Process:**
    1. **AHP Weight Calculation**: Calculates criteria weights based
       on delivery type (standard/express/sameday)
    2. **TOPSIS Ranking**: Ranks ALL candidates using TOPSIS
       multi-criteria decision algorithm

    **Criteria:**
    - Geographic proximity (distance to pickup and delivery)
    - Reputation (rating 0-10)
    - Capacity (volume in m³)
    - Vehicle type (velo/moto/voiture/camion)

    **Input:**
    - Annonce with pickup/delivery points, delivery type, and package volume (m³)
    - List of candidate livreurs with their attributes

    **Response:**
    Returns a simple list of livreur IDs sorted by score (best first).
    ALL livreurs are ranked and returned - no filtering.

    Example response: `{"livreurs_ids": ["livreur_3", "livreur_1", "livreur_2"]}`
    """,
)
async def rank_livreurs(request: RankingRequestSchema) -> RankingResponseSchema:
    """
    Rank delivery persons for a delivery announcement.

    Args:
        request: Ranking request with announcement and candidates

    Returns:
        RankingResponseSchema with list of livreur IDs in ranked order
    """
    logger.info(
        f"Ranking request for annonce {request.annonce.annonce_id} "
        f"with {len(request.livreurs_candidats)} candidates"
    )

    try:
        orchestrator = get_orchestrator()
        response = orchestrator.rank_livreurs(request=request)

        logger.info(
            f"Ranking complete for {request.annonce.annonce_id}: "
            f"{len(response.livreurs_ids)} livreurs ranked"
        )

        return response

    except ValueError as e:
        logger.error(f"Validation error in ranking: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ranking error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health check for Module 4",
    description="Check if Module 4 (Livreur Ranking) is operational"
)
async def health_check():
    """
    Health check endpoint for Module 4.

    Returns:
        Dict with module status and component availability
    """
    try:
        orchestrator = get_orchestrator()

        components = {
            "spatial_filter": orchestrator.spatial_filter is not None,
            "ahp_calculator": orchestrator.ahp_calculator is not None,
            "topsis_ranker": orchestrator.topsis_ranker is not None,
        }

        all_ok = all(components.values())

        return {
            "status": "healthy" if all_ok else "degraded",
            "module": "module4_livreur_ranking",
            "components": components,
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "module": "module4_livreur_ranking",
            "error": str(e)
        }
