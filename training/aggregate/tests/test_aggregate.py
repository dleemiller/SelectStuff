import pytest
from typing import List, Literal, Optional
from pydantic import BaseModel
from unittest.mock import Mock, patch
from aggregate.aggregate import LLMOutputAggregator


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
        result = LLMOutputAggregator.aggregate(SimpleModel, simple_predictions)

        assert isinstance(result, SimpleModel)
        assert result.name == "Test"  # Most common name
        assert result.count == 1  # Most common count
        assert set(result.tags) >= {"a", "b"}  # Most common tags

    def test_complex_aggregation(self, complex_predictions):
        result = LLMOutputAggregator.aggregate(ComplexModel, complex_predictions)

        assert isinstance(result, ComplexModel)
        assert result.title == "First Post"
        assert result.category == "news"
        assert len(result.tags) > 0

    def test_empty_predictions(self):
        with pytest.raises(ValueError, match="No predictions to aggregate"):
            LLMOutputAggregator.aggregate(SimpleModel, [])

    def test_optional_fields(self, complex_predictions):
        result = LLMOutputAggregator.aggregate(ComplexModel, complex_predictions)

        # Optional author field should be handled properly
        assert result.author is not None  # Should pick most common non-None value

    @patch("wordllama.WordLlama")
    def test_semantic_clustering(self, mock_wordllama, complex_predictions):
        # Set up mock for semantic clustering
        wl = Mock()
        wl.embed.return_value = Mock()
        wl.vector_similarity.return_value = Mock()
        mock_wordllama.load.return_value = wl

        # Force semantic clustering by setting a low threshold
        result = LLMOutputAggregator.aggregate(
            ComplexModel, complex_predictions, threshold=1
        )
        assert isinstance(result, ComplexModel)

    def test_majority_voting(self):
        values = ["a", "b", "a", "c", "a", "b"]
        result = LLMOutputAggregator.majority_vote(values, debug=True)
        assert result == "a"

    def test_debug_output(self, simple_predictions, caplog):
        """Test that debug output is properly logged."""
        import logging

        caplog.set_level(logging.INFO)

        # Perform an operation that should generate debug output
        result = LLMOutputAggregator.majority_vote(["a", "b", "a", "c"], debug=True)

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

        result = LLMOutputAggregator.aggregate(self.ModelWithLiteral, predictions)
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

        result = LLMOutputAggregator.aggregate(ComplexModel, predictions)
        assert result.author is None

    def test_required_field_aggregation(self):
        """Test handling of required fields with None values during aggregation."""
        from pydantic import BaseModel

        class RequiredFieldModel(BaseModel):
            required_field: str

        predictions = [
            {"required_field": "test1"},
            {"required_field": "test2"},
            {"required_field": None},
        ]

        result = LLMOutputAggregator.aggregate(RequiredFieldModel, predictions)
        assert result.required_field in ["test1", "test2"]

        all_none_predictions = [{"required_field": None}, {"required_field": None}]
        with pytest.raises(ValueError, match="No values found for required field"):
            LLMOutputAggregator.aggregate(RequiredFieldModel, all_none_predictions)
