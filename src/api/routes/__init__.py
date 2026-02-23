from fastapi import APIRouter

from .tenant import router as tenant_router
from .sentiment import router as sentiment_router
from .health import router as health_router
from .admin import router as admin_router

api_router = APIRouter()

api_router.include_router(
    tenant_router,
    prefix="/tenant",
    tags=["Tenant API"],
)

api_router.include_router(
    sentiment_router,
    prefix="/sentiment",
    tags=["Sentiment Analysis"],
)

api_router.include_router(
    health_router,
    prefix="/health",
    tags=["Health"],
)

api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["Administration"],
)
