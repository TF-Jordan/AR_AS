"""
Administration API endpoints (multi-tenant).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session, get_current_tenant_id
from src.api.schemas import ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/cache/invalidate",
    summary="Invalidate cache",
    description="Invalidate cache entries for a specific product.",
    responses={
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
)
async def invalidate_cache(
    product_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Invalidate cache entries for a product.

    Removes all cached recommendations related to the specified product
    within the current tenant scope.
    """
    logger.info(
        "Cache invalidation request: tenant=%s, product=%s",
        tenant_id,
        product_id,
    )

    try:
        from src.modules.module2_recommendation.cache import get_cache_manager

        cache = get_cache_manager()
        count = await cache.invalidate(
            product_id=product_id,
            product_type=tenant_id,  # Use tenant_id as namespace
        )

        return {
            "message": f"Invalidated {count} cache entries",
            "tenant_id": tenant_id,
            "product_id": product_id,
        }

    except Exception as e:
        logger.error("Cache invalidation error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/collections/stats",
    summary="Get collection stats for current tenant",
    description="Get Qdrant collection statistics for the authenticated tenant.",
)
async def get_collection_stats(
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get information about the tenant's Qdrant collection."""
    from src.modules.module2_recommendation.vector_store import get_vector_store

    try:
        vector_store = get_vector_store()
        info = vector_store.get_collection_stats(tenant_id)
        return info

    except Exception as e:
        logger.error("Collection stats error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
