"""
Cache invalidation handler — purges Redis keys when data changes.
"""

import logging

from src.events.base import BaseEvent
from src.events.types import ItemsImported, ItemDeleted, TenantDeprovisioned

logger = logging.getLogger(__name__)


async def handle_cache_invalidation(event: BaseEvent) -> None:
    """Invalidate tenant cache when catalog data changes."""
    from src.modules.module2_recommendation import get_cache_manager

    cache = get_cache_manager()

    if isinstance(event, ItemsImported):
        deleted = await cache.invalidate_tenant(event.tenant_slug)
        logger.info(
            f"Cache invalidated for tenant={event.tenant_slug} "
            f"(items imported, {deleted} keys removed)"
        )

    elif isinstance(event, ItemDeleted):
        deleted = await cache.invalidate_item(event.tenant_slug, event.item_id)
        logger.info(
            f"Cache invalidated for tenant={event.tenant_slug} "
            f"item={event.item_id}"
        )

    elif isinstance(event, TenantDeprovisioned):
        deleted = await cache.invalidate_tenant(event.tenant_slug)
        logger.info(
            f"Cache purged for deprovisioned tenant={event.tenant_slug} "
            f"({deleted} keys removed)"
        )
