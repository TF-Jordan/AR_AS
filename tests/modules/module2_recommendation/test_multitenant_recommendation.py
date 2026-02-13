"""
Integration tests for the multi-tenant recommendation engine.

Tests the complete workflow:
1. Create tenant with scoring config
2. Upload products with custom metadata
3. Make recommendation request
4. Verify dynamic scoring is applied correctly

These tests mock external services (Qdrant, Redis, embedding model)
to run without infrastructure dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from types import SimpleNamespace

from src.modules.module2_recommendation.engine import MultiTenantRecommendationEngine
from src.modules.module2_recommendation.vector_store import MultiTenantVectorStore
from src.modules.module2_recommendation.schemas import (
    ProductScore,
    MultiTenantRecommendationResult,
)
from src.modules.module1_sentiment.schemas import SentimentResult
from src.services.product_service import ProductService
from src.services.scoring_service import ScoringConfigService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_scoring_config(criteria, version=1, tenant_id="test_tenant"):
    """Create a mock ScoringConfig object."""
    config = SimpleNamespace()
    config.tenant_id = tenant_id
    config.scoring_criteria = criteria
    config.version = version
    config.is_active = True
    return config


def _make_sentiment_result(
    label="positive", score=0.85, client_id="client_1", product_id="prod_1"
):
    """Create a SentimentResult for testing."""
    return SentimentResult(
        client_id=client_id,
        product_id=product_id,
        sentiment_score=score,
        sentiment_label=label,
        confidence=0.92,
    )


def _make_scored_point(product_id, score, payload_extras=None):
    """Create a mock Qdrant ScoredPoint."""
    payload = {
        "product_id": product_id,
        "description": f"Description for {product_id}",
    }
    if payload_extras:
        payload.update(payload_extras)

    point = SimpleNamespace()
    point.id = f"uuid-{product_id}"
    point.score = score
    point.payload = payload
    return point


def _make_engine(db=None, scoring_config=None):
    """Create engine with mocked dependencies and optional mock DB."""
    cache = MagicMock()
    cache.health_check = AsyncMock(return_value=True)
    embedding = MagicMock()
    embedding.health_check = MagicMock(return_value=True)
    embedding.encode_for_qdrant = MagicMock(return_value=[0.1] * 768)
    vector_store = MagicMock(spec=MultiTenantVectorStore)
    vector_store.health_check = MagicMock(return_value=True)

    # If a db mock is provided with a scoring config, wire up the mock
    mock_db = db
    if mock_db is None and scoring_config is not None:
        mock_db = AsyncMock()

    engine = MultiTenantRecommendationEngine(
        db=mock_db,
        cache_manager=cache,
        embedding_service=embedding,
        vector_store=vector_store,
    )

    return engine, vector_store, embedding


# ---------------------------------------------------------------------------
# Tests: MultiTenantVectorStore
# ---------------------------------------------------------------------------


class TestMultiTenantVectorStore:
    """Tests for MultiTenantVectorStore."""

    def test_collection_name_for_tenant(self):
        """Verify tenant collection naming convention."""
        assert MultiTenantVectorStore.collection_name_for_tenant("acme") == "tenant_acme"
        assert (
            MultiTenantVectorStore.collection_name_for_tenant("my-corp")
            == "tenant_my-corp"
        )

    def test_collection_name_format_always_prefixed(self):
        """Ensure collection names always use tenant_ prefix."""
        for tid in ["abc", "123", "real-estate-co", "tenant_already"]:
            name = MultiTenantVectorStore.collection_name_for_tenant(tid)
            assert name.startswith("tenant_")
            assert name == f"tenant_{tid}"


# ---------------------------------------------------------------------------
# Tests: Dynamic Scoring
# ---------------------------------------------------------------------------


class TestDynamicScoring:
    """Tests for the dynamic scoring engine."""

    def test_dynamic_scoring_system_criteria_only(self):
        """Test scoring with only system criteria (similarity + sentiment_boost)."""
        engine, _, _ = _make_engine()

        scoring_config = _make_scoring_config(
            criteria=[
                {"name": "similarity", "weight": 0.7, "type": "system"},
                {"name": "sentiment_boost", "weight": 0.3, "type": "system"},
            ]
        )

        search_results = [
            _make_scored_point("prod_A", 0.95),
            _make_scored_point("prod_B", 0.80),
        ]

        sentiment = _make_sentiment_result(label="positive", score=0.9)

        scored = engine._apply_dynamic_scoring(
            search_results, scoring_config, sentiment
        )

        assert len(scored) == 2
        assert scored[0].product_id == "prod_A"
        assert scored[1].product_id == "prod_B"

        # prod_A: 0.7 * 0.95 + 0.3 * 1.0 = 0.665 + 0.3 = 0.965
        assert abs(scored[0].total_score - 0.965) < 0.01

        # prod_B: 0.7 * 0.80 + 0.3 * 1.0 = 0.56 + 0.3 = 0.86
        assert abs(scored[1].total_score - 0.86) < 0.01

        # Ranks
        assert scored[0].rank == 1
        assert scored[1].rank == 2

        # Criterion breakdown present
        assert "similarity" in scored[0].criterion_scores
        assert "sentiment_boost" in scored[0].criterion_scores

    def test_dynamic_scoring_with_custom_criteria(self):
        """Test scoring with custom criteria from Qdrant payload."""
        engine, _, _ = _make_engine()

        scoring_config = _make_scoring_config(
            criteria=[
                {"name": "similarity", "weight": 0.5, "type": "system"},
                {"name": "price_match", "weight": 0.3, "type": "custom"},
                {"name": "location_proximity", "weight": 0.2, "type": "custom"},
            ]
        )

        search_results = [
            _make_scored_point(
                "prod_A",
                0.90,
                {"price_match": 0.8, "location_proximity": 0.5},
            ),
            _make_scored_point(
                "prod_B",
                0.85,
                {"price_match": 0.95, "location_proximity": 0.9},
            ),
        ]

        sentiment = _make_sentiment_result(label="neutral")

        scored = engine._apply_dynamic_scoring(
            search_results, scoring_config, sentiment
        )

        assert len(scored) == 2

        # prod_A: 0.5*0.90 + 0.3*0.8 + 0.2*0.5 = 0.45 + 0.24 + 0.10 = 0.79
        # prod_B: 0.5*0.85 + 0.3*0.95 + 0.2*0.9 = 0.425 + 0.285 + 0.18 = 0.89
        assert scored[0].product_id == "prod_B"  # Higher total
        assert scored[1].product_id == "prod_A"

        assert abs(scored[0].total_score - 0.89) < 0.01
        assert abs(scored[1].total_score - 0.79) < 0.01

    def test_dynamic_scoring_negative_sentiment(self):
        """Test that negative sentiment reduces sentiment_boost value."""
        engine, _, _ = _make_engine()

        scoring_config = _make_scoring_config(
            criteria=[
                {"name": "similarity", "weight": 0.6, "type": "system"},
                {"name": "sentiment_boost", "weight": 0.4, "type": "system"},
            ]
        )

        search_results = [_make_scored_point("prod_A", 0.90)]

        # Negative sentiment => sentiment_boost = 0.5
        sentiment = _make_sentiment_result(label="negative", score=-0.7)

        scored = engine._apply_dynamic_scoring(
            search_results, scoring_config, sentiment
        )

        # prod_A: 0.6*0.90 + 0.4*0.5 = 0.54 + 0.20 = 0.74
        assert abs(scored[0].total_score - 0.74) < 0.01

    def test_dynamic_scoring_missing_custom_field(self):
        """Test graceful handling of missing custom fields in payload."""
        engine, _, _ = _make_engine()

        scoring_config = _make_scoring_config(
            criteria=[
                {"name": "similarity", "weight": 0.7, "type": "system"},
                {"name": "rating", "weight": 0.3, "type": "custom"},
            ]
        )

        # Product payload does not contain "rating"
        search_results = [_make_scored_point("prod_A", 0.90)]

        sentiment = _make_sentiment_result()

        scored = engine._apply_dynamic_scoring(
            search_results, scoring_config, sentiment
        )

        # prod_A: 0.7*0.90 + 0.3*0.0 = 0.63
        assert abs(scored[0].total_score - 0.63) < 0.01

    def test_metadata_included_in_result(self):
        """Test that Qdrant payload metadata is included in the scored result."""
        engine, _, _ = _make_engine()

        scoring_config = _make_scoring_config(
            criteria=[
                {"name": "similarity", "weight": 1.0, "type": "system"},
            ]
        )

        search_results = [
            _make_scored_point(
                "prod_A",
                0.95,
                {"brand": "TestBrand", "category": "electronics"},
            )
        ]

        sentiment = _make_sentiment_result()

        scored = engine._apply_dynamic_scoring(
            search_results, scoring_config, sentiment
        )

        assert scored[0].metadata["brand"] == "TestBrand"
        assert scored[0].metadata["category"] == "electronics"
        assert scored[0].metadata["product_id"] == "prod_A"


# ---------------------------------------------------------------------------
# Tests: recommend() returns List[str]
# ---------------------------------------------------------------------------


class TestRecommendReturnsProductIds:
    """Tests that recommend() returns a plain list of product ID strings."""

    @pytest.mark.asyncio
    async def test_recommend_returns_list_of_strings(self):
        """recommend() should return List[str] of product_ids."""
        scoring_config = _make_scoring_config(
            criteria=[
                {"name": "similarity", "weight": 0.6, "type": "system"},
                {"name": "sentiment_boost", "weight": 0.1, "type": "system"},
                {"name": "price_match", "weight": 0.3, "type": "custom"},
            ]
        )

        engine, mock_vectors, mock_embeddings = _make_engine(
            scoring_config=scoring_config,
        )

        mock_vectors.search_similar = MagicMock(
            return_value=[
                _make_scored_point("prod_A", 0.95, {"price_match": 0.8}),
                _make_scored_point("prod_B", 0.88, {"price_match": 0.6}),
                _make_scored_point("prod_C", 0.75, {"price_match": 0.9}),
            ]
        )

        sentiment = _make_sentiment_result(
            label="positive", score=0.85, client_id="client_42", product_id="ref_prod"
        )

        # Mock _get_scoring_config to return our config
        with patch.object(engine, "_get_scoring_config", new_callable=AsyncMock) as mock_get_config:
            mock_get_config.return_value = scoring_config

            result = await engine.recommend(
                tenant_id="test_tenant",
                product_id="ref_prod",
                product_description="A great product for testing",
                sentiment_result=sentiment,
                top_k=5,
            )

        # Result should be a list of strings
        assert isinstance(result, list)
        assert all(isinstance(pid, str) for pid in result)
        assert len(result) == 3
        assert "prod_A" in result
        assert "prod_B" in result
        assert "prod_C" in result

    @pytest.mark.asyncio
    async def test_recommend_empty_returns_empty_list(self):
        """recommend() should return [] when no similar products found."""
        engine, mock_vectors, _ = _make_engine(scoring_config=_make_scoring_config([]))

        mock_vectors.search_similar = MagicMock(return_value=[])

        sentiment = _make_sentiment_result()

        result = await engine.recommend(
            tenant_id="test_tenant",
            product_id="prod_1",
            product_description="Test description",
            sentiment_result=sentiment,
        )

        assert result == []


# ---------------------------------------------------------------------------
# Tests: recommend_detailed() returns MultiTenantRecommendationResult
# ---------------------------------------------------------------------------


class TestRecommendDetailed:
    """Tests for the detailed recommendation method."""

    @pytest.mark.asyncio
    async def test_recommend_detailed_full_flow(self):
        """Test the complete recommendation workflow with mocked services."""
        scoring_config = _make_scoring_config(
            criteria=[
                {"name": "similarity", "weight": 0.6, "type": "system"},
                {"name": "sentiment_boost", "weight": 0.1, "type": "system"},
                {"name": "price_match", "weight": 0.3, "type": "custom"},
            ]
        )

        engine, mock_vectors, mock_embeddings = _make_engine(
            scoring_config=scoring_config,
        )

        mock_vectors.search_similar = MagicMock(
            return_value=[
                _make_scored_point("prod_A", 0.95, {"price_match": 0.8}),
                _make_scored_point("prod_B", 0.88, {"price_match": 0.6}),
                _make_scored_point("prod_C", 0.75, {"price_match": 0.9}),
            ]
        )

        sentiment = _make_sentiment_result(
            label="positive", score=0.85, client_id="client_42", product_id="ref_prod"
        )

        with patch.object(engine, "_get_scoring_config", new_callable=AsyncMock) as mock_get_config:
            mock_get_config.return_value = scoring_config

            result = await engine.recommend_detailed(
                tenant_id="test_tenant",
                product_id="ref_prod",
                product_description="A great product for testing",
                sentiment_result=sentiment,
                top_k=5,
            )

        # Assertions
        assert isinstance(result, MultiTenantRecommendationResult)
        assert result.tenant_id == "test_tenant"
        assert result.client_id == "client_42"
        assert result.reference_product_id == "ref_prod"
        assert result.sentiment_label == "positive"
        assert result.total_results == 3
        assert result.scoring_config_version == 1
        assert result.cached is False

        # All products should be ranked
        assert len(result.recommendations) == 3
        assert result.recommendations[0].rank == 1
        assert result.recommendations[1].rank == 2
        assert result.recommendations[2].rank == 3

        # Verify embedding was generated from description
        mock_embeddings.encode_for_qdrant.assert_called_once_with(
            "A great product for testing"
        )

        # Verify search was called on correct tenant
        mock_vectors.search_similar.assert_called_once()
        call_kwargs = mock_vectors.search_similar.call_args
        assert call_kwargs.kwargs.get("tenant_id") == "test_tenant" or call_kwargs[1].get("tenant_id") == "test_tenant"

    @pytest.mark.asyncio
    async def test_recommend_detailed_empty_results(self):
        """Test recommendation with no similar products found."""
        scoring_config = _make_scoring_config(
            criteria=[
                {"name": "similarity", "weight": 1.0, "type": "system"},
            ]
        )

        engine, mock_vectors, _ = _make_engine(scoring_config=scoring_config)

        mock_vectors.search_similar = MagicMock(return_value=[])

        sentiment = _make_sentiment_result()

        with patch.object(engine, "_get_scoring_config", new_callable=AsyncMock) as mock_get_config:
            mock_get_config.return_value = scoring_config

            result = await engine.recommend_detailed(
                tenant_id="test_tenant",
                product_id="prod_1",
                product_description="Test description",
                sentiment_result=sentiment,
            )

        assert result.total_results == 0
        assert result.recommendations == []

    @pytest.mark.asyncio
    async def test_recommend_detailed_filters_self(self):
        """Test that the reference product is excluded from results."""
        scoring_config = _make_scoring_config(
            criteria=[
                {"name": "similarity", "weight": 1.0, "type": "system"},
            ]
        )

        engine, mock_vectors, _ = _make_engine(scoring_config=scoring_config)

        # Include the reference product in search results
        mock_vectors.search_similar = MagicMock(
            return_value=[
                _make_scored_point("ref_prod", 1.0),  # Self
                _make_scored_point("other_prod", 0.85),
            ]
        )

        sentiment = _make_sentiment_result(product_id="ref_prod")

        with patch.object(engine, "_get_scoring_config", new_callable=AsyncMock) as mock_get_config:
            mock_get_config.return_value = scoring_config

            result = await engine.recommend_detailed(
                tenant_id="test_tenant",
                product_id="ref_prod",
                product_description="Test",
                sentiment_result=sentiment,
            )

        # Only other_prod should appear
        assert result.total_results == 1
        assert result.recommendations[0].product_id == "other_prod"


# ---------------------------------------------------------------------------
# Tests: Engine requires DB for ScoringConfig
# ---------------------------------------------------------------------------


class TestEngineRequiresDB:
    """Test that the engine correctly requires a DB session."""

    @pytest.mark.asyncio
    async def test_recommend_without_db_raises(self):
        """recommend() should raise ValueError if no db session provided."""
        engine, mock_vectors, _ = _make_engine()
        # Explicitly set db to None
        engine.db = None

        mock_vectors.search_similar = MagicMock(
            return_value=[_make_scored_point("prod_A", 0.95)]
        )

        sentiment = _make_sentiment_result()

        with pytest.raises(ValueError, match="requires a database session"):
            await engine.recommend(
                tenant_id="test_tenant",
                product_id="other_prod",
                product_description="Test",
                sentiment_result=sentiment,
            )


# ---------------------------------------------------------------------------
# Tests: ProductService
# ---------------------------------------------------------------------------


class TestProductService:
    """Tests for the ProductService."""

    @pytest.mark.asyncio
    async def test_upload_products_validation(self):
        """Test product validation during upload."""
        mock_vectors = MagicMock(spec=MultiTenantVectorStore)
        mock_vectors.ensure_collection_exists = MagicMock(return_value=True)
        mock_vectors.add_products = MagicMock(return_value=1)

        mock_embeddings = MagicMock()
        mock_embeddings.encode_batch_for_qdrant = MagicMock(
            return_value=[[0.1] * 768]
        )

        service = ProductService(
            vector_store=mock_vectors,
            embedding_service=mock_embeddings,
        )

        # One valid product, one missing product_id, one missing description
        products = [
            {"product_id": "p1", "description": "Valid product"},
            {"description": "Missing ID"},  # No product_id
            {"product_id": "p3"},  # No description
        ]

        result = await service.upload_products("test_tenant", products)

        assert result["uploaded"] == 1
        assert result["errors"] == 2

    @pytest.mark.asyncio
    async def test_upload_products_empty_list(self):
        """Test uploading an empty product list."""
        service = ProductService(
            vector_store=MagicMock(),
            embedding_service=MagicMock(),
        )

        result = await service.upload_products("test_tenant", [])

        assert result["uploaded"] == 0
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_upload_products_with_metadata(self):
        """Test that metadata is passed through to vector store."""
        mock_vectors = MagicMock(spec=MultiTenantVectorStore)
        mock_vectors.ensure_collection_exists = MagicMock(return_value=True)
        mock_vectors.add_products = MagicMock(return_value=2)

        mock_embeddings = MagicMock()
        mock_embeddings.encode_batch_for_qdrant = MagicMock(
            return_value=[[0.1] * 768, [0.2] * 768]
        )

        service = ProductService(
            vector_store=mock_vectors,
            embedding_service=mock_embeddings,
        )

        products = [
            {
                "product_id": "p1",
                "description": "Product 1",
                "metadata": {"price_score": 0.8, "location_match": 0.9},
            },
            {
                "product_id": "p2",
                "description": "Product 2",
                "metadata": {"price_score": 0.5},
            },
        ]

        result = await service.upload_products("test_tenant", products)

        assert result["uploaded"] == 2
        assert result["errors"] == 0

        # Verify add_products was called with vectors and metadata
        mock_vectors.add_products.assert_called_once()
        call_args = mock_vectors.add_products.call_args
        products_with_vectors = call_args[0][1]  # second positional arg
        assert len(products_with_vectors) == 2
        assert products_with_vectors[0]["metadata"] == {"price_score": 0.8, "location_match": 0.9}


# ---------------------------------------------------------------------------
# Tests: ScoringConfig Validation
# ---------------------------------------------------------------------------


class TestScoringConfigValidation:
    """Tests for scoring criteria validation."""

    def test_validate_criteria_valid(self):
        """Test valid criteria pass validation."""
        criteria = [
            {"name": "similarity", "weight": 0.7, "type": "system"},
            {"name": "price", "weight": 0.3, "type": "custom"},
        ]
        assert ScoringConfigService.validate_criteria(criteria) is True

    def test_validate_criteria_weights_not_one(self):
        """Test that weights not summing to 1.0 raises ValueError."""
        criteria = [
            {"name": "similarity", "weight": 0.5, "type": "system"},
            {"name": "price", "weight": 0.3, "type": "custom"},
        ]
        with pytest.raises(ValueError, match="must sum to 1.0"):
            ScoringConfigService.validate_criteria(criteria)

    def test_validate_criteria_invalid_type(self):
        """Test that invalid criterion type raises ValueError."""
        criteria = [
            {"name": "similarity", "weight": 1.0, "type": "invalid"},
        ]
        with pytest.raises(ValueError, match="invalid type"):
            ScoringConfigService.validate_criteria(criteria)

    def test_validate_criteria_missing_field(self):
        """Test that missing required field raises ValueError."""
        criteria = [
            {"name": "similarity", "weight": 1.0},  # Missing "type"
        ]
        with pytest.raises(ValueError, match="missing required field"):
            ScoringConfigService.validate_criteria(criteria)

    def test_validate_criteria_empty(self):
        """Test that empty criteria list raises ValueError."""
        with pytest.raises(ValueError, match="At least one"):
            ScoringConfigService.validate_criteria([])


# ---------------------------------------------------------------------------
# Integration Test: Full Multi-Tenant Workflow
# ---------------------------------------------------------------------------


class TestMultiTenantIntegrationWorkflow:
    """
    Integration test that exercises the complete multi-tenant recommendation
    workflow end-to-end with mocked infrastructure:

    1. Create tenant (simulated)
    2. Upload products with metadata
    3. Create scoring config with custom criteria
    4. Call recommend()
    5. Verify dynamic scoring applied
    """

    @pytest.mark.asyncio
    async def test_full_multitenant_workflow(self):
        """End-to-end multi-tenant recommendation workflow."""

        # ---- Step 1: Simulate tenant setup ----
        tenant_id = "acme_realestate"
        collection_name = f"tenant_{tenant_id}"

        # ---- Step 2: Upload products with metadata ----
        mock_vectors = MagicMock(spec=MultiTenantVectorStore)
        mock_vectors.ensure_collection_exists = MagicMock(return_value=True)
        mock_vectors.add_products = MagicMock(return_value=4)
        mock_vectors.health_check = MagicMock(return_value=True)

        mock_embeddings = MagicMock()
        mock_embeddings.health_check = MagicMock(return_value=True)
        mock_embeddings.encode_batch_for_qdrant = MagicMock(
            return_value=[
                [0.1] * 768,
                [0.2] * 768,
                [0.3] * 768,
                [0.4] * 768,
            ]
        )
        mock_embeddings.encode_for_qdrant = MagicMock(return_value=[0.15] * 768)

        product_service = ProductService(
            vector_store=mock_vectors,
            embedding_service=mock_embeddings,
        )

        products = [
            {
                "product_id": "apt_001",
                "description": "Appartement 3 pieces centre-ville lumineux",
                "metadata": {"price_score": 0.85, "location_match": 0.95},
            },
            {
                "product_id": "apt_002",
                "description": "Studio moderne proche metro",
                "metadata": {"price_score": 0.70, "location_match": 0.80},
            },
            {
                "product_id": "apt_003",
                "description": "Grand loft avec terrasse",
                "metadata": {"price_score": 0.60, "location_match": 0.40},
            },
            {
                "product_id": "house_001",
                "description": "Maison avec jardin en banlieue",
                "metadata": {"price_score": 0.90, "location_match": 0.30},
            },
        ]

        upload_result = await product_service.upload_products(tenant_id, products)
        assert upload_result["uploaded"] == 4
        assert upload_result["errors"] == 0

        # ---- Step 3: Create scoring config with custom criteria ----
        scoring_config = _make_scoring_config(
            criteria=[
                {"name": "similarity", "weight": 0.50, "type": "system"},
                {"name": "sentiment_boost", "weight": 0.10, "type": "system"},
                {"name": "price_score", "weight": 0.25, "type": "custom"},
                {"name": "location_match", "weight": 0.15, "type": "custom"},
            ],
            version=1,
            tenant_id=tenant_id,
        )

        # Validate weights sum to 1.0
        total_weight = sum(c["weight"] for c in scoring_config.scoring_criteria)
        assert abs(total_weight - 1.0) < 0.01

        # ---- Step 4: Call recommend() ----

        # Simulate Qdrant search results (products with payload metadata)
        mock_vectors.search_similar = MagicMock(
            return_value=[
                _make_scored_point(
                    "apt_001", 0.92,
                    {"price_score": 0.85, "location_match": 0.95},
                ),
                _make_scored_point(
                    "apt_002", 0.88,
                    {"price_score": 0.70, "location_match": 0.80},
                ),
                _make_scored_point(
                    "apt_003", 0.75,
                    {"price_score": 0.60, "location_match": 0.40},
                ),
                _make_scored_point(
                    "house_001", 0.65,
                    {"price_score": 0.90, "location_match": 0.30},
                ),
            ]
        )

        mock_cache = MagicMock()
        mock_cache.health_check = AsyncMock(return_value=True)

        engine = MultiTenantRecommendationEngine(
            db=AsyncMock(),  # Mocked db session
            cache_manager=mock_cache,
            embedding_service=mock_embeddings,
            vector_store=mock_vectors,
        )

        sentiment = _make_sentiment_result(
            label="positive",
            score=0.85,
            client_id="client_100",
            product_id="query_product",
        )

        with patch.object(engine, "_get_scoring_config", new_callable=AsyncMock) as mock_get_config:
            mock_get_config.return_value = scoring_config

            # Test recommend() -> List[str]
            product_ids = await engine.recommend(
                tenant_id=tenant_id,
                product_id="query_product",
                product_description="Cherche appartement lumineux centre-ville",
                sentiment_result=sentiment,
                top_k=10,
            )

        # ---- Step 5: Verify dynamic scoring applied ----

        assert isinstance(product_ids, list)
        assert all(isinstance(pid, str) for pid in product_ids)
        assert len(product_ids) == 4

        # Verify collection convention
        assert collection_name == "tenant_acme_realestate"

        # Verify search was called on correct tenant
        mock_vectors.search_similar.assert_called_once()
        call_kwargs = mock_vectors.search_similar.call_args
        assert call_kwargs.kwargs.get("tenant_id") == tenant_id

        # Verify embedding was generated
        mock_embeddings.encode_for_qdrant.assert_called_with(
            "Cherche appartement lumineux centre-ville"
        )

        # Verify scoring order (manually compute expected scores):
        # apt_001: 0.50*0.92 + 0.10*1.0 + 0.25*0.85 + 0.15*0.95
        #        = 0.46 + 0.10 + 0.2125 + 0.1425 = 0.915
        # apt_002: 0.50*0.88 + 0.10*1.0 + 0.25*0.70 + 0.15*0.80
        #        = 0.44 + 0.10 + 0.175 + 0.12 = 0.835
        # apt_003: 0.50*0.75 + 0.10*1.0 + 0.25*0.60 + 0.15*0.40
        #        = 0.375 + 0.10 + 0.15 + 0.06 = 0.685
        # house_001: 0.50*0.65 + 0.10*1.0 + 0.25*0.90 + 0.15*0.30
        #          = 0.325 + 0.10 + 0.225 + 0.045 = 0.695

        # Expected order: apt_001, apt_002, house_001, apt_003
        assert product_ids[0] == "apt_001"
        assert product_ids[1] == "apt_002"
        assert product_ids[2] == "house_001"
        assert product_ids[3] == "apt_003"

    @pytest.mark.asyncio
    async def test_full_workflow_detailed_response(self):
        """End-to-end workflow returning detailed score breakdowns."""

        tenant_id = "acme_realestate"

        scoring_config = _make_scoring_config(
            criteria=[
                {"name": "similarity", "weight": 0.70, "type": "system"},
                {"name": "sentiment_boost", "weight": 0.10, "type": "system"},
                {"name": "price_score", "weight": 0.15, "type": "custom"},
                {"name": "location_match", "weight": 0.05, "type": "custom"},
            ],
            version=2,
            tenant_id=tenant_id,
        )

        mock_vectors = MagicMock(spec=MultiTenantVectorStore)
        mock_vectors.health_check = MagicMock(return_value=True)
        mock_vectors.search_similar = MagicMock(
            return_value=[
                _make_scored_point(
                    "prod_X", 0.90,
                    {"price_score": 0.8, "location_match": 0.9},
                ),
                _make_scored_point(
                    "prod_Y", 0.85,
                    {"price_score": 0.5, "location_match": 0.7},
                ),
            ]
        )

        mock_embeddings = MagicMock()
        mock_embeddings.health_check = MagicMock(return_value=True)
        mock_embeddings.encode_for_qdrant = MagicMock(return_value=[0.1] * 768)

        mock_cache = MagicMock()
        mock_cache.health_check = AsyncMock(return_value=True)

        engine = MultiTenantRecommendationEngine(
            db=AsyncMock(),
            cache_manager=mock_cache,
            embedding_service=mock_embeddings,
            vector_store=mock_vectors,
        )

        sentiment = _make_sentiment_result(
            label="positive",
            score=0.9,
            client_id="client_200",
            product_id="query_prod",
        )

        with patch.object(engine, "_get_scoring_config", new_callable=AsyncMock) as mock_get_config:
            mock_get_config.return_value = scoring_config

            result = await engine.recommend_detailed(
                tenant_id=tenant_id,
                product_id="query_prod",
                product_description="Looking for great products",
                sentiment_result=sentiment,
                top_k=10,
            )

        assert isinstance(result, MultiTenantRecommendationResult)
        assert result.tenant_id == tenant_id
        assert result.scoring_config_version == 2
        assert result.total_results == 2

        # Verify per-criterion breakdowns exist
        top_rec = result.recommendations[0]
        assert "similarity" in top_rec.criterion_scores
        assert "sentiment_boost" in top_rec.criterion_scores
        assert "price_score" in top_rec.criterion_scores
        assert "location_match" in top_rec.criterion_scores

        # Verify criterion structure
        sim_score = top_rec.criterion_scores["similarity"]
        assert "value" in sim_score
        assert "weight" in sim_score
        assert "contribution" in sim_score
