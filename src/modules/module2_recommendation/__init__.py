"""
Module 2: Multi-Tenant Recommendation Engine.

Provides semantic similarity-based recommendations with dynamic,
per-tenant scoring configured via ScoringConfig JSON criteria.

The engine accepts a database session at construction time so it can
resolve the active ScoringConfig for each tenant internally.
"""

from .engine import MultiTenantRecommendationEngine
from .cache import CacheManager, get_cache_manager
from .embeddings import EmbeddingService
from .vector_store import MultiTenantVectorStore, get_vector_store
from .schemas import ProductScore, MultiTenantRecommendationResult

__all__ = [
    "MultiTenantRecommendationEngine",
    "CacheManager",
    "EmbeddingService",
    "MultiTenantVectorStore",
    "ProductScore",
    "MultiTenantRecommendationResult",
    "get_cache_manager",
    "get_vector_store",
]
