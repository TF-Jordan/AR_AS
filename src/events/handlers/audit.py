"""
Audit log handler — structured log of every event for traceability.
"""

import logging

from src.events.base import BaseEvent

logger = logging.getLogger("audit")


async def handle_audit_log(event: BaseEvent) -> None:
    """Log every event with structured data for audit trail."""
    logger.info(
        f"[AUDIT] {event.event_type}",
        extra={
            "event_type": event.event_type,
            "event_id": event.event_id,
            "tenant_slug": event.tenant_slug,
            "timestamp": event.timestamp.isoformat(),
            "correlation_id": event.correlation_id,
        },
    )
