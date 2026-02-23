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
from src.modules.module2_recommendation import (
    get_embedding_service,
    get_vector_store,
)
from src.modules.module3_orchestration import Orchestrator

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

    # Insert items into PostgreSQL
    items_imported = await tenant_manager.insert_items(
        session, tenant.slug, request.items
    )

    # Generate embeddings and index in Qdrant
    vectors_indexed = 0
    if request.vectorize:
        embedding_service = get_embedding_service()
        vector_store = get_vector_store()

        # Fetch embedding texts
        items_for_embedding = []
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

        if items_for_embedding:
            texts = [i["text"] for i in items_for_embedding]
            vectors = embedding_service.encode_batch_for_qdrant(texts)

            batch_items = []
            for item_info, vector in zip(items_for_embedding, vectors):
                batch_items.append({
                    "real_product_id": item_info["id"],
                    "vector": vector,
                    "metadata": item_info["data"],
                })

            vectors_indexed = vector_store.upsert_vectors_batch(
                tenant.slug, batch_items
            )

    logger.info(
        f"Import completed: tenant={tenant.slug}, "
        f"items={items_imported}, vectors={vectors_indexed}"
    )

    return ImportResponse(
        status="success",
        items_imported=items_imported,
        vectors_indexed=vectors_indexed,
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

    # Also delete from Qdrant
    vector_store = get_vector_store()
    vector_store.delete_by_product_id(tenant.slug, item_id)


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

        return RecommendationResponse(
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
