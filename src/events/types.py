"""
Event type catalog — all domain events for the platform.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .base import BaseEvent


# ── Items ──────────────────────────────────────────────

@dataclass
class ItemsImported(BaseEvent):
    """Emitted after items are inserted in DB (before vectorization)."""
    item_ids: List[str] = field(default_factory=list)
    items_for_embedding: List[Dict[str, Any]] = field(default_factory=list)
    vectorize: bool = True


@dataclass
class ItemDeleted(BaseEvent):
    """Emitted when an item is deleted from a tenant catalog."""
    item_id: str = ""


# ── Tenant lifecycle ───────────────────────────────────

@dataclass
class TenantProvisioned(BaseEvent):
    """Emitted after a new tenant is fully provisioned."""
    tenant_name: str = ""
    domain: str = ""


@dataclass
class TenantDeprovisioned(BaseEvent):
    """Emitted after a tenant is soft-deleted and deprovisioned."""
    pass


# ── Recommendations ────────────────────────────────────

@dataclass
class RecommendationServed(BaseEvent):
    """Emitted after a recommendation response is returned."""
    query: str = ""
    results_count: int = 0
    cached: bool = False
    processing_time_ms: float = 0.0


# ── Vectorization ──────────────────────────────────────

@dataclass
class VectorizationCompleted(BaseEvent):
    """Emitted after successful background vectorization."""
    item_count: int = 0
    duration_ms: float = 0.0


@dataclass
class VectorizationFailed(BaseEvent):
    """Emitted when background vectorization fails."""
    item_ids: List[str] = field(default_factory=list)
    error: str = ""
