"""
Keycloak OAuth2 authentication handler for the RaaS platform.

Responsibilities:
- Verify JWT tokens signed by Keycloak (RS256)
- Extract custom claims (tenant_id, client_id)
- Provide FastAPI dependencies for route protection
- Cache JWKS keys for performance via PyJWKClient

Environment:
- Keycloak 25.0 running in Docker
- Realm: "raas"
- Custom JWT claims: tenant_id, client_id
"""

import logging
from typing import Optional

import jwt
from jwt import PyJWKClient, PyJWKClientError
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config import settings

logger = logging.getLogger(__name__)

# FastAPI security scheme
security = HTTPBearer(
    auto_error=True,
    description="Keycloak JWT Bearer token",
)


class KeycloakAuth:
    """
    Keycloak OAuth2 authentication handler.

    Verifies JWT tokens issued by Keycloak, extracts custom claims
    (tenant_id, client_id), and provides FastAPI-compatible dependencies
    for protecting API routes.

    The JWKS (JSON Web Key Set) client is initialized lazily on first use
    and caches public keys automatically (PyJWKClient default behavior).
    """

    def __init__(self) -> None:
        self._jwks_client: Optional[PyJWKClient] = None
        self._jwks_url: str = settings.keycloak_jwks_url
        self._issuer: str = settings.keycloak_issuer_url
        self._audience: str = settings.keycloak_client_id

    @property
    def jwks_client(self) -> PyJWKClient:
        """
        Lazily initialize the JWKS client.

        PyJWKClient fetches and caches signing keys from the Keycloak
        JWKS endpoint. Lazy initialization avoids startup failures when
        Keycloak is not yet available.
        """
        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(
                self._jwks_url,
                cache_jwk_set=True,
                lifespan=300,  # Cache keys for 5 minutes
            )
            logger.info(
                "JWKS client initialized",
                extra={"jwks_url": self._jwks_url},
            )
        return self._jwks_client

    async def verify_token(
        self, credentials: HTTPAuthorizationCredentials
    ) -> dict:
        """
        Verify a JWT token and return the decoded payload.

        Steps:
            1. Extract the raw token from the Authorization header.
            2. Fetch the signing key from the Keycloak JWKS endpoint.
            3. Decode and verify the token:
               - RS256 signature validation
               - Expiration check (exp claim)
               - Audience verification (must contain keycloak_client_id)
               - Issuer verification (must match Keycloak realm URL)
            4. Return the full decoded payload with all claims.

        Args:
            credentials: HTTP Bearer credentials from the Authorization header.

        Returns:
            Decoded JWT payload as a dictionary.

        Raises:
            HTTPException(401): Token is invalid, expired, or signature
                verification fails.
            HTTPException(403): Audience mismatch -- token was issued for
                a different client.
        """
        token = credentials.credentials

        # Step 1: Fetch the signing key from JWKS
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
        except PyJWKClientError as exc:
            logger.error(
                "Failed to fetch signing key from Keycloak JWKS endpoint: %s",
                exc,
                extra={"jwks_url": self._jwks_url},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials: unable to fetch signing key",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        except Exception as exc:
            logger.error(
                "Unexpected error fetching signing key: %s",
                exc,
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        # Step 2: Decode and verify the token
        try:
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": ["exp", "iss", "sub"],
                },
            )
        except jwt.ExpiredSignatureError as exc:
            logger.warning("Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        except jwt.InvalidAudienceError as exc:
            logger.warning(
                "Token audience mismatch: expected %s", self._audience
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Token audience mismatch: expected '{self._audience}'"
                ),
            ) from exc
        except jwt.InvalidIssuerError as exc:
            logger.warning(
                "Token issuer mismatch: expected %s", self._issuer
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token issuer mismatch",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        except jwt.DecodeError as exc:
            logger.warning("Token decode error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        except jwt.InvalidTokenError as exc:
            logger.warning("Invalid token: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        logger.debug(
            "Token verified successfully",
            extra={
                "sub": payload.get("sub"),
                "tenant_id": payload.get("tenant_id"),
            },
        )
        return payload

    async def get_current_tenant(self, token_payload: dict) -> str:
        """
        Extract tenant_id from a verified token payload.

        Args:
            token_payload: Decoded JWT payload dictionary.

        Returns:
            The tenant_id string.

        Raises:
            HTTPException(403): If tenant_id claim is missing from the token.
        """
        tenant_id = token_payload.get("tenant_id")
        if not tenant_id:
            logger.warning(
                "Token missing tenant_id claim",
                extra={"sub": token_payload.get("sub")},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token does not contain tenant_id claim. "
                "Ensure the Keycloak mapper is configured.",
            )
        return tenant_id

    async def get_client_id(self, token_payload: dict) -> str:
        """
        Extract client_id from a verified token payload.

        The client_id may come from the ``client_id`` custom claim
        or fall back to the standard ``azp`` (authorized party) claim.

        Args:
            token_payload: Decoded JWT payload dictionary.

        Returns:
            The client_id string.

        Raises:
            HTTPException(403): If neither client_id nor azp claim is present.
        """
        client_id = token_payload.get("client_id") or token_payload.get("azp")
        if not client_id:
            logger.warning(
                "Token missing client_id claim",
                extra={"sub": token_payload.get("sub")},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token does not contain client_id claim.",
            )
        return client_id

    async def require_admin_role(self, token_payload: dict) -> bool:
        """
        Check whether the user has the 'admin' role in realm_access.

        Keycloak stores realm roles in the ``realm_access.roles`` array
        within the JWT payload.

        Args:
            token_payload: Decoded JWT payload dictionary.

        Returns:
            True if the user has the admin role.

        Raises:
            HTTPException(403): If the user does not have the admin role.
        """
        realm_access = token_payload.get("realm_access", {})
        roles = realm_access.get("roles", [])

        if "admin" not in roles:
            logger.warning(
                "Admin role required but not present",
                extra={
                    "sub": token_payload.get("sub"),
                    "roles": roles,
                },
            )
            current_roles = ", ".join(roles) if roles else "none"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Admin role required. Current roles: {current_roles}",
            )
        return True


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

keycloak_auth = KeycloakAuth()


# ---------------------------------------------------------------------------
# FastAPI Dependencies
# ---------------------------------------------------------------------------

async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """
    FastAPI dependency: verify the Bearer token and return the decoded payload.

    Usage::

        @router.get("/protected")
        async def protected_route(payload: dict = Depends(get_token_payload)):
            ...
    """
    return await keycloak_auth.verify_token(credentials)


async def get_current_tenant_id(
    payload: dict = Depends(get_token_payload),
) -> str:
    """
    FastAPI dependency: extract tenant_id from the verified token.

    Usage::

        @router.get("/data")
        async def tenant_data(tenant_id: str = Depends(get_current_tenant_id)):
            ...
    """
    return await keycloak_auth.get_current_tenant(payload)


async def get_current_client_id(
    payload: dict = Depends(get_token_payload),
) -> str:
    """
    FastAPI dependency: extract client_id from the verified token.
    """
    return await keycloak_auth.get_client_id(payload)


async def require_admin(
    payload: dict = Depends(get_token_payload),
) -> dict:
    """
    FastAPI dependency: require that the caller has the 'admin' realm role.

    Returns the full token payload so it can be used in the route handler.

    Usage::

        @router.delete("/tenants/{id}")
        async def delete_tenant(payload: dict = Depends(require_admin)):
            ...
    """
    await keycloak_auth.require_admin_role(payload)
    return payload
