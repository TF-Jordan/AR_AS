"""
Vectorization handler — encodes items and upserts to Qdrant in background.
"""

import logging
import time

from src.events.base import BaseEvent
from src.events.types import ItemsImported, VectorizationCompleted, VectorizationFailed

logger = logging.getLogger(__name__)


async def handle_items_vectorize(event: BaseEvent) -> None:
    """Vectorize imported items in background after HTTP response is sent."""
    if not isinstance(event, ItemsImported):
        return

    if not event.vectorize or not event.items_for_embedding:
        logger.debug(f"Skipping vectorization for {event.tenant_slug}: nothing to vectorize")
        return

    from src.modules.module2_recommendation import get_embedding_service, get_vector_store
    from src.events.bus import get_event_bus

    embedding_service = get_embedding_service()
    vector_store = get_vector_store()
    bus = get_event_bus()

    start = time.perf_counter()

    try:
        # Encode all texts in batch
        texts = [item["text"] for item in event.items_for_embedding]
        vectors = embedding_service.encode_batch_for_qdrant(texts)

        # Build batch for Qdrant
        batch_items = []
        for item_info, vector in zip(event.items_for_embedding, vectors):
            batch_items.append({
                "real_product_id": item_info["id"],
                "vector": vector,
                "metadata": item_info.get("data", {}),
            })

        # Upsert to Qdrant
        vectors_indexed = vector_store.upsert_vectors_batch(event.tenant_slug, batch_items)

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"Vectorized {vectors_indexed} items for tenant={event.tenant_slug} "
            f"in {duration_ms:.0f}ms"
        )

        # Emit completion event
        await bus.publish(VectorizationCompleted(
            tenant_slug=event.tenant_slug,
            correlation_id=event.correlation_id,
            item_count=vectors_indexed,
            duration_ms=duration_ms,
        ))

    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(f"Vectorization failed for tenant={event.tenant_slug}: {e}")

        await bus.publish(VectorizationFailed(
            tenant_slug=event.tenant_slug,
            correlation_id=event.correlation_id,
            item_ids=event.item_ids,
            error=str(e),
        ))
        raise  # re-raise so _safe_execute logs the full traceback
