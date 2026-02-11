"""
Administration API endpoints.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import require_auth
from src.config.constants import ProductType

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/cache/invalidate",
    summary="Invalidate cache",
    description="Invalidate cache entries for a specific product.",
)
async def invalidate_cache(
    product_id: str,
    product_type: ProductType,
    auth: dict = Depends(require_auth),
):
    """
    Invalidate cache entries for a product.

    Removes all cached recommendations related to the specified product.
    """
    logger.info(f"Cache invalidation request: {product_id}")

    try:
        from src.modules.module2_recommendation.cache import get_cache_manager
        cache = get_cache_manager()
        count = await cache.invalidate(
            product_id=product_id,
            product_type=product_type.value,
        )

        return {
            "message": f"Invalidated {count} cache entries",
            "product_id": product_id,
            "product_type": product_type,
        }

    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/collections/{product_type}",
    summary="Get collection info",
    description="Get Qdrant collection statistics.",
)
async def get_collection_info(
    product_type: ProductType,
):
    """Get information about a Qdrant collection."""
    from src.modules.module2_recommendation.vector_store import get_vector_store

    try:
        vector_store = get_vector_store()
        info = vector_store.get_collection_info(product_type)
        return info

    except Exception as e:
        logger.error(f"Collection info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/token",
    summary="Generate API token",
    description="Generate a JWT token for API authentication (for testing).",
)
async def generate_token(client_id: str, secret: str):
    """
    Generate an API token for testing.

    In production, use proper authentication flow.
    """
    from src.config import settings
    from src.api.dependencies import create_access_token

    # Simple secret check for demo purposes
    if secret != settings.secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid secret",
        )

    token = create_access_token({"sub": client_id, "type": "api"})

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }
