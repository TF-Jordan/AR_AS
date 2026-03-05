"""
Authentication routes: login (super admin + platform owner) and registration.
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.api.auth import (
    hash_password,
    verify_password,
    create_access_token,
)
from src.api.dependencies import get_db_session
from src.database.tenant_models import Platform, generate_platform_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# Schemas
# ============================================================

class AdminLoginRequest(BaseModel):
    key: str = Field(..., min_length=1)


class PlatformLoginRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class PlatformRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=2, max_length=100)
    domain: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9][a-z0-9_-]{1,98}$', v):
            raise ValueError(
                "Le slug doit être en minuscules avec chiffres, tirets ou underscores, "
                "commencer par une lettre ou un chiffre, entre 2 et 100 caractères"
            )
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email invalide")
        return v.lower().strip()


class AuthResponse(BaseModel):
    token: str
    role: str
    platform: Optional[dict] = None


# ============================================================
# Endpoints
# ============================================================

@router.post(
    "/login/admin",
    response_model=AuthResponse,
    summary="Super Admin login",
)
async def login_admin(request: AdminLoginRequest):
    """Authenticate as super admin using the environment key."""
    if request.key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé d'administration invalide.",
        )

    token = create_access_token({"sub": "admin", "role": "super_admin"})
    logger.info("Super admin authenticated")

    return AuthResponse(token=token, role="super_admin")


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Platform owner login",
)
async def login_platform(
    request: PlatformLoginRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Authenticate as platform owner using email and password."""
    result = await session.execute(
        select(Platform).where(Platform.email == request.email.lower().strip())
    )
    platform = result.scalar_one_or_none()

    if platform is None or not verify_password(request.password, platform.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
        )

    if not platform.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre plateforme est désactivée. Contactez l'administrateur.",
        )

    token = create_access_token({"sub": platform.slug, "role": "platform_owner"})
    logger.info(f"Platform owner authenticated: {platform.slug}")

    return AuthResponse(
        token=token,
        role="platform_owner",
        platform={
            "slug": platform.slug,
            "name": platform.name,
            "domain": platform.domain,
            "email": platform.email,
        },
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new platform",
)
async def register_platform(
    request: PlatformRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Register a new platform owner account (creates a new platform)."""
    # Check email uniqueness
    existing_email = await session.execute(
        select(Platform).where(Platform.email == request.email)
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe déjà avec cet email.",
        )

    # Check slug uniqueness
    existing_slug = await session.execute(
        select(Platform).where(Platform.slug == request.slug)
    )
    if existing_slug.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Le slug '{request.slug}' est déjà utilisé.",
        )

    # Create platform
    platform = Platform(
        name=request.name,
        slug=request.slug,
        domain=request.domain,
        email=request.email,
        password_hash=hash_password(request.password),
        api_key=generate_platform_api_key(),
    )
    session.add(platform)
    await session.flush()

    token = create_access_token({"sub": platform.slug, "role": "platform_owner"})
    logger.info(f"New platform registered: {platform.slug} ({platform.email})")

    return AuthResponse(
        token=token,
        role="platform_owner",
        platform={
            "slug": platform.slug,
            "name": platform.name,
            "domain": platform.domain,
            "email": platform.email,
        },
    )
