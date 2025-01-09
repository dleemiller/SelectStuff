import pytest
from typing import List, Literal, Optional
from pydantic import BaseModel
from unittest.mock import Mock, patch

from aggregate.aggregate import LLMOutputAggregator, FieldType
from aggregate.cluster import ClusteringConfig


# Test models
class SimpleModel(BaseModel):
    name: str
    count: int
    tags: List[str]


class ComplexModel(BaseModel):
    title: str
    description: str
    category: Literal["news", "blog", "article"]
    tags: List[str]
    author: Optional[str] = None


@pytest.fixture
def simple_predictions():
    return [
        SimpleModel(name="Test", count=1, tags=["a", "b"]),
        SimpleModel(name="Test", count=2, tags=["b", "c"]),
        SimpleModel(name="Other", count=1, tags=["a", "d"]),
    ]


@pytest.fixture
def complex_predictions():
    return [
        ComplexModel(
            title="First Post",
            description="A test post",
            category="news",
            tags=["tech", "ai"],
            author="Alice",
        ),
        ComplexModel(
            title="First Post",
            description="A test posting",
            category="news",
            tags=["technology", "artificial intelligence"],
            author="Bob",
        ),
        ComplexModel(
            title="Another Post",
            description="Different post",
            category="blog",
            tags=["tech", "ml"],
            author=None,
        ),
    ]


class TestLLMOutputAggregator:
    def test_simple_aggregation(self, simple_predictions):
        aggregator = LLMOutputAggregator(SimpleModel)
        result = aggregator.aggregate(SimpleModel, simple_predictions)

        assert isinstance(result, SimpleModel)
        assert result.name == "Test"  # Most common name
        assert result.count == 1  # Most common count
        assert set(result.tags) >= {"a", "b"}  # Most common tags

    def test_complex_aggregation(self, complex_predictions):
        aggregator = LLMOutputAggregator(ComplexModel)
        result = aggregator.aggregate(ComplexModel, complex_predictions)

        assert isinstance(result, ComplexModel)
        assert result.title == "First Post"
        assert result.category == "news"
        assert len(result.tags) > 0

    def test_empty_predictions(self):
        aggregator = LLMOutputAggregator(SimpleModel)
        with pytest.raises(ValueError, match="No predictions to aggregate"):
            aggregator.aggregate(SimpleModel, [])

    def test_field_type_detection(self):
        aggregator = LLMOutputAggregator(SimpleModel)

        # Test various field types
        assert aggregator._get_field_type(str, "test") == FieldType.STRING
        assert (
            aggregator._get_field_type(List[str], ["a", "b"]) == FieldType.STRING_LIST
        )
        assert aggregator._get_field_type(int, 42) == FieldType.OTHER

    def test_optional_fields(self, complex_predictions):
        aggregator = LLMOutputAggregator(ComplexModel)
        result = aggregator.aggregate(ComplexModel, complex_predictions)

        # Optional author field should be handled properly
        assert result.author is not None  # Should pick most common non-None value

    @patch("wordllama.WordLlama")
    def test_semantic_clustering(self, mock_wordllama, complex_predictions):
        # Set up mock for semantic clustering
        wl = Mock()
        wl.embed.return_value = Mock()
        wl.vector_similarity.return_value = Mock()
        mock_wordllama.load.return_value = wl

        aggregator = LLMOutputAggregator(ComplexModel)
        # Force semantic clustering by setting a low threshold
        aggregator.config.min_length_for_semantic = 10

        result = aggregator.aggregate(ComplexModel, complex_predictions)
        assert isinstance(result, ComplexModel)

    def test_majority_voting(self):
        aggregator = LLMOutputAggregator(SimpleModel)
        values = ["a", "b", "a", "c", "a", "b"]
        result = aggregator._majority_vote(values)
        assert result == "a"

    def test_debug_output(self, simple_predictions, caplog):
        """Test that debug output is properly logged"""
        import logging

        caplog.set_level(logging.INFO)

        # Perform the operation that should generate debug output
        aggregator = LLMOutputAggregator(SimpleModel, debug=True)
        result = aggregator._majority_vote(["a", "b", "a", "c"])

        # Print captured logs for debugging
        print(f"Captured logs: {caplog.text}")

        # More lenient check - look for key components in any case
        log_text = caplog.text.lower()
        assert (
            "counter" in log_text and "vote" in log_text
        ), f"Expected 'counter' and 'vote' in log output, got: {log_text}"

        # Verify the actual counter content is present
        assert "'a': 2" in caplog.text, "Expected count for 'a' not found in logs"


class TestEdgeCases:
    class ModelWithLiteral(BaseModel):
        status: Literal["active", "inactive", "pending"]

    def test_literal_field_aggregation(self):
        predictions = [
            self.ModelWithLiteral(status="active"),
            self.ModelWithLiteral(status="active"),
            self.ModelWithLiteral(status="pending"),
        ]

        aggregator = LLMOutputAggregator(self.ModelWithLiteral)
        result = aggregator.aggregate(self.ModelWithLiteral, predictions)
        assert result.status == "active"

    def test_all_none_optional_field(self):
        predictions = [
            ComplexModel(
                title="Test",
                description="Test",
                category="news",
                tags=["test"],
                author=None,
            ),
            ComplexModel(
                title="Test",
                description="Test",
                category="news",
                tags=["test"],
                author=None,
            ),
        ]

        aggregator = LLMOutputAggregator(ComplexModel)
        result = aggregator.aggregate(ComplexModel, predictions)
        assert result.author is None

    def test_required_field_aggregation(self):
        """Test handling of required fields with None values during aggregation"""
        from pydantic import BaseModel

        class RequiredFieldModel(BaseModel):
            required_field: str

        # Create predictions where some fields will be None after extraction
        predictions = [
            Mock(required_field="test1"),
            Mock(required_field="test2"),
            Mock(
                required_field=None
            ),  # This one has None but won't cause Pydantic validation
        ]

        aggregator = LLMOutputAggregator(RequiredFieldModel)

        # Should work because we have some non-None values
        result = aggregator.aggregate(RequiredFieldModel, predictions)
        assert result.required_field in ["test1", "test2"]

        # Now test with all None values
        all_none_predictions = [Mock(required_field=None), Mock(required_field=None)]

        with pytest.raises(ValueError, match="No values found for required field"):
            aggregator.aggregate(RequiredFieldModel, all_none_predictions)
