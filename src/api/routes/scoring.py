"""
Scoring configuration management API routes.

Provides endpoints for managing per-tenant scoring criteria:
- Admin routes: Cross-tenant management (requires admin role)
- Tenant self-service routes: Manage own scoring config (requires auth)

Scoring configurations are versioned. Each update creates a new version
and deactivates the previous one, providing a full audit trail.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session, require_admin, get_current_tenant_id
from src.api.schemas_multitenant import (
    ScoringConfigCreate,
    ScoringConfigResponse,
    ScoringConfigHistoryResponse,
)
from src.services.scoring_service import ScoringConfigService
from src.services.tenant_service import TenantService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/scoring", tags=["Admin - Scoring"])


# ===========================================================================
# Admin routes (cross-tenant management)
# ===========================================================================

@router.get(
    "/tenants/{tenant_id}/config",
    response_model=ScoringConfigResponse,
    summary="Get tenant scoring config (admin)",
    responses={
        404: {"description": "Tenant or scoring config not found"},
    },
)
async def get_tenant_scoring_config(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """
    Get the active scoring configuration for a specific tenant (admin only).

    Returns the currently active scoring configuration with all criteria,
    weights, and version information.
    """
    # Verify tenant exists
    tenant_service = TenantService(db)
    try:
        await tenant_service.get_tenant(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    scoring_service = ScoringConfigService(db)
    config = await scoring_service.get_active_config(tenant_id)

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active scoring config found for tenant '{tenant_id}'",
        )

    return config


@router.put(
    "/tenants/{tenant_id}/config",
    response_model=ScoringConfigResponse,
    summary="Update tenant scoring config (admin)",
    responses={
        404: {"description": "Tenant not found"},
        422: {"description": "Validation error (weights must sum to 1.0)"},
    },
)
async def update_tenant_scoring_config(
    tenant_id: str,
    config_data: ScoringConfigCreate,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """
    Update the scoring configuration for a specific tenant (admin only).

    Creates a new version of the scoring config and deactivates the
    previous one. The criteria weights must sum to 1.0 (with 0.01 tolerance).

    A new version number is assigned automatically.
    """
    admin_sub = admin.get("sub", "unknown")
    logger.info(
        "Admin updating scoring config: tenant_id=%s, by=%s",
        tenant_id,
        admin_sub,
        extra={
            "event": "scoring_config_update",
            "tenant_id": tenant_id,
            "admin_sub": admin_sub,
        },
    )

    # Verify tenant exists
    tenant_service = TenantService(db)
    try:
        await tenant_service.get_tenant(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    scoring_service = ScoringConfigService(db)
    created_by = config_data.created_by or admin_sub

    try:
        config = await scoring_service.update_config(
            tenant_id=tenant_id,
            criteria=config_data.criteria,
            created_by=created_by,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    logger.info(
        "Scoring config updated: tenant=%s, version=%d, by=%s",
        tenant_id,
        config.version,
        created_by,
        extra={
            "event": "scoring_config_updated",
            "tenant_id": tenant_id,
            "version": config.version,
            "admin_sub": admin_sub,
        },
    )
    return config


@router.get(
    "/tenants/{tenant_id}/config/history",
    response_model=List[ScoringConfigResponse],
    summary="Get scoring config history (admin)",
    responses={
        404: {"description": "Tenant not found"},
    },
)
async def get_scoring_config_history(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """
    Get all scoring configuration versions for a tenant (admin only).

    Returns all versions ordered by version number (newest first),
    including inactive (superseded) configurations.
    """
    # Verify tenant exists
    tenant_service = TenantService(db)
    try:
        await tenant_service.get_tenant(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )

    scoring_service = ScoringConfigService(db)
    configs = await scoring_service.get_config_history(tenant_id)
    return configs


# ===========================================================================
# Tenant self-service routes (authenticated tenant manages own config)
# ===========================================================================

@router.get(
    "/config",
    response_model=ScoringConfigResponse,
    summary="Get my scoring config",
    tags=["Scoring - Self Service"],
    responses={
        404: {"description": "No active scoring config found"},
    },
)
async def get_my_scoring_config(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get the active scoring configuration for the authenticated tenant.

    This is a self-service endpoint -- no admin role required.
    The tenant_id is extracted from the JWT token.
    """
    scoring_service = ScoringConfigService(db)
    config = await scoring_service.get_active_config(tenant_id)

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active scoring config found for your tenant",
        )

    return config


@router.put(
    "/config",
    response_model=ScoringConfigResponse,
    summary="Update my scoring config",
    tags=["Scoring - Self Service"],
    responses={
        422: {"description": "Validation error (weights must sum to 1.0)"},
    },
)
async def update_my_scoring_config(
    config_data: ScoringConfigCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Update the scoring configuration for the authenticated tenant.

    This is a self-service endpoint -- no admin role required.
    Creates a new version of the scoring config. The criteria weights
    must sum to 1.0 (with 0.01 tolerance).
    """
    logger.info(
        "Tenant updating own scoring config: tenant_id=%s",
        tenant_id,
        extra={
            "event": "scoring_config_self_update",
            "tenant_id": tenant_id,
        },
    )

    scoring_service = ScoringConfigService(db)
    created_by = config_data.created_by or f"tenant:{tenant_id}"

    try:
        config = await scoring_service.update_config(
            tenant_id=tenant_id,
            criteria=config_data.criteria,
            created_by=created_by,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    logger.info(
        "Tenant scoring config updated: tenant=%s, version=%d",
        tenant_id,
        config.version,
        extra={
            "event": "scoring_config_self_updated",
            "tenant_id": tenant_id,
            "version": config.version,
        },
    )
    return config
