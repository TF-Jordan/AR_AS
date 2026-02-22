"""
Administration API endpoints.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/status",
    summary="System status",
    description="Get overall system status.",
)
async def system_status():
    """Get system status overview."""
    from src.modules.module3_orchestration import get_orchestrator

    try:
        orchestrator = get_orchestrator()
        health = await orchestrator.health_check()
        return {
            "status": "operational",
            "services": health.get("services", {}),
        }

    except Exception as e:
        logger.error(f"Status check error: {e}")
        return {
            "status": "degraded",
            "error": str(e),
        }
