"""
Test helpers for Keycloak OAuth2 authentication.

Provides utilities to create mock JWT tokens and patch the Keycloak
verification flow so that integration tests can run without a live
Keycloak instance.

Usage in tests::

    from tests.utils.auth_helpers import create_test_token, override_auth

    # Create a token with custom claims
    token = create_test_token(tenant_id="acme", roles=["admin"])

    # Or patch the FastAPI dependency
    app.dependency_overrides[get_token_payload] = override_auth(
        tenant_id="acme", roles=["admin"]
    )
"""

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from src.config import settings


# ---------------------------------------------------------------------------
# RSA key pair for test token signing (generated once per module load)
# ---------------------------------------------------------------------------

_TEST_PRIVATE_KEY = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

_TEST_PUBLIC_KEY = _TEST_PRIVATE_KEY.public_key()

TEST_PRIVATE_KEY_PEM = _TEST_PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)

TEST_PUBLIC_KEY_PEM = _TEST_PUBLIC_KEY.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


def create_test_token(
    tenant_id: str = "test-tenant",
    client_id: str = "raas-api",
    roles: Optional[list] = None,
    sub: Optional[str] = None,
    expires_in: int = 3600,
    extra_claims: Optional[dict] = None,
) -> str:
    """
    Create a signed test JWT token mimicking Keycloak's output.

    The token is signed with an RSA key pair generated at module load
    time. This allows tests to verify token handling without needing
    a running Keycloak instance.

    Args:
        tenant_id: Custom tenant_id claim.
        client_id: Custom client_id claim (and azp).
        roles: List of realm roles (e.g., ["admin", "user"]).
        sub: Subject claim (user ID). Auto-generated if not provided.
        expires_in: Token lifetime in seconds (default 1 hour).
        extra_claims: Additional claims to include in the payload.

    Returns:
        A signed JWT token string (RS256).
    """
    if roles is None:
        roles = ["user"]

    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub or str(uuid.uuid4()),
        "iss": settings.keycloak_issuer_url,
        "aud": client_id,
        "azp": client_id,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "tenant_id": tenant_id,
        "client_id": client_id,
        "realm_access": {"roles": roles},
        "scope": "openid profile email",
        "email_verified": True,
        "preferred_username": f"testuser-{tenant_id}",
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, TEST_PRIVATE_KEY_PEM, algorithm="RS256")


def create_expired_token(
    tenant_id: str = "test-tenant",
    client_id: str = "raas-api",
) -> str:
    """
    Create a JWT token that has already expired.

    Useful for testing token expiration handling.

    Args:
        tenant_id: Custom tenant_id claim.
        client_id: Custom client_id claim.

    Returns:
        An expired JWT token string (RS256).
    """
    return create_test_token(
        tenant_id=tenant_id,
        client_id=client_id,
        expires_in=-3600,  # Expired 1 hour ago
    )


def create_test_payload(
    tenant_id: str = "test-tenant",
    client_id: str = "raas-api",
    roles: Optional[list] = None,
    sub: Optional[str] = None,
) -> dict:
    """
    Create a decoded token payload dictionary for direct injection.

    This bypasses token signing/verification entirely and is useful
    when you want to override the ``get_token_payload`` dependency.

    Args:
        tenant_id: The tenant identifier.
        client_id: The client identifier.
        roles: Realm roles.
        sub: Subject (user ID).

    Returns:
        A dictionary matching the structure of a decoded Keycloak JWT.
    """
    if roles is None:
        roles = ["user"]

    return {
        "sub": sub or str(uuid.uuid4()),
        "iss": settings.keycloak_issuer_url,
        "aud": client_id,
        "azp": client_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "tenant_id": tenant_id,
        "client_id": client_id,
        "realm_access": {"roles": roles},
        "scope": "openid profile email",
        "preferred_username": f"testuser-{tenant_id}",
    }


def override_auth(
    tenant_id: str = "test-tenant",
    client_id: str = "raas-api",
    roles: Optional[list] = None,
    sub: Optional[str] = None,
):
    """
    Return a callable that can be used as a FastAPI dependency override
    for ``get_token_payload``.

    Usage::

        from src.auth.keycloak import get_token_payload

        app.dependency_overrides[get_token_payload] = override_auth(
            tenant_id="acme", roles=["admin"]
        )

    Args:
        tenant_id: The tenant identifier.
        client_id: The client identifier.
        roles: Realm roles.
        sub: Subject (user ID).

    Returns:
        An async callable returning a test payload dictionary.
    """
    payload = create_test_payload(
        tenant_id=tenant_id,
        client_id=client_id,
        roles=roles,
        sub=sub,
    )

    async def _override():
        return payload

    return _override


def override_tenant(tenant_id: str = "test-tenant"):
    """
    Return a callable that can be used as a FastAPI dependency override
    for ``get_current_tenant_id``.

    Usage::

        from src.auth.keycloak import get_current_tenant_id

        app.dependency_overrides[get_current_tenant_id] = override_tenant("acme")

    Args:
        tenant_id: The tenant identifier to return.

    Returns:
        An async callable returning the tenant_id string.
    """

    async def _override():
        return tenant_id

    return _override
