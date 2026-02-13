"""
Multi-tenant Recommendation API endpoints.
Coordinates Module 1 (sentiment) and Module 2 (recommendation) directly.

Tenant isolation is enforced via OAuth2 token (tenant_id from Keycloak).
The recommendation engine fetches the tenant's ScoringConfig internally
via the database session provided through dependency injection.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    get_db_session,
    get_current_tenant_id,
    get_recommendation_engine,
)
from src.api.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendationDetailedResponse,
    FullWorkflowResponse,
    ErrorResponse,
)
from src.modules.module1_sentiment import SentimentAnalyzer, SentimentInput
from src.modules.module2_recommendation.engine import MultiTenantRecommendationEngine
from src.services.tenant_service import TenantService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=FullWorkflowResponse,
    responses={
        200: {"description": "Successful recommendation"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Tenant or scoring config not found"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
    summary="Get multi-tenant product recommendations",
    description="""
    Process a complete multi-tenant recommendation request.

    This endpoint:
    1. Identifies the tenant from the OAuth2 token
    2. Analyzes sentiment of the provided comment (Module 1)
    3. The engine internally loads the tenant-specific scoring configuration
    4. Generates recommendations using dynamic scoring (Module 2)
    5. Returns ranked results with per-criterion breakdowns
    """,
)
async def get_recommendations(
    request: RecommendationRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
    engine: MultiTenantRecommendationEngine = Depends(get_recommendation_engine),
):
    """Get product recommendations based on sentiment analysis (multi-tenant)."""
    logger.info(
        "Recommendation request: tenant=%s, product=%s, client=%s",
        tenant_id,
        request.product_id,
        request.client_id,
    )

    try:
        start_time = datetime.utcnow()

        # Verify tenant exists and is active
        tenant_service = TenantService(session)
        try:
            tenant = await tenant_service.get_tenant(tenant_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' not found",
            )

        if not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tenant '{tenant_id}' is deactivated",
            )

        # Step 1: Sentiment Analysis (Module 1)
        analyzer = SentimentAnalyzer()
        sentiment_input = SentimentInput(
            product_id=request.product_id,
            client_id=request.client_id,
            commentaire=request.comment,
        )
        sentiment_result = analyzer.analyze(sentiment_input)

        logger.info(
            "Sentiment analysis completed: label=%s, score=%.2f",
            sentiment_result.sentiment_label,
            sentiment_result.sentiment_score,
        )

        # Step 2: Product description for embedding
        # Use the comment as fallback description for query embedding
        product_description = request.comment

        # Step 3: Recommendation (Module 2)
        # The engine now fetches the ScoringConfig internally via its db session
        rec_result = await engine.recommend_detailed(
            tenant_id=tenant_id,
            product_id=request.product_id,
            product_description=product_description,
            sentiment_result=sentiment_result,
            top_k=request.top_k,
            filters=request.filters,
        )

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return FullWorkflowResponse(
            status="completed",
            processing_time_seconds=processing_time,
            sentiment={
                "client_id": sentiment_result.client_id,
                "product_id": sentiment_result.product_id,
                "sentiment_score": sentiment_result.sentiment_score,
                "sentiment_label": sentiment_result.sentiment_label or "unknown",
                "confidence": sentiment_result.confidence,
            },
            recommendations=rec_result.model_dump(),
        )

    except HTTPException:
        raise
    except ValueError as e:
        # ScoringConfig not found or validation error
        logger.warning("Recommendation ValueError: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Recommendation error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/simple",
    response_model=RecommendationResponse,
    responses={
        200: {"description": "Successful recommendation"},
        404: {"model": ErrorResponse, "description": "Tenant or scoring config not found"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
    summary="Get simple product ID recommendations",
    description="""
    Lightweight endpoint that returns only client_id and an ordered list
    of product_ids (no score breakdowns).
    """,
)
async def get_recommendations_simple(
    request: RecommendationRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
    engine: MultiTenantRecommendationEngine = Depends(get_recommendation_engine),
):
    """Get simple product ID recommendations (no score details)."""
    logger.info(
        "Simple recommendation request: tenant=%s, product=%s, client=%s",
        tenant_id,
        request.product_id,
        request.client_id,
    )

    try:
        # Verify tenant
        tenant_service = TenantService(session)
        try:
            tenant = await tenant_service.get_tenant(tenant_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' not found",
            )

        if not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tenant '{tenant_id}' is deactivated",
            )

        # Sentiment
        analyzer = SentimentAnalyzer()
        sentiment_input = SentimentInput(
            product_id=request.product_id,
            client_id=request.client_id,
            commentaire=request.comment,
        )
        sentiment_result = analyzer.analyze(sentiment_input)

        # Recommendation (returns List[str])
        product_ids = await engine.recommend(
            tenant_id=tenant_id,
            product_id=request.product_id,
            product_description=request.comment,
            sentiment_result=sentiment_result,
            top_k=request.top_k,
            filters=request.filters,
        )

        return RecommendationResponse(
            client_id=request.client_id,
            product_ids=product_ids,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning("Simple recommendation ValueError: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Simple recommendation error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
