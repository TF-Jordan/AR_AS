"""
Base event class — all events inherit from this.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class BaseEvent:
    """Base class for all internal events."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_slug: Optional[str] = None
    correlation_id: Optional[str] = None

    @property
    def event_type(self) -> str:
        return self.__class__.__name__
