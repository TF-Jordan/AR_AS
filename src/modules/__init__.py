# Modules package
from .module1_sentiment import SentimentAnalyzer, SentimentResult
from .module2_recommendation import RecommendationEngine

__all__ = [
    "SentimentAnalyzer",
    "SentimentResult",
    "RecommendationEngine",
]
