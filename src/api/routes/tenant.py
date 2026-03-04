"""
Tenant-facing API endpoints.
These routes are authenticated via the tenant's API key.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_tenant
from src.api.dependencies import get_db_session, get_orchestrator_dep
from src.api.schemas import (
    ImportItemsRequest,
    ImportResponse,
    RecommendationRequest,
    RecommendationResponse,
    RankedProductResponse,
)
from src.database.tenant_models import Tenant
from src.database.tenant_manager import get_tenant_manager
from src.modules.module2_recommendation import get_vector_store
from src.modules.module3_orchestration import Orchestrator
from src.events.bus import get_event_bus
from src.events.types import ItemsImported, ItemDeleted, RecommendationServed
from src.utils.context import get_correlation_id

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# Items management
# ============================================================

@router.post(
    "/items/import",
    response_model=ImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import items into your catalog",
)
async def import_items(
    request: ImportItemsRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Import items into the tenant's catalog.
    Each item must have an 'id' field. All other fields are stored as JSONB.
    Optionally generates embeddings and indexes them in Qdrant.
    """
    logger.info(f"Import request: tenant={tenant.slug}, items={len(request.items)}")

    # Validate all items have 'id'
    for i, item in enumerate(request.items):
        if "id" not in item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item at index {i} is missing required 'id' field",
            )

    tenant_manager = get_tenant_manager()

    # Insert items into PostgreSQL (fast, synchronous part)
    items_imported = await tenant_manager.insert_items(
        session, tenant.slug, request.items
    )

    # Prepare embedding data for background vectorization
    items_for_embedding = []
    if request.vectorize:
        for item in request.items:
            item_id = str(item["id"])
            data = {k: v for k, v in item.items() if k != "id"}

            embedding_text = item.get("embedding_text")
            if not embedding_text:
                text_parts = []
                for k, v in data.items():
                    if isinstance(v, str):
                        text_parts.append(f"{k}: {v}")
                embedding_text = ". ".join(text_parts)

            if embedding_text:
                items_for_embedding.append({
                    "id": item_id,
                    "text": embedding_text,
                    "data": data,
                })

    # Publish event — vectorization + cache invalidation happen in background
    await get_event_bus().publish(ItemsImported(
        tenant_slug=tenant.slug,
        correlation_id=get_correlation_id(),
        item_ids=[str(item["id"]) for item in request.items],
        items_for_embedding=items_for_embedding,
        vectorize=request.vectorize,
    ))

    logger.info(
        f"Import completed: tenant={tenant.slug}, "
        f"items={items_imported}, vectorization={'queued' if request.vectorize else 'skipped'}"
    )

    return ImportResponse(
        status="accepted",
        items_imported=items_imported,
        vectors_indexed=0,
        tenant=tenant.slug,
    )


@router.get(
    "/items",
    summary="List items in your catalog",
)
async def list_items(
    limit: int = 100,
    offset: int = 0,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
):
    """List items in the tenant's catalog."""
    tenant_manager = get_tenant_manager()
    items = await tenant_manager.get_items(session, tenant.slug, limit=limit, offset=offset)
    total = await tenant_manager.count_items(session, tenant.slug)

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "tenant": tenant.slug,
    }


@router.get(
    "/items/{item_id}",
    summary="Get a specific item",
)
async def get_item(
    item_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
):
    """Get a specific item from the tenant's catalog."""
    tenant_manager = get_tenant_manager()
    item = await tenant_manager.get_item(session, tenant.slug, item_id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_id}' not found",
        )

    return item


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item",
)
async def delete_item(
    item_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
):
    """Delete an item from the tenant's catalog and vector store."""
    tenant_manager = get_tenant_manager()
    deleted = await tenant_manager.delete_item(session, tenant.slug, item_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_id}' not found",
        )

    # Delete from Qdrant (synchronous — must be consistent)
    vector_store = get_vector_store()
    vector_store.delete_by_product_id(tenant.slug, item_id)

    # Publish event — cache invalidation happens in background
    await get_event_bus().publish(ItemDeleted(
        tenant_slug=tenant.slug,
        correlation_id=get_correlation_id(),
        item_id=item_id,
    ))


# ============================================================
# Recommendations
# ============================================================

@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    summary="Get recommendations",
)
async def get_recommendations(
    request: RecommendationRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
    orchestrator: Orchestrator = Depends(get_orchestrator_dep),
):
    """
    Get recommendations based on a query.

    The system:
    1. Analyzes sentiment of the query
    2. Generates embeddings and searches for similar items
    3. Applies your custom scoring criteria
    4. Returns ranked results
    """
    logger.info(f"Recommendation request: tenant={tenant.slug}, query='{request.query[:50]}...'")

    try:
        scoring_criteria = tenant.scoring_config.get("criteria", [])

        result = await orchestrator.process_recommendation(
            tenant_slug=tenant.slug,
            query=request.query,
            scoring_criteria=scoring_criteria,
            session=session,
            top_k=request.top_k,
            client_id=request.client_id,
        )

        response = RecommendationResponse(
            status=result.get("status", "success"),
            tenant=tenant.slug,
            recommendations=[
                RankedProductResponse(**r) for r in result.get("recommendations", [])
            ],
            total_results=result.get("total_results", 0),
            sentiment_query=result.get("sentiment_query", 0.0),
            sentiment_label=result.get("sentiment_label"),
            temps_traitement_ms=result.get("temps_traitement_ms", 0.0),
            cached=result.get("cached", False),
        )

        # Publish event for audit/metrics (background)
        await get_event_bus().publish(RecommendationServed(
            tenant_slug=tenant.slug,
            correlation_id=get_correlation_id(),
            query=request.query[:200],
            results_count=response.total_results,
            cached=response.cached,
            processing_time_ms=response.temps_traitement_ms,
        ))

        return response

    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================
# Tenant info
# ============================================================

@router.get(
    "/me",
    summary="Get current tenant info",
)
async def get_tenant_info(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
):
    """Get information about the authenticated tenant."""
    tenant_manager = get_tenant_manager()
    item_count = await tenant_manager.count_items(session, tenant.slug)

    vector_store = get_vector_store()
    collection_info = vector_store.get_collection_info(tenant.slug)

    return {
        "tenant_id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "domain": tenant.domain,
        "scoring_config": tenant.scoring_config,
        "items_count": item_count,
        "vectors_count": collection_info.get("vectors_count", 0),
    }
