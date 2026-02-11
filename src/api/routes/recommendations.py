"""
Recommendation API endpoints.
Coordinates Module 1 (sentiment) and Module 2 (recommendation) directly.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.api.schemas import (
    RecommendationRequestSchema,
    RecommendationOnlyRequest,
    RecommendationResponse,
    FullWorkflowResponse,
    ErrorResponse,
)
from src.config.constants import ProductType
from src.modules.module1_sentiment import SentimentAnalyzer, SentimentInput
from src.modules.module2_recommendation import (
    RecommendationEngine,
    RecommendationRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=FullWorkflowResponse,
    responses={
        200: {"description": "Successful recommendation"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
    summary="Get product recommendations",
    description="""
    Process a complete recommendation request.

    This endpoint:
    1. Analyzes sentiment of the provided comment (Module 1)
    2. Generates recommendations based on semantic similarity (Module 2)
    3. Returns ranked results
    """,
)
async def get_recommendations(
    request: RecommendationRequestSchema,
    session: AsyncSession = Depends(get_db_session),
):
    """Get product recommendations based on sentiment analysis."""
    logger.info(
        f"Recommendation request: product={request.product_id}, "
        f"client={request.client_id}"
    )

    try:
        start_time = datetime.utcnow()

        # Step 1: Sentiment Analysis (Module 1)
        analyzer = SentimentAnalyzer()
        sentiment_input = SentimentInput(
            product_id=request.product_id,
            client_id=request.client_id,
            commentaire=request.commentaire,
            product_type=request.product_type.value,
        )
        sentiment_result = analyzer.analyze(sentiment_input)

        logger.info(
            f"Sentiment analysis completed: score={sentiment_result.sentiment_score:.2f}"
        )

        # Step 2: Recommendation (Module 2)
        engine = RecommendationEngine()
        rec_request = RecommendationRequest(
            client_id=request.client_id,
            product_id=request.product_id,
            sentiment_score=sentiment_result.sentiment_score,
            product_type=ProductType(request.product_type),
            top_k=request.top_k,
        )

        rec_result = await engine.recommend(rec_request, session)

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return {
            "status": "completed",
            "processing_time_seconds": processing_time,
            "sentiment": {
                "client_id": sentiment_result.client_id,
                "product_id": sentiment_result.product_id,
                "sentiment_score": sentiment_result.sentiment_score,
                "sentiment_label": sentiment_result.sentiment_label or "unknown",
                "confidence": sentiment_result.confidence,
            },
            "recommendations": rec_result.model_dump(),
        }

    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/direct",
    response_model=RecommendationResponse,
    summary="Get recommendations with pre-computed sentiment",
    description="Get recommendations using an already computed sentiment score.",
)
async def get_recommendations_direct(
    request: RecommendationOnlyRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Get recommendations with pre-computed sentiment score."""
    try:
        engine = RecommendationEngine()
        rec_request = RecommendationRequest(
            client_id=request.client_id,
            product_id=request.product_id,
            sentiment_score=request.sentiment_score,
            product_type=request.product_type,
            top_k=request.top_k,
        )

        result = await engine.recommend(rec_request, session)
        return result.model_dump()

    except Exception as e:
        logger.error(f"Direct recommendation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
