from typing import Any
from collections import Counter
import itertools
from functools import singledispatch
from statistics import median

from aggregate.cluster import (
    ClusteringConfig,
    get_clustering_strategy,
    SemanticClustering,
)


@singledispatch
def aggregate_field(
    values: list, config: ClusteringConfig, threshold: int, debug: bool
) -> Any:
    """Default aggregation method for fields.

    Args:
        values (list[Any]): The list of values to aggregate.
        config (ClusteringConfig): Configuration for clustering-based aggregation.
        threshold (int): Threshold for clustering similarity.
        debug (bool): Whether to enable debug logging.

    Returns:
        Any: Aggregated result.
    """
    if not values:
        return None
    return majority_vote(values, debug)


@aggregate_field.register
def _(values: list[str], config: ClusteringConfig, threshold: int, debug: bool) -> str:
    """Aggregates a field of type `list[str]`.

    Args:
        values (list[str]): The list of string values to aggregate.
        config (ClusteringConfig): Configuration for clustering-based aggregation.
        threshold (int): Threshold for clustering similarity.
        debug (bool): Whether to enable debug logging.

    Returns:
        str: Aggregated string result.
    """
    strategy = get_clustering_strategy(values, config)
    if isinstance(strategy, SemanticClustering):
        clusters = strategy.cluster_strings(values, threshold, config)
        return clusters[0] if clusters else values[0]
    return majority_vote(values, debug)


@aggregate_field.register
def _(
    values: list[list[str]], config: ClusteringConfig, threshold: int, debug: bool
) -> list[str]:
    """Aggregates a field of type `list[list[str]]`.

    Args:
        values (list[list[str]]): The list of string lists to aggregate.
        config (ClusteringConfig): Configuration for clustering-based aggregation.
        threshold (int): Threshold for clustering similarity.
        debug (bool): Whether to enable debug logging.

    Returns:
        list[str]: Aggregated list of strings.
    """
    flattened = list(itertools.chain.from_iterable(values))
    strategy = get_clustering_strategy(flattened, config)
    return strategy.cluster_strings(flattened, threshold, config)


@aggregate_field.register
def _(
    values: list[float], config: ClusteringConfig, threshold: int, debug: bool
) -> float:
    """Aggregates a field of type `list[float]` using the median.

    Args:
        values (list[float]): The list of float values to aggregate.
        config (ClusteringConfig): Configuration for clustering-based aggregation (unused).
        threshold (int): Threshold for clustering similarity (unused).
        debug (bool): Whether to enable debug logging.

    Returns:
        float: Aggregated float value (median).
    """
    if not values:
        return 0.0
    if debug:
        import logging

        logging.info(f"Aggregating list[float] with values: {values}")
    return median(values)


def majority_vote(values: list[Any], debug: bool) -> Any:
    """Performs majority voting on a list of values.

    Args:
        values (list[Any]): The list of values to vote on.
        debug (bool): Whether to enable debug logging.

    Returns:
        Any: The most common value.
    """
    counter = Counter(values)
    if debug:
        import logging

        logging.info(f"Majority vote counter: {counter}")
    return counter.most_common(1)[0][0]
