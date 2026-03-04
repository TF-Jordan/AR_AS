"""
Event handlers — each handler is a standalone async function.
Registered to the EventBus at application startup (lifespan).
"""

from .vectorize import handle_items_vectorize
from .cache import handle_cache_invalidation
from .audit import handle_audit_log

__all__ = [
    "handle_items_vectorize",
    "handle_cache_invalidation",
    "handle_audit_log",
]
