import logging
from functools import singledispatch
from typing import Any, List
import numpy as np
from datetime import date
import textdistance

SEMANTIC_THRESHOLD = 32


@singledispatch
def compare_value(ref_val: Any, pred_val: Any, wl) -> float:
    """Default comparison function (fallback).

    Performs an exact match comparison for fallback.

    Args:
        ref_val: The reference value.
        pred_val: The predicted value.
        wl: The WordLlama instance.

    Returns:
        float: A similarity score between 0.0 and 1.0.
    """
    return 1.0 if ref_val == pred_val else 0.0


@compare_value.register
def _(ref_val: str, pred_val: str, wl) -> float:
    """Compares two strings using exact match, Jaccard similarity, or WordLlama.

    - If the strings are identical (case-insensitive), score as 1.0.
    - If the strings are shorter than `SEMANTIC_THRESHOLD`, use Jaccard similarity.
    - Otherwise, use WordLlama's semantic similarity.

    Args:
        ref_val: The reference string.
        pred_val: The predicted string.
        wl: The WordLlama instance.

    Returns:
        float: A similarity score between 0.0 and 1.0.
    """
    if not ref_val or not pred_val:
        return 0.0

    # Case-insensitive exact match
    if ref_val.lower() == pred_val.lower():
        return 1.0

    # Use Jaccard similarity for shorter strings
    if len(ref_val) < SEMANTIC_THRESHOLD or len(pred_val) < SEMANTIC_THRESHOLD:
        return float(textdistance.jaccard.normalized_similarity(ref_val, pred_val))

    # Default to WordLlama similarity
    return float(wl.similarity(ref_val, pred_val))


@compare_value.register
def _(ref_val: list, pred_val: list, wl) -> float:
    """Compares two lists of strings using WordLlama's cross-similarity.

    Args:
        ref_val: The reference list of strings.
        pred_val: The predicted list of strings.
        wl: The WordLlama instance.

    Returns:
        float: A similarity score between 0.0 and 1.0.
    """
    if not ref_val or not pred_val:
        return 0.0

    ref_embeds = wl.embed(ref_val, norm=True)
    pred_embeds = wl.embed(pred_val, norm=True)
    sim_matrix = wl.vector_similarity(ref_embeds, pred_embeds)

    precision = np.mean(np.max(sim_matrix, axis=1))
    recall = np.mean(np.max(sim_matrix, axis=0))
    return (precision + recall) / 2


@compare_value.register
def _(ref_val: date, pred_val: date, wl) -> float:
    """Compares two dates using the formula 1 / (1 + |days_difference|).

    Args:
        ref_val: The reference date.
        pred_val: The predicted date.
        wl: The WordLlama instance (not used for date comparison).

    Returns:
        float: A similarity score between 0.0 and 1.0.
    """
    diff_days = abs((pred_val - ref_val).days)
    return 1.0 / (1.0 + diff_days)


@compare_value.register
def _(ref_val: float, pred_val: float, wl) -> float:
    """Compares two floats, scaled by the reference's magnitude.

    Args:
        ref_val: The reference float.
        pred_val: The predicted float.
        wl: The WordLlama instance (not used for float comparison).

    Returns:
        float: A similarity score between 0.0 and 1.0.
    """
    if ref_val == 0.0 and pred_val == 0.0:
        return 1.0

    scale = abs(ref_val) if ref_val != 0 else 1.0
    difference = abs(ref_val - pred_val)

    ratio = difference / (scale + 1e-6)  # Avoid zero-division
    return max(0.0, 1.0 - ratio)
