from functools import singledispatch
from typing import Any, List
import numpy as np
from datetime import date


@singledispatch
def compare_value(wl, ref_val: Any, pred_val: Any) -> float:
    """Default comparison function (fallback).

    - If both values are `None`, returns `1.0`.
    - If one value is `None`, returns `0.0`.
    - Otherwise performs an exact match comparison.

    Args:
        wl: The WordLlama instance.
        ref_val: The reference value.
        pred_val: The predicted value.

    Returns:
        float: A similarity score between 0.0 and 1.0.
    """
    if ref_val is None and pred_val is None:
        return 1.0
    if ref_val is None or pred_val is None:
        return 0.0

    return 1.0 if ref_val == pred_val else 0.0


@compare_value.register
def _(wl, ref_val: str, pred_val: str) -> float:
    """Compares two strings using WordLlama's semantic similarity.

    Args:
        wl: The WordLlama instance.
        ref_val: The reference string.
        pred_val: The predicted string.

    Returns:
        float: A similarity score between 0.0 and 1.0.
    """
    if not ref_val or not pred_val:
        return 0.0

    return float(wl.similarity(ref_val, pred_val))


@compare_value.register
def _(wl, ref_val: list, pred_val: list) -> float:
    """Compares two lists of strings using WordLlama's cross-similarity.

    Args:
        wl: The WordLlama instance.
        ref_val: The reference list of strings.
        pred_val: The predicted list of strings.

    Returns:
        float: A similarity score between 0.0 and 1.0.
    """
    if not ref_val or not pred_val:
        return 0.0

    ref_embeds = wl.embed(ref_val)
    pred_embeds = wl.embed(pred_val)
    sim_matrix = wl.vector_similarity(ref_embeds, pred_embeds)

    precision = np.mean(np.max(sim_matrix, axis=1))
    recall = np.mean(np.max(sim_matrix, axis=0))
    return (precision + recall) / 2


@compare_value.register
def _(wl, ref_val: date, pred_val: date) -> float:
    """Compares two dates using the formula 1 / (1 + |days_difference|).

    Args:
        wl: The WordLlama instance (not used for date comparison).
        ref_val: The reference date.
        pred_val: The predicted date.

    Returns:
        float: A similarity score between 0.0 and 1.0.
    """
    diff_days = abs((pred_val - ref_val).days)
    return 1.0 / (1.0 + diff_days)


@compare_value.register
def _(wl, ref_val: float, pred_val: float) -> float:
    """Compares two floats, scaled by the reference's magnitude.

    Args:
        wl: The WordLlama instance (not used for float comparison).
        ref_val: The reference float.
        pred_val: The predicted float.

    Returns:
        float: A similarity score between 0.0 and 1.0.
    """
    if ref_val == 0.0 and pred_val == 0.0:
        return 1.0

    scale = abs(ref_val) if ref_val != 0 else 1.0
    difference = abs(ref_val - pred_val)

    ratio = difference / (scale + 1e-6)  # avoid zero-div
    return max(0.0, 1.0 - ratio)
