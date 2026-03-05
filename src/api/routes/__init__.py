from fastapi import APIRouter

from .tenant import router as tenant_router
from .sentiment import router as sentiment_router
from .health import router as health_router
from .admin import router as admin_router
from .auth_routes import router as auth_router
from .platform import router as platform_router
from .super_admin import router as super_admin_router

api_router = APIRouter()

api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

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
    tags=["Administration (Legacy)"],
)

api_router.include_router(
    platform_router,
    prefix="/platform",
    tags=["Platform Owner"],
)

api_router.include_router(
    super_admin_router,
    prefix="/super-admin",
    tags=["Super Admin"],
)
