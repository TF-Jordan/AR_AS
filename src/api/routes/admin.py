"""
Administration API endpoints for tenant management.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import require_admin
from src.api.dependencies import get_db_session
from src.database.tenant_models import Tenant, generate_api_key
from src.database.tenant_manager import get_tenant_manager
from src.events.bus import get_event_bus
from src.events.types import TenantProvisioned, TenantDeprovisioned

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# Request / Response Schemas
# ============================================================

class ScoringCriterion(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    weight: float = Field(..., gt=0.0, le=1.0)


class CreateTenantRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=2, max_length=100)
    domain: str = Field(..., min_length=1, max_length=100)
    scoring: Dict[str, List[ScoringCriterion]] = Field(
        ...,
        description="Scoring configuration with criteria and weights",
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9][a-z0-9_-]{1,98}$', v):
            raise ValueError(
                "Slug must be lowercase alphanumeric with hyphens/underscores, "
                "start with a letter or digit, 2-100 chars"
            )
        return v

    @field_validator("scoring")
    @classmethod
    def validate_scoring(cls, v: Dict) -> Dict:
        criteria = v.get("criteria", [])
        if not criteria:
            raise ValueError("At least one scoring criterion is required")
        total_weight = sum(c.weight for c in criteria)
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total_weight:.2f}")
        return v


class UpdateTenantRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    domain: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[str] = Field(None, pattern=r'^(active|suspended)$')
    scoring: Optional[Dict[str, List[ScoringCriterion]]] = None

    @field_validator("scoring")
    @classmethod
    def validate_scoring(cls, v: Optional[Dict]) -> Optional[Dict]:
        if v is None:
            return v
        criteria = v.get("criteria", [])
        if not criteria:
            raise ValueError("At least one scoring criterion is required")
        total_weight = sum(c.weight for c in criteria)
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total_weight:.2f}")
        return v


class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    slug: str
    domain: str
    api_key: str
    status: str
    scoring_config: Dict[str, Any]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    tenants: List[TenantResponse]
    total: int


# ============================================================
# Admin Endpoints
# ============================================================

@router.get(
    "/status",
    summary="System status",
    description="Get overall system status.",
)
async def system_status():
    """Get system status overview."""
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


@router.post(
    "/tenants",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant",
    dependencies=[Depends(require_admin)],
)
async def create_tenant(
    request: CreateTenantRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Create a new tenant with automatic provisioning.
    Creates PostgreSQL schema and Qdrant collection.
    """
    # Check slug uniqueness
    existing = await session.execute(
        select(Tenant).where(Tenant.slug == request.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with slug '{request.slug}' already exists",
        )

    # Create tenant record
    scoring_config = {
        "criteria": [c.model_dump() for c in request.scoring["criteria"]]
    }

    tenant = Tenant(
        name=request.name,
        slug=request.slug,
        domain=request.domain,
        api_key=generate_api_key(),
        scoring_config=scoring_config,
    )
    session.add(tenant)
    await session.flush()

    # Provision infrastructure
    tenant_manager = get_tenant_manager()
    try:
        await tenant_manager.provision_tenant(session, request.slug)
    except Exception as e:
        logger.error(f"Provisioning failed for {request.slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tenant provisioning failed: {e}",
        )

    logger.info(f"Tenant created: {request.slug} ({request.domain})")

    # Publish lifecycle event
    await get_event_bus().publish(TenantProvisioned(
        tenant_slug=request.slug,
        tenant_name=request.name,
        domain=request.domain,
    ))

    return TenantResponse(
        tenant_id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        domain=tenant.domain,
        api_key=tenant.api_key,
        status=tenant.status,
        scoring_config=tenant.scoring_config,
        created_at=tenant.created_at.isoformat(),
        updated_at=tenant.updated_at.isoformat(),
    )


@router.get(
    "/tenants",
    response_model=TenantListResponse,
    summary="List all tenants",
    dependencies=[Depends(require_admin)],
)
async def list_tenants(
    session: AsyncSession = Depends(get_db_session),
):
    """List all tenants."""
    result = await session.execute(
        select(Tenant).where(Tenant.status != "deleted").order_by(Tenant.created_at.desc())
    )
    tenants = result.scalars().all()

    count_result = await session.execute(
        select(func.count(Tenant.id)).where(Tenant.status != "deleted")
    )
    total = count_result.scalar() or 0

    return TenantListResponse(
        tenants=[
            TenantResponse(
                tenant_id=str(t.id),
                name=t.name,
                slug=t.slug,
                domain=t.domain,
                api_key=t.api_key,
                status=t.status,
                scoring_config=t.scoring_config,
                created_at=t.created_at.isoformat(),
                updated_at=t.updated_at.isoformat(),
            )
            for t in tenants
        ],
        total=total,
    )


@router.get(
    "/tenants/{slug}",
    response_model=TenantResponse,
    summary="Get tenant details",
    dependencies=[Depends(require_admin)],
)
async def get_tenant(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get details of a specific tenant."""
    result = await session.execute(
        select(Tenant).where(Tenant.slug == slug, Tenant.status != "deleted")
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{slug}' not found",
        )

    return TenantResponse(
        tenant_id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        domain=tenant.domain,
        api_key=tenant.api_key,
        status=tenant.status,
        scoring_config=tenant.scoring_config,
        created_at=tenant.created_at.isoformat(),
        updated_at=tenant.updated_at.isoformat(),
    )


@router.put(
    "/tenants/{slug}",
    response_model=TenantResponse,
    summary="Update a tenant",
    dependencies=[Depends(require_admin)],
)
async def update_tenant(
    slug: str,
    request: UpdateTenantRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Update tenant configuration."""
    result = await session.execute(
        select(Tenant).where(Tenant.slug == slug, Tenant.status != "deleted")
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{slug}' not found",
        )

    if request.name is not None:
        tenant.name = request.name
    if request.domain is not None:
        tenant.domain = request.domain
    if request.status is not None:
        tenant.status = request.status
    if request.scoring is not None:
        tenant.scoring_config = {
            "criteria": [c.model_dump() for c in request.scoring["criteria"]]
        }

    await session.flush()
    logger.info(f"Tenant updated: {slug}")

    return TenantResponse(
        tenant_id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        domain=tenant.domain,
        api_key=tenant.api_key,
        status=tenant.status,
        scoring_config=tenant.scoring_config,
        created_at=tenant.created_at.isoformat(),
        updated_at=tenant.updated_at.isoformat(),
    )


@router.delete(
    "/tenants/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tenant",
    dependencies=[Depends(require_admin)],
)
async def delete_tenant(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Soft-delete a tenant and deprovision its infrastructure.
    """
    result = await session.execute(
        select(Tenant).where(Tenant.slug == slug, Tenant.status != "deleted")
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{slug}' not found",
        )

    # Deprovision infrastructure
    tenant_manager = get_tenant_manager()
    try:
        await tenant_manager.deprovision_tenant(session, slug)
    except Exception as e:
        logger.error(f"Deprovisioning failed for {slug}: {e}")

    tenant.status = "deleted"
    await session.flush()
    logger.info(f"Tenant deleted: {slug}")

    # Publish lifecycle event (cache purge, audit)
    await get_event_bus().publish(TenantDeprovisioned(
        tenant_slug=slug,
    ))


@router.post(
    "/tenants/{slug}/regenerate-key",
    response_model=TenantResponse,
    summary="Regenerate tenant API key",
    dependencies=[Depends(require_admin)],
)
async def regenerate_tenant_key(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Regenerate the API key for a tenant."""
    result = await session.execute(
        select(Tenant).where(Tenant.slug == slug, Tenant.status != "deleted")
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{slug}' not found",
        )

    tenant.api_key = generate_api_key()
    await session.flush()
    logger.info(f"API key regenerated for tenant: {slug}")

    return TenantResponse(
        tenant_id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        domain=tenant.domain,
        api_key=tenant.api_key,
        status=tenant.status,
        scoring_config=tenant.scoring_config,
        created_at=tenant.created_at.isoformat(),
        updated_at=tenant.updated_at.isoformat(),
    )


@router.get(
    "/tenants/{slug}/stats",
    summary="Get tenant statistics",
    dependencies=[Depends(require_admin)],
)
async def get_tenant_stats(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get detailed statistics for a specific tenant (items, vectors, cache)."""
    result = await session.execute(
        select(Tenant).where(Tenant.slug == slug, Tenant.status != "deleted")
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{slug}' not found",
        )

    tenant_manager = get_tenant_manager()
    item_count = await tenant_manager.count_items(session, slug)

    from src.modules.module2_recommendation import get_vector_store
    vector_store = get_vector_store()
    collection_info = vector_store.get_collection_info(slug)

    return {
        "tenant": slug,
        "items_count": item_count,
        "vectors_count": collection_info.get("vectors_count", 0),
        "collection_status": collection_info.get("status", "unknown"),
    }


@router.get(
    "/metrics",
    summary="Platform metrics overview",
    dependencies=[Depends(require_admin)],
)
async def get_platform_metrics(
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get platform-wide metrics for the monitoring dashboard.
    Returns active tenants count, total items, total vectors, and service health.
    """
    # Count active tenants
    active_result = await session.execute(
        select(func.count(Tenant.id)).where(Tenant.status == "active")
    )
    active_tenants = active_result.scalar() or 0

    # Count total tenants (non-deleted)
    total_result = await session.execute(
        select(func.count(Tenant.id)).where(Tenant.status != "deleted")
    )
    total_tenants = total_result.scalar() or 0

    # Get all active tenant slugs for aggregate stats
    slugs_result = await session.execute(
        select(Tenant.slug).where(Tenant.status == "active")
    )
    tenant_slugs = [row[0] for row in slugs_result.fetchall()]

    # Aggregate item counts
    tenant_manager = get_tenant_manager()
    total_items = 0
    total_vectors = 0
    tenant_stats = []

    from src.modules.module2_recommendation import get_vector_store
    vector_store = get_vector_store()

    for slug in tenant_slugs:
        try:
            items = await tenant_manager.count_items(session, slug)
            collection_info = vector_store.get_collection_info(slug)
            vectors = collection_info.get("vectors_count", 0)
            total_items += items
            total_vectors += vectors
            tenant_stats.append({
                "slug": slug,
                "items_count": items,
                "vectors_count": vectors,
            })
        except Exception as e:
            logger.warning(f"Error getting stats for tenant {slug}: {e}")
            tenant_stats.append({
                "slug": slug,
                "items_count": 0,
                "vectors_count": 0,
                "error": str(e),
            })

    # Service health
    services = {}
    try:
        from src.modules.module2_recommendation.cache import get_cache_manager
        cache = get_cache_manager()
        services["redis"] = await cache.health_check()
    except Exception:
        services["redis"] = False

    try:
        services["qdrant"] = vector_store.health_check()
    except Exception:
        services["qdrant"] = False

    try:
        from sqlalchemy import text as sa_text
        await session.execute(sa_text("SELECT 1"))
        services["postgresql"] = True
    except Exception:
        services["postgresql"] = False

    return {
        "active_tenants": active_tenants,
        "total_tenants": total_tenants,
        "total_items": total_items,
        "total_vectors": total_vectors,
        "tenant_stats": tenant_stats,
        "services": services,
    }
