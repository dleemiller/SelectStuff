import pytest
import numpy as np
from unittest.mock import Mock, patch

from aggregate.cluster import (
    ClusteringConfig,
    JaccardClustering,
    SemanticClustering,
    get_clustering_strategy,
)


@pytest.fixture
def config():
    return ClusteringConfig(
        jaccard_threshold=0.5,
        semantic_threshold=0.7,
        min_length_for_semantic=50,
        embedding_dim=64,
    )


class TestJaccardClustering:
    def test_exact_matches(self, config):
        strings = ["apple", "apple", "banana", "banana", "cherry"]
        strategy = JaccardClustering()
        result = strategy.cluster_strings(strings, threshold=2, config=config)
        assert set(result) == {"apple", "banana"}

    def test_similar_matches(self, config):
        strings = [
            "quick brown fox",
            "quick brown dog",
            "lazy brown fox",
            "completely different",
        ]
        strategy = JaccardClustering()
        result = strategy.cluster_strings(strings, threshold=2, config=config)
        assert len(result) == 1
        assert "quick" in result[0]  # Should cluster similar phrases

    def test_threshold_filtering(self, config):
        strings = ["apple", "apple", "banana", "cherry", "cherry"]
        strategy = JaccardClustering()
        # Threshold of 3 means only clusters with 3+ items should remain
        result = strategy.cluster_strings(strings, threshold=3, config=config)
        assert len(result) == 0  # No clusters meet the threshold

    def test_empty_input(self, config):
        strategy = JaccardClustering()
        result = strategy.cluster_strings([], threshold=2, config=config)
        assert result == []


class TestSemanticClustering:
    @pytest.fixture
    def mock_wordllama(self):
        with patch("wordllama.WordLlama") as mock:
            wl = Mock()
            # Mock the embedding method
            wl.embed.return_value = np.random.rand(3, 64)
            # Mock the vector_similarity method
            wl.vector_similarity.return_value = np.array(
                [[1.0, 0.8, 0.3], [0.8, 1.0, 0.2], [0.3, 0.2, 1.0]]
            )
            mock.load.return_value = wl
            yield mock

    def test_semantic_clustering(self, config, mock_wordllama):
        strings = [
            "The quick brown fox jumps",
            "A brown fox quickly leaps",
            "Something completely different",
        ]
        strategy = SemanticClustering()
        result = strategy.cluster_strings(strings, threshold=2, config=config)
        assert len(result) == 1  # Should cluster similar sentences

    def test_find_representative(self, config, mock_wordllama):
        strings = [
            "The quick brown fox jumps",
            "A brown fox quickly leaps",
            "The speedy fox leaps around",
        ]
        strategy = SemanticClustering()
        representative = strategy._find_representative(strings)
        assert representative in strings

    def test_empty_input(self, config, mock_wordllama):
        strategy = SemanticClustering()
        result = strategy.cluster_strings([], threshold=2, config=config)
        assert result == []

    def test_single_string(self, config, mock_wordllama):
        strategy = SemanticClustering()
        result = strategy.cluster_strings(["standalone"], threshold=1, config=config)
        assert result == ["standalone"]


class TestStrategySelection:
    def test_short_strings_get_jaccard(self, config):
        strings = ["cat", "dog", "rat"]
        strategy = get_clustering_strategy(strings, config)
        assert isinstance(strategy, JaccardClustering)

    def test_long_strings_get_semantic(self, config):
        strings = [
            "This is a much longer string that should trigger semantic clustering"
        ]
        strategy = get_clustering_strategy(strings, config)
        assert isinstance(strategy, SemanticClustering)

    def test_mixed_length_prefers_semantic(self, config):
        strings = ["short", "This is a much longer string that should trigger semantic"]
        strategy = get_clustering_strategy(strings, config)
        assert isinstance(strategy, SemanticClustering)
