"""
Product management API endpoints (multi-tenant).

Provides endpoints for uploading, deleting, and inspecting products
in a tenant's Qdrant collection.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    get_db_session,
    get_current_tenant_id,
    get_product_service,
)
from src.api.schemas import (
    ProductBatchUpload,
    ProductUploadResponse,
    ProductDeleteResponse,
    ProductStatsResponse,
    ErrorResponse,
)
from src.services.product_service import ProductService
from src.services.tenant_service import TenantService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/upload",
    response_model=ProductUploadResponse,
    summary="Upload products",
    description="Upload products with descriptions and metadata to the tenant's collection.",
    responses={
        404: {"model": ErrorResponse, "description": "Tenant not found"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
)
async def upload_products(
    batch: ProductBatchUpload,
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
    product_service: ProductService = Depends(get_product_service),
):
    """Upload a batch of products for the authenticated tenant."""
    logger.info(
        "Product upload request: tenant=%s, count=%d",
        tenant_id,
        len(batch.products),
    )

    # Verify tenant exists
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

    try:
        products = [p.model_dump() for p in batch.products]
        result = await product_service.upload_products(tenant_id, products)
        return result

    except Exception as e:
        logger.error("Product upload error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete(
    "/{product_id}",
    response_model=ProductDeleteResponse,
    summary="Delete a product",
    description="Delete a product from the tenant's Qdrant collection.",
    responses={
        404: {"model": ErrorResponse, "description": "Tenant not found"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
)
async def delete_product(
    product_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    product_service: ProductService = Depends(get_product_service),
):
    """Delete a product from the authenticated tenant's collection."""
    logger.info(
        "Product delete request: tenant=%s, product=%s",
        tenant_id,
        product_id,
    )

    try:
        result = await product_service.delete_product(tenant_id, product_id)
        return result

    except Exception as e:
        logger.error("Product delete error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/stats",
    response_model=ProductStatsResponse,
    summary="Get product statistics",
    description="Get statistics for the tenant's product collection.",
)
async def get_product_stats(
    tenant_id: str = Depends(get_current_tenant_id),
    product_service: ProductService = Depends(get_product_service),
):
    """Get collection statistics for the authenticated tenant."""
    try:
        result = await product_service.get_stats(tenant_id)
        return result

    except Exception as e:
        logger.error("Product stats error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
