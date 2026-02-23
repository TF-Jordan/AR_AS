"""
Authentication dependencies for the RaaS API.
Handles API key validation and tenant resolution.
"""

import logging

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.tenant_models import Tenant
from src.api.dependencies import get_db_session

logger = logging.getLogger(__name__)

# API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_tenant(
    api_key: str = Security(api_key_header),
    session: AsyncSession = Depends(get_db_session),
) -> Tenant:
    """
    Dependency that validates the API key and returns the authenticated tenant.

    Raises:
        HTTPException 401 if no API key provided
        HTTPException 403 if API key is invalid or tenant is not active
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
    Dependency that validates the admin API key.
    Used to protect admin-only endpoints.

    Raises:
        HTTPException 401 if no API key provided
        HTTPException 403 if API key is not the admin key
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
