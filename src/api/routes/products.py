"""
Product management API endpoints (multi-tenant).

Provides endpoints for uploading, deleting, listing, and inspecting products
in a tenant's collection with proper pagination support.
"""

import logging
import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy import select, func
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
from src.database.models_multitenant import Product

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# CSV UPLOAD (for Frontend)
# ============================================================================

@router.post(
    "/tenants/{tenant_id}/products/upload",
    response_model=ProductUploadResponse,
    summary="Upload products via CSV",
    description="Upload products from a CSV file",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid CSV format"},
        404: {"model": ErrorResponse, "description": "Tenant not found"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
)
async def upload_products_csv(
    tenant_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    product_service: ProductService = Depends(get_product_service),
):
    """
    Upload products from CSV file.

    CSV Format:
    - Required columns: product_id, name
    - Optional columns: description, category, sku, price
    """
    logger.info(f"CSV upload request for tenant: {tenant_id}")

    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file"
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
        # Read CSV
        contents = await file.read()
        decoded = contents.decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))

        products = []
        errors = []

        for idx, row in enumerate(reader, start=2):  # Start at 2 (line 1 is headers)
            try:
                # Validate required fields
                if 'product_id' not in row or 'name' not in row:
                    errors.append(f"Line {idx}: Missing required fields (product_id, name)")
                    continue

                if not row['product_id'] or not row['name']:
                    errors.append(f"Line {idx}: product_id and name cannot be empty")
                    continue

                product_data = {
                    'product_id': row['product_id'].strip(),
                    'name': row['name'].strip(),
                    'description': row.get('description', '').strip(),
                    'category': row.get('category', '').strip(),
                    'sku': row.get('sku', '').strip(),
                }

                # Create Product model instance
                product = Product(
                    tenant_id=tenant.id,
                    product_id=product_data['product_id'],
                    name=product_data['name'],
                    description=product_data['description'] or None,
                    category=product_data['category'] or None,
                    sku=product_data['sku'] or None,
                )

                session.add(product)
                products.append(product_data)

            except Exception as e:
                errors.append(f"Line {idx}: {str(e)}")

        if errors and not products:
            # All rows failed - rollback
            await session.rollback()
        else:
            # Commit successfully parsed products
            try:
                await session.commit()
            except Exception as db_error:
                await session.rollback()
                logger.error(f"Database commit failed: {db_error}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error while saving products: {str(db_error)}",
                )

        logger.info(f"Uploaded {len(products)} products for tenant {tenant_id}")

        return ProductUploadResponse(
            success=len(errors) == 0,
            total_processed=len(products) + len(errors),
            total_created=len(products),
            total_updated=0,
            errors=errors[:100],  # Limit to first 100 errors
        )

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded"
        )
    except csv.Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"CSV upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# LIST PRODUCTS (with pagination)
# ============================================================================

@router.get(
    "/tenants/{tenant_id}/products",
    summary="List products for a tenant",
    description="Get paginated list of products for a specific tenant",
)
async def list_products(
    tenant_id: str,
    page: int = Query(1, ge=1, le=10000, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db_session),
):
    """List products for a tenant with pagination."""
    logger.info(f"List products: tenant={tenant_id}, page={page}, size={page_size}")

    try:
        # Verify tenant exists
        tenant_service = TenantService(session)
        tenant = await tenant_service.get_tenant(tenant_id)

        # Get total count
        count_query = select(func.count(Product.id)).where(Product.tenant_id == tenant.id)
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated products
        offset = (page - 1) * page_size
        products_query = (
            select(Product)
            .where(Product.tenant_id == tenant.id)
            .order_by(Product.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        products_result = await session.execute(products_query)
        products = products_result.scalars().all()

        total_pages = (total + page_size - 1) // page_size

        return {
            "items": [
                {
                    "id": str(p.id),
                    "product_id": p.product_id,
                    "name": p.name,
                    "description": p.description,
                    "category": p.category,
                    "sku": p.sku,
                    "score": None,  # TODO: Get from Score table
                    "review_count": 0,  # TODO: Get from Review table
                    "created_at": p.created_at.isoformat(),
                }
                for p in products
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )
    except Exception as e:
        logger.error(f"List products error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


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
    status_code=status.HTTP_200_OK,
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
