"""
Ranking Service (DEPRECATED).

This module has been replaced by the dynamic scoring system in
MultiTenantRecommendationEngine._apply_dynamic_scoring().

Scoring is now driven by per-tenant ScoringConfig JSON criteria
rather than hardcoded weights.

Kept for backward compatibility reference only.
"""

import logging

logger = logging.getLogger(__name__)

logger.info(
    "ranking.py is deprecated. Use MultiTenantRecommendationEngine "
    "with ScoringConfig-based dynamic scoring instead."
)
