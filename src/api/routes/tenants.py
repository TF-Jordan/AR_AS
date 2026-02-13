"""
Tenant management admin API routes.

Provides full CRUD operations for tenant lifecycle management.
All routes require the 'admin' realm role in the JWT token.

Operations:
- Create tenant (provisions Qdrant collection + default scoring config)
- List tenants with pagination and filtering
- Get tenant details
- Update tenant configuration
- Delete tenant (irreversible: removes all data)
- Get tenant statistics
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session, require_admin
from src.api.schemas_multitenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListResponse,
)
from src.services.tenant_service import TenantService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/tenants", tags=["Admin - Tenants"])


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant",
    responses={
        409: {"description": "Tenant with this tenant_id already exists"},
    },
)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """
    Create a new tenant (admin only).

    This operation:
    - Creates a Tenant record in PostgreSQL
    - Provisions a Qdrant collection: ``tenant_{tenant_id}``
    - Creates a default scoring configuration (or uses provided criteria)

    Returns the full tenant details including the generated UUID.
    """
    admin_sub = admin.get("sub", "unknown")
    logger.info(
        "Admin creating tenant: tenant_id=%s, by=%s",
        tenant_data.tenant_id,
        admin_sub,
        extra={
            "event": "tenant_create",
            "tenant_id": tenant_data.tenant_id,
            "admin_sub": admin_sub,
        },
    )

    service = TenantService(db)
    try:
        tenant = await service.create_tenant(tenant_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    logger.info(
        "Tenant created successfully: %s (id=%s)",
        tenant.tenant_id,
        tenant.id,
        extra={
            "event": "tenant_created",
            "tenant_id": tenant.tenant_id,
            "tenant_uuid": str(tenant.id),
            "admin_sub": admin_sub,
        },
    )
    return tenant


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=TenantListResponse,
    summary="List all tenants",
)
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """
    List all tenants with pagination (admin only).

    Query parameters:
    - **skip**: Number of records to skip (offset).
    - **limit**: Maximum number of results to return (default 100, max 500).
    - **is_active**: Optional filter by active status. If omitted, returns all tenants.
    """
    # Clamp limit to prevent abuse
    limit = min(limit, 500)

    service = TenantService(db)

    # Determine active_only based on filter
    if is_active is None:
        # Return all tenants: use active_only=False
        tenants, total = await service.list_tenants(
            skip=skip, limit=limit, active_only=False
        )
    else:
        tenants, total = await service.list_tenants(
            skip=skip, limit=limit, active_only=is_active
        )

    return TenantListResponse(
        tenants=[TenantResponse.model_validate(t) for t in tenants],
        total=total,
        skip=skip,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------

@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Get tenant details",
    responses={
        404: {"description": "Tenant not found"},
    },
)
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """
    Get tenant details by tenant_id (admin only).

    Returns the full tenant record including rate limit configuration,
    Qdrant collection name, and timestamps.
    """
    service = TenantService(db)
    try:
        tenant = await service.get_tenant(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )
    return tenant


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

@router.patch(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Update tenant configuration",
    responses={
        404: {"description": "Tenant not found"},
    },
)
async def update_tenant(
    tenant_id: str,
    updates: TenantUpdate,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """
    Update tenant configuration (admin only).

    Supports partial updates. Only provided fields are modified:
    - **name**: Display name
    - **domain**: Business domain
    - **keycloak_client_id**: OAuth2 client mapping
    - **rate_limit_requests**: Max requests per window
    - **rate_limit_window_seconds**: Rate limit window duration
    - **is_active**: Enable/disable tenant
    """
    admin_sub = admin.get("sub", "unknown")
    logger.info(
        "Admin updating tenant: tenant_id=%s, by=%s, fields=%s",
        tenant_id,
        admin_sub,
        updates.model_dump(exclude_unset=True).keys(),
        extra={
            "event": "tenant_update",
            "tenant_id": tenant_id,
            "admin_sub": admin_sub,
        },
    )

    service = TenantService(db)
    try:
        tenant = await service.update_tenant(tenant_id, updates)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    logger.info(
        "Tenant updated successfully: %s",
        tenant_id,
        extra={
            "event": "tenant_updated",
            "tenant_id": tenant_id,
            "admin_sub": admin_sub,
        },
    )
    return tenant


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tenant",
    responses={
        404: {"description": "Tenant not found"},
    },
)
async def delete_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """
    Delete a tenant and all associated data (admin only).

    **WARNING: This operation is irreversible!**

    This will permanently:
    - Delete the Qdrant collection (all vector embeddings)
    - Delete all scoring configuration versions
    - Delete all product descriptions
    - Remove the tenant record from PostgreSQL
    """
    admin_sub = admin.get("sub", "unknown")
    logger.warning(
        "Admin deleting tenant: tenant_id=%s, by=%s",
        tenant_id,
        admin_sub,
        extra={
            "event": "tenant_delete",
            "tenant_id": tenant_id,
            "admin_sub": admin_sub,
        },
    )

    service = TenantService(db)
    try:
        await service.delete_tenant(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    logger.warning(
        "Tenant deleted permanently: %s",
        tenant_id,
        extra={
            "event": "tenant_deleted",
            "tenant_id": tenant_id,
            "admin_sub": admin_sub,
        },
    )
    return None


# ---------------------------------------------------------------------------
# STATS
# ---------------------------------------------------------------------------

@router.get(
    "/{tenant_id}/stats",
    summary="Get tenant statistics",
    responses={
        404: {"description": "Tenant not found"},
    },
)
async def get_tenant_stats(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """
    Get tenant statistics (admin only).

    Returns:
    - **tenant_id**: External tenant identifier
    - **name**: Tenant display name
    - **total_products**: Number of product descriptions in PostgreSQL
    - **active_scoring_version**: Current active scoring config version
    - **qdrant_collection_info**: Qdrant collection statistics (if available)
    - **is_active**: Whether the tenant is active
    - **created_at**: When the tenant was created
    """
    service = TenantService(db)
    try:
        tenant = await service.get_tenant(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    # Count products
    from sqlalchemy import func, select
    from src.database.models_multitenant import ProductDescription, ScoringConfig

    product_count_result = await db.execute(
        select(func.count(ProductDescription.id)).where(
            ProductDescription.tenant_id == tenant_id
        )
    )
    total_products = product_count_result.scalar_one()

    # Get active scoring version
    active_config_result = await db.execute(
        select(ScoringConfig.version).where(
            ScoringConfig.tenant_id == tenant_id,
            ScoringConfig.is_active.is_(True),
        )
    )
    active_version = active_config_result.scalar_one_or_none()

    # Get Qdrant collection stats (best-effort)
    qdrant_info = None
    try:
        from src.modules.module2_recommendation.vector_store import get_vector_store
        vector_store = get_vector_store()
        qdrant_info = vector_store.get_collection_stats(tenant_id)
    except Exception as exc:
        logger.debug("Could not fetch Qdrant stats for tenant %s: %s", tenant_id, exc)
        qdrant_info = {"error": "Qdrant unavailable"}

    return {
        "tenant_id": tenant.tenant_id,
        "name": tenant.name,
        "domain": tenant.domain,
        "total_products": total_products,
        "active_scoring_version": active_version,
        "qdrant_collection_info": qdrant_info,
        "is_active": tenant.is_active,
        "rate_limit_requests": tenant.rate_limit_requests,
        "rate_limit_window_seconds": tenant.rate_limit_window_seconds,
        "created_at": tenant.created_at.isoformat(),
        "updated_at": tenant.updated_at.isoformat(),
    }
