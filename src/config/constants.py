"""
Application constants and enumerations.
"""

from enum import Enum

# Cache Settings
CACHE_TTL_SECONDS = 3600
SENTIMENT_SCORE_TOLERANCE = 0.1
DEFAULT_TOP_K = 10

# Tenant Settings
TENANT_SCHEMA_PREFIX = "tenant_"
TENANT_STATUSES = ("active", "suspended", "deleted")


class SentimentLabel(str, Enum):
    """Sentiment classification labels."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class CacheKeyPrefix(str, Enum):
    """Redis cache key prefixes."""
    RECOMMENDATION = "rec"
    SENTIMENT = "sent"
    PRODUCT = "prod"
    EMBEDDING = "emb"
    TENANT = "tenant"
