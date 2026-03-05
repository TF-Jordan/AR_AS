"""
Authentication dependencies for the RaaS API.
Handles API key validation, JWT tokens, and role-based access.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.tenant_models import Tenant, Platform
from src.api.dependencies import get_db_session

logger = logging.getLogger(__name__)

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


# ============================================================
# Password utilities
# ============================================================

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hash_bytes)


# ============================================================
# JWT utilities
# ============================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


# ============================================================
# Auth dependencies
# ============================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Decode JWT and return user info with role.
    Returns: {"role": "super_admin"|"platform_owner", "platform": Platform|None}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification requis.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = payload.get("role")
    sub = payload.get("sub")

    if role == "super_admin":
        return {"role": "super_admin", "platform": None}

    if role == "platform_owner":
        result = await session.execute(
            select(Platform).where(Platform.slug == sub)
        )
        platform = result.scalar_one_or_none()
        if platform is None or not platform.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Plateforme introuvable ou désactivée.",
            )
        return {"role": "platform_owner", "platform": platform}

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Rôle inconnu.",
    )


async def require_super_admin(
    user: dict = Depends(get_current_user),
) -> dict:
    """Require super admin role."""
    if user["role"] != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé au super administrateur.",
        )
    return user


async def require_platform_owner(
    user: dict = Depends(get_current_user),
) -> Platform:
    """Require platform owner role. Returns the Platform object."""
    if user["role"] != "platform_owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs de plateforme.",
        )
    return user["platform"]


# ============================================================
# Legacy: tenant API key auth (for programmatic access)
# ============================================================

async def get_current_tenant(
    api_key: str = Security(api_key_header),
    session: AsyncSession = Depends(get_db_session),
) -> Tenant:
    """
    Dependency that validates the API key and returns the authenticated tenant.
    Used for tenant-facing API endpoints (recommendations, items).
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
        )

    result = await session.execute(
        select(Tenant).where(Tenant.api_key == api_key)
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        logger.warning(f"Invalid API key attempt: {api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )

    if tenant.status != "active":
        logger.warning(f"Inactive tenant access attempt: {tenant.slug}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant is {tenant.status}. Contact administrator.",
        )

    return tenant


async def require_admin(
    api_key: str = Security(api_key_header),
) -> bool:
    """
    Legacy admin key validation.
    Used for backward compatibility with existing admin endpoints.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin API key required. Provide X-API-Key header.",
        )

    if api_key != settings.admin_api_key:
        logger.warning("Invalid admin API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key.",
        )

    return True
