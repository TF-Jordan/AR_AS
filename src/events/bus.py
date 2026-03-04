"""
Internal Event Bus — in-process async pub/sub (Amazon pattern).

- Handlers run as background asyncio tasks (fire-and-forget)
- Errors are captured and logged, never propagated to the publisher
- Supports wildcard "*" to listen to ALL events
- drain() ensures clean shutdown
"""

import asyncio
import logging
from typing import Awaitable, Callable, Dict, List, Optional, Type

from .base import BaseEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[BaseEvent], Awaitable[None]]


class EventBus:
    """In-process async event bus with topic-based routing."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._running_tasks: set[asyncio.Task] = set()

    # ── Subscribe ──────────────────────────────────────

    def subscribe(self, event_type: Type[BaseEvent], handler: EventHandler) -> None:
        """Subscribe a handler to a specific event type."""
        key = event_type.__name__
        self._handlers.setdefault(key, []).append(handler)
        logger.info(f"EventBus: {handler.__name__} -> {key}")

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe a handler to ALL events (wildcard)."""
        self._handlers.setdefault("*", []).append(handler)
        logger.info(f"EventBus: {handler.__name__} -> * (all events)")

    # ── Publish ────────────────────────────────────────

    async def publish(self, event: BaseEvent) -> None:
        """
        Publish an event. Matching handlers execute in background tasks.
        Returns immediately — does NOT wait for handlers to finish.
        """
        event_name = event.event_type
        handlers = self._handlers.get(event_name, []) + self._handlers.get("*", [])

        if not handlers:
            logger.debug(f"EventBus: no handlers for {event_name}")
            return

        logger.info(
            f"EventBus: publishing {event_name} "
            f"(id={event.event_id[:8]}...) to {len(handlers)} handler(s)"
        )

        for handler in handlers:
            task = asyncio.create_task(
                self._safe_execute(handler, event),
                name=f"event:{event_name}:{handler.__name__}",
            )
            self._running_tasks.add(task)
            task.add_done_callback(self._running_tasks.discard)

    # ── Internal ───────────────────────────────────────

    async def _safe_execute(self, handler: EventHandler, event: BaseEvent) -> None:
        """Execute a handler with full error capture."""
        try:
            await handler(event)
        except Exception:
            logger.error(
                f"EventBus: handler {handler.__name__} failed for "
                f"{event.event_type} (id={event.event_id})",
                exc_info=True,
            )

    # ── Lifecycle ──────────────────────────────────────

    async def drain(self, timeout: float = 30.0) -> None:
        """Wait for all running tasks to complete (for clean shutdown)."""
        if not self._running_tasks:
            return
        logger.info(f"EventBus: draining {len(self._running_tasks)} pending task(s)...")
        done, pending = await asyncio.wait(self._running_tasks, timeout=timeout)
        if pending:
            logger.warning(f"EventBus: {len(pending)} task(s) did not finish in {timeout}s")
            for task in pending:
                task.cancel()

    @property
    def handler_count(self) -> int:
        return sum(len(h) for h in self._handlers.values())

    @property
    def pending_tasks(self) -> int:
        return len(self._running_tasks)


# ── Singleton ──────────────────────────────────────────

_bus_instance: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the singleton event bus."""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = EventBus()
    return _bus_instance
