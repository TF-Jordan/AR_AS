"""
Custom middleware for the API.
"""

import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.utils.context import set_correlation_id, clear_all_context

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to manage correlation IDs for request tracing.

    Extracts or generates a correlation ID for each request
    and propagates it through the request context.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract or generate correlation ID
        correlation_id = request.headers.get(
            "X-Correlation-ID", str(uuid4())
        )
        set_correlation_id(correlation_id)

        start_time = time.time()

        try:
            response = await call_next(request)

            duration_ms = (time.time() - start_time) * 1000
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Processing-Time-Ms"] = f"{duration_ms:.2f}"

            logger.info(
                f"{request.method} {request.url.path} - {response.status_code} ({duration_ms:.2f}ms)",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": correlation_id,
                },
            )

            return response

        finally:
            clear_all_context()
