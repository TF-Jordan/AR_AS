"""
Internal Event Bus module — Amazon-style pub/sub pattern.
Fully in-process, zero external dependencies.
"""

from .base import BaseEvent
from .bus import EventBus, get_event_bus
from .types import (
    ItemsImported,
    ItemDeleted,
    TenantProvisioned,
    TenantDeprovisioned,
    RecommendationServed,
    VectorizationCompleted,
    VectorizationFailed,
)

__all__ = [
    "BaseEvent",
    "EventBus",
    "get_event_bus",
    "ItemsImported",
    "ItemDeleted",
    "TenantProvisioned",
    "TenantDeprovisioned",
    "RecommendationServed",
    "VectorizationCompleted",
    "VectorizationFailed",
]
