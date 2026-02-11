"""
Authentication middleware for the RaaS platform.

Extracts tenant information from JWT tokens and attaches it to
``request.state`` so that it is available throughout the request
lifecycle without re-parsing the token.

This middleware is optional -- routes can also use the FastAPI
dependency ``get_current_tenant_id`` directly. The middleware is
useful for:
- Logging and monitoring (tenant info in every log line)
- Centralized token validation before routing
- Attaching tenant context for non-dependency-injected code
"""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.auth.keycloak import keycloak_auth

logger = logging.getLogger(__name__)

# Paths that should not require authentication
_PUBLIC_PATHS = frozenset({
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
})

# Path prefixes that are public
_PUBLIC_PREFIXES = (
    "/api/v1/health",
)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts tenant information from JWT tokens and
    attaches it to ``request.state``.

    For public endpoints (health checks, docs), the middleware is a
    pass-through. For all other endpoints, the Authorization header is
    inspected and, if present, the token is verified and tenant context
    is set on the request state.

    Attributes set on ``request.state``:
        - tenant_id (str | None): The tenant identifier from the JWT.
        - client_id (str | None): The client identifier from the JWT.
        - token_payload (dict | None): The full decoded JWT payload.
        - is_authenticated (bool): Whether a valid token was present.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Initialize request state defaults
        request.state.tenant_id = None
        request.state.client_id = None
        request.state.token_payload = None
        request.state.is_authenticated = False

        # Skip auth for public paths
        path = request.url.path
        if path in _PUBLIC_PATHS or path.startswith(_PUBLIC_PREFIXES):
            return await call_next(request)

        # Try to extract and verify the Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # Build a minimal credentials object for verify_token
                from fastapi.security import HTTPAuthorizationCredentials

                token = auth_header[7:]  # Strip "Bearer "
                credentials = HTTPAuthorizationCredentials(
                    scheme="Bearer", credentials=token
                )

                payload = await keycloak_auth.verify_token(credentials)

                # Attach to request state
                request.state.token_payload = payload
                request.state.tenant_id = payload.get("tenant_id")
                request.state.client_id = (
                    payload.get("client_id") or payload.get("azp")
                )
                request.state.is_authenticated = True

                logger.debug(
                    "Auth middleware: tenant context set",
                    extra={
                        "tenant_id": request.state.tenant_id,
                        "client_id": request.state.client_id,
                        "sub": payload.get("sub"),
                    },
                )
            except Exception as exc:
                # Token verification failed -- do NOT block here.
                # Let the route-level dependency raise the proper HTTP error.
                logger.debug(
                    "Auth middleware: token verification failed: %s",
                    exc,
                )

        response = await call_next(request)

        # Attach rate limit headers if they were set by the rate limiter
        rate_info = getattr(request.state, "rate_limit_info", None)
        if rate_info:
            response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(
                rate_info["remaining"]
            )
            response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])

        return response
