from typing import List, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np
import textdistance
from wordllama import WordLlama


@dataclass
class ClusteringConfig:
    """Configuration for clustering parameters"""

    jaccard_threshold: float = 0.6  # For short string exact matching
    semantic_threshold: float = 0.7  # For semantic deduplication
    min_length_for_semantic: int = 50  # Use semantic for strings longer than this
    embedding_dim: int = 256


class ClusteringStrategy(ABC):
    """Abstract base class for clustering strategies"""

    @abstractmethod
    def cluster_strings(
        self, strings: List[str], threshold: int, config: ClusteringConfig
    ) -> List[str]:
        pass


class JaccardClustering(ClusteringStrategy):
    """Simple Jaccard similarity-based clustering for short strings"""

    def cluster_strings(
        self, strings: List[str], threshold: int, config: ClusteringConfig
    ) -> List[str]:
        clusters = []
        for string in strings:
            added = False
            for cluster in clusters:
                similarity = textdistance.jaccard.normalized_similarity(
                    set(string.lower().split()), set(cluster[0].lower().split())
                )
                if similarity >= config.jaccard_threshold:
                    cluster.append(string)
                    added = True
                    break
            if not added:
                clusters.append([string])

        filtered_clusters = [
            cluster for cluster in clusters if len(cluster) >= threshold
        ]
        return [cluster[0] for cluster in filtered_clusters]


class SemanticClustering(ClusteringStrategy):
    """WordLlama-based semantic clustering using embeddings and similarity matrices"""

    def __init__(self):
        self.wl = WordLlama.load(trunc_dim=64)  # Truncate for efficiency

    def _compute_similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        """Compute pairwise similarities between all embeddings"""
        return self.wl.vector_similarity(embeddings, embeddings)

    def _find_representative(self, cluster: List[str]) -> str:
        """Find the most representative string in a cluster using embeddings"""
        if len(cluster) == 1:
            return cluster[0]

        embeddings = self.wl.embed(cluster)
        sim_matrix = self._compute_similarity_matrix(embeddings)
        avg_similarities = np.mean(sim_matrix, axis=1)
        most_representative_idx = np.argmax(avg_similarities)

        return cluster[most_representative_idx]

    def _semantic_deduplication(
        self, strings: List[str], similarity_threshold: float
    ) -> List[Tuple[str, List[str]]]:
        """
        Deduplicate strings based on semantic similarity.
        Returns list of (representative, similar_strings) tuples.
        """
        if not strings:
            return []

        embeddings = self.wl.embed(strings)
        sim_matrix = self._compute_similarity_matrix(embeddings)

        used = set()
        clusters = []

        for i in range(len(strings)):
            if i in used:
                continue

            similar_indices = np.where(sim_matrix[i] >= similarity_threshold)[0]
            similar_indices = [idx for idx in similar_indices if idx not in used]

            if len(similar_indices) >= 1:
                cluster_strings = [strings[idx] for idx in similar_indices]
                representative = self._find_representative(cluster_strings)
                clusters.append((representative, cluster_strings))
                used.update(similar_indices)

        return clusters

    def cluster_strings(
        self, strings: List[str], threshold: int, config: ClusteringConfig
    ) -> List[str]:
        """Cluster strings using semantic similarity."""
        clusters = self._semantic_deduplication(strings, config.semantic_threshold)
        return [rep for rep, cluster in clusters if len(cluster) >= threshold]


def get_clustering_strategy(
    strings: List[str], config: ClusteringConfig
) -> ClusteringStrategy:
    """Factory function to get appropriate clustering strategy"""
    if any(
        len(s.split()) > 5 or len(s) > config.min_length_for_semantic for s in strings
    ):
        return SemanticClustering()
    return JaccardClustering()
