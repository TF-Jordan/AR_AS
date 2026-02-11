"""
Authentication and authorization module.

Provides Keycloak OAuth2 integration for the RaaS platform.
"""

from .keycloak import (
    KeycloakAuth,
    keycloak_auth,
    get_token_payload,
    get_current_tenant_id,
    get_current_client_id,
    require_admin,
)

__all__ = [
    "KeycloakAuth",
    "keycloak_auth",
    "get_token_payload",
    "get_current_tenant_id",
    "get_current_client_id",
    "require_admin",
]
