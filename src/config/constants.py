"""
Application constants and enumerations.
"""

from enum import Enum

# Product Types (legacy, kept for backward compatibility with Comment model)
PRODUCT_TYPE_VEHICLE = "vehicle"

# Cache Settings
CACHE_TTL_SECONDS = 3600
SENTIMENT_SCORE_TOLERANCE = 0.1
DEFAULT_TOP_K = 10


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
