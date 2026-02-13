"""
Dashboard metrics API endpoint.

Provides aggregated statistics across all tenants for the admin dashboard.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session, require_admin
from src.api.schemas import ErrorResponse
from src.database.models import Tenant, Product, Review, Score

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/dashboard", tags=["Admin - Dashboard"])


@router.get(
    "/metrics",
    summary="Get dashboard metrics",
    description="Get aggregated metrics across all tenants for admin dashboard",
    responses={
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
)
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """
    Get dashboard metrics (admin only).

    Returns:
    - total_tenants: Total number of tenants
    - active_tenants: Number of active tenants
    - total_products: Total products across all tenants
    - total_reviews: Total reviews across all tenants
    - avg_score: Average score across all scored products
    - recent_activity: Last 10 activity events
    """
    try:
        # Total tenants
        total_tenants_query = select(func.count(Tenant.id))
        total_tenants_result = await db.execute(total_tenants_query)
        total_tenants = total_tenants_result.scalar() or 0

        # Active tenants
        active_tenants_query = select(func.count(Tenant.id)).where(Tenant.is_active == True)
        active_tenants_result = await db.execute(active_tenants_query)
        active_tenants = active_tenants_result.scalar() or 0

        # Total products
        total_products_query = select(func.count(Product.id))
        total_products_result = await db.execute(total_products_query)
        total_products = total_products_result.scalar() or 0

        # Total reviews
        total_reviews_query = select(func.count(Review.id))
        total_reviews_result = await db.execute(total_reviews_query)
        total_reviews = total_reviews_result.scalar() or 0

        # Average score (only where score is not null)
        avg_score_query = select(func.avg(Score.final_score))
        avg_score_result = await db.execute(avg_score_query)
        avg_score = avg_score_result.scalar() or 0.0

        # Recent activity (simplified - get last 10 tenants created)
        recent_tenants_query = (
            select(Tenant)
            .order_by(Tenant.created_at.desc())
            .limit(10)
        )
        recent_tenants_result = await db.execute(recent_tenants_query)
        recent_tenants = recent_tenants_result.scalars().all()

        recent_activity = [
            {
                "id": str(tenant.id),
                "type": "tenant_created",
                "message": f"Tenant '{tenant.name}' was created",
                "timestamp": tenant.created_at.isoformat(),
                "tenant_name": tenant.name,
            }
            for tenant in recent_tenants
        ]

        return {
            "total_tenants": total_tenants,
            "active_tenants": active_tenants,
            "total_products": total_products,
            "total_reviews": total_reviews,
            "avg_score": round(float(avg_score), 2),
            "tenants_growth": "+0%",  # TODO: Calculate based on last month
            "products_growth": "+0%",  # TODO: Calculate based on last month
            "reviews_growth": "+0%",   # TODO: Calculate based on last month
            "score_growth": "+0%",     # TODO: Calculate based on last month
            "recent_activity": recent_activity,
        }

    except Exception as e:
        logger.error("Dashboard metrics error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
