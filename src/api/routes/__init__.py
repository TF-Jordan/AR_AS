from fastapi import APIRouter

from .recommendations import router as recommendations_router
from .sentiment import router as sentiment_router
from .health import router as health_router
from .admin import router as admin_router
from .livreur_ranking import router as livreur_ranking_router
from .products import router as products_router
from .tenants import router as tenants_router
from .scoring import router as scoring_router

api_router = APIRouter()

# --- Public routes ---
api_router.include_router(
    health_router,
    prefix="/health",
    tags=["Health"],
)

# --- Protected routes (require auth) ---
api_router.include_router(
    recommendations_router,
    prefix="/recommendations",
    tags=["Recommendations"],
)

api_router.include_router(
    sentiment_router,
    prefix="/sentiment",
    tags=["Sentiment Analysis"],
)

api_router.include_router(
    products_router,
    prefix="/products",
    tags=["Products"],
)

api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["Administration"],
)

api_router.include_router(
    livreur_ranking_router,
    prefix="/livreur-ranking",
    tags=["Livreur Ranking (Module 4)"],
)

# --- Admin routes (require admin role) ---
api_router.include_router(tenants_router)
api_router.include_router(scoring_router)
