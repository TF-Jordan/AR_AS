"""
Super Admin API endpoints.
Manages platforms, global monitoring, and system-wide operations.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import require_super_admin
from src.api.dependencies import get_db_session
from src.database.tenant_models import Platform, Tenant
from src.database.tenant_manager import get_tenant_manager
from src.events.bus import get_event_bus

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# Schemas
# ============================================================

class PlatformResponse(BaseModel):
    platform_id: str
    name: str
    slug: str
    domain: str
    email: str
    api_key: str
    is_active: bool
    tenants_count: int = 0
    created_at: str
    updated_at: str


class PlatformListResponse(BaseModel):
    platforms: List[PlatformResponse]
    total: int


class PlatformDetailResponse(PlatformResponse):
    tenants: List[dict] = []


class UpdatePlatformRequest(BaseModel):
    is_active: Optional[bool] = None
    name: Optional[str] = Field(None, min_length=1, max_length=200)


# ============================================================
# Dashboard / System Status
# ============================================================

@router.get(
    "/dashboard",
    summary="Super admin dashboard metrics",
)
async def super_admin_dashboard(
    _user: dict = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session),
):
    """Get global system metrics for super admin."""
    # Count platforms
    platforms_result = await session.execute(select(func.count(Platform.id)))
    total_platforms = platforms_result.scalar() or 0

    active_platforms_result = await session.execute(
        select(func.count(Platform.id)).where(Platform.is_active == True)
    )
    active_platforms = active_platforms_result.scalar() or 0

    # Count tenants
    tenants_result = await session.execute(
        select(func.count(Tenant.id)).where(Tenant.status != "deleted")
    )
    total_tenants = tenants_result.scalar() or 0

    active_tenants_result = await session.execute(
        select(func.count(Tenant.id)).where(Tenant.status == "active")
    )
    active_tenants = active_tenants_result.scalar() or 0

    # Service health
    services = {}
    try:
        from src.modules.module2_recommendation.cache import get_cache_manager
        cache = get_cache_manager()
        services["redis"] = await cache.health_check()
    except Exception:
        services["redis"] = False

    try:
        from src.modules.module2_recommendation import get_vector_store
        vector_store = get_vector_store()
        services["qdrant"] = vector_store.health_check()
    except Exception:
        services["qdrant"] = False

    try:
        from sqlalchemy import text as sa_text
        await session.execute(sa_text("SELECT 1"))
        services["postgresql"] = True
    except Exception:
        services["postgresql"] = False

    bus = get_event_bus()

    return {
        "total_platforms": total_platforms,
        "active_platforms": active_platforms,
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "services": services,
        "event_bus": {
            "handlers": bus.handler_count,
            "pending_tasks": bus.pending_tasks,
        },
    }


@router.get(
    "/status",
    summary="System status",
)
async def system_status(
    _user: dict = Depends(require_super_admin),
):
    """Get overall system status."""
    from src.modules.module3_orchestration import get_orchestrator

    try:
        orchestrator = get_orchestrator()
        health = await orchestrator.health_check()
        bus = get_event_bus()
        return {
            "status": "operational",
            "services": health.get("services", {}),
            "event_bus": {
                "handlers": bus.handler_count,
                "pending_tasks": bus.pending_tasks,
            },
        }
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return {"status": "degraded", "error": str(e)}


# ============================================================
# Platform management
# ============================================================

@router.get(
    "/platforms",
    response_model=PlatformListResponse,
    summary="List all platforms",
)
async def list_platforms(
    _user: dict = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session),
):
    """List all registered platforms."""
    result = await session.execute(
        select(Platform).order_by(Platform.created_at.desc())
    )
    platforms = result.scalars().all()

    platform_responses = []
    for p in platforms:
        # Count tenants for this platform
        count_result = await session.execute(
            select(func.count(Tenant.id)).where(
                Tenant.platform_id == p.id,
                Tenant.status != "deleted",
            )
        )
        tenants_count = count_result.scalar() or 0

        platform_responses.append(PlatformResponse(
            platform_id=str(p.id),
            name=p.name,
            slug=p.slug,
            domain=p.domain,
            email=p.email,
            api_key=p.api_key,
            is_active=p.is_active,
            tenants_count=tenants_count,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        ))

    return PlatformListResponse(
        platforms=platform_responses,
        total=len(platform_responses),
    )


@router.get(
    "/platforms/{slug}",
    response_model=PlatformDetailResponse,
    summary="Get platform details",
)
async def get_platform(
    slug: str,
    _user: dict = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session),
):
    """Get details of a specific platform including its tenants."""
    result = await session.execute(
        select(Platform).where(Platform.slug == slug)
    )
    platform = result.scalar_one_or_none()

    if platform is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform '{slug}' not found",
        )

    # Get tenants
    tenants_result = await session.execute(
        select(Tenant).where(
            Tenant.platform_id == platform.id,
            Tenant.status != "deleted",
        ).order_by(Tenant.created_at.desc())
    )
    tenants = tenants_result.scalars().all()

    tenants_data = [
        {
            "tenant_id": str(t.id),
            "name": t.name,
            "slug": t.slug,
            "domain": t.domain,
            "status": t.status,
            "created_at": t.created_at.isoformat(),
        }
        for t in tenants
    ]

    return PlatformDetailResponse(
        platform_id=str(platform.id),
        name=platform.name,
        slug=platform.slug,
        domain=platform.domain,
        email=platform.email,
        api_key=platform.api_key,
        is_active=platform.is_active,
        tenants_count=len(tenants_data),
        tenants=tenants_data,
        created_at=platform.created_at.isoformat(),
        updated_at=platform.updated_at.isoformat(),
    )


@router.put(
    "/platforms/{slug}",
    response_model=PlatformResponse,
    summary="Update a platform",
)
async def update_platform(
    slug: str,
    request: UpdatePlatformRequest,
    _user: dict = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session),
):
    """Activate/deactivate a platform or update its name."""
    result = await session.execute(
        select(Platform).where(Platform.slug == slug)
    )
    platform = result.scalar_one_or_none()

    if platform is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform '{slug}' not found",
        )

    if request.is_active is not None:
        platform.is_active = request.is_active
        logger.info(f"Platform {slug} {'activated' if request.is_active else 'deactivated'}")

    if request.name is not None:
        platform.name = request.name

    await session.flush()

    count_result = await session.execute(
        select(func.count(Tenant.id)).where(
            Tenant.platform_id == platform.id,
            Tenant.status != "deleted",
        )
    )
    tenants_count = count_result.scalar() or 0

    return PlatformResponse(
        platform_id=str(platform.id),
        name=platform.name,
        slug=platform.slug,
        domain=platform.domain,
        email=platform.email,
        api_key=platform.api_key,
        is_active=platform.is_active,
        tenants_count=tenants_count,
        created_at=platform.created_at.isoformat(),
        updated_at=platform.updated_at.isoformat(),
    )


@router.put(
    "/platforms/{platform_slug}/tenants/{tenant_slug}/toggle",
    summary="Toggle tenant status",
)
async def toggle_tenant_status(
    platform_slug: str,
    tenant_slug: str,
    _user: dict = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db_session),
):
    """Activate or suspend a tenant (super admin override)."""
    result = await session.execute(
        select(Tenant).join(Platform).where(
            Platform.slug == platform_slug,
            Tenant.slug == tenant_slug,
            Tenant.status != "deleted",
        )
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_slug}' not found in platform '{platform_slug}'",
        )

    new_status = "suspended" if tenant.status == "active" else "active"
    tenant.status = new_status
    await session.flush()

    logger.info(f"Super admin toggled tenant {tenant_slug} to {new_status}")

    return {
        "tenant": tenant_slug,
        "platform": platform_slug,
        "status": new_status,
    }
