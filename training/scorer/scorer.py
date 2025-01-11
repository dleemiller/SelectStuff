import logging
import numpy as np
from typing import Any, get_args, get_origin, Union
from datetime import date

import dspy
from wordllama import WordLlama
from core.dispatcher import compare_value

logger = logging.getLogger(__name__)


def strip_optional(hint: Any) -> Any:
    """Removes Optional[...] wrappers from a type annotation.

    Converts Union[T, None] into T and returns the base type.

    Args:
        hint (Any): The type hint to process.

    Returns:
        Any: The base type without the Optional wrapper.
    """
    origin = get_origin(hint)
    if origin is Union:
        args = get_args(hint)
        # Detect Union[T, None] by checking if one of the args is `type(None)`
        if len(args) == 2 and type(None) in args:
            # Return whichever arg is not None
            return args[0] if args[0] is not type(None) else args[1]
    return hint


class WordLlamaScorer:
    """A scorer that compares dictionaries using type-aware logic and WordLlama.

    This class processes fields defined in a signature class (with type annotations),
    removes Optional[...] wrappers for cleaner type handling, and computes similarity
    scores between reference and prediction dictionaries.

    Attributes:
        annotations (dict): The type annotations of the signature class.
        fields (dict): The fields to compare, with stripped type hints.
        wl (WordLlama): The WordLlama instance used for embeddings and similarity.
    """

    def __init__(self, signature_class: type, skip_fields: list[str] | None = None):
        """Initializes the scorer with a signature class and optional skipped fields.

        Args:
            signature_class (type): The class with type annotations defining the fields.
            skip_fields (list[str] | None): List of field names to exclude. Defaults to None.
        """
        self.annotations = signature_class.__annotations__

        # If skip_fields is None, make it an empty list to simplify checks
        if skip_fields is None:
            skip_fields = []

        # Strip Optional[...] wrappers from annotations and store fields
        self.fields = {
            field_name: strip_optional(field_type)
            for field_name, field_type in self.annotations.items()
            if field_name not in skip_fields
        }

        # Load the underlying WordLlama model
        self.wl = WordLlama.load()

    @classmethod
    def from_signature(
        cls, signature_class: type, skip_fields: list[str] | None = None
    ) -> "WordLlamaScorer":
        """Creates a WordLlamaScorer instance from a signature class.

        Args:
            signature_class (type): The class with type annotations defining the fields.
            skip_fields (list[str] | None): List of field names to exclude. Defaults to None.

        Returns:
            WordLlamaScorer: An initialized scorer.
        """
        return cls(signature_class, skip_fields)

    def __call__(
        self,
        reference: dspy.Example,
        prediction: dspy.Prediction,
        trace: Any = None,
    ) -> float:
        """Compares dspy.Example and dspy.Prediction objects.

        Converts both inputs to dictionaries using `.toDict()` and compares
        them field-by-field using type-aware logic.

        Args:
            reference (dspy.Example): The reference example object.
            prediction (dspy.Prediction): The prediction object.
            trace (Any, optional): Optional debug information (currently unused).

        Returns:
            float: The average similarity score across all fields, between 0.0 and 1.0.
        """
        reference_dict = reference.toDict()
        prediction_dict = prediction.toDict()

        scores = []
        for field_name, field_type in self.fields.items():
            ref_val = reference_dict.get(field_name)
            pred_val = prediction_dict.get(field_name)

            if ref_val == pred_val:  # exact match (including None)
                field_score = 1.0
            elif ref_val is None or pred_val is None:
                field_score = 0.0
            else:
                # Use WordLlama instance with singledispatch for field comparison
                field_score = compare_value(ref_val, pred_val, self.wl)

            # logger.info(f"{ref_val}, {pred_val}, {field_score}")
            scores.append(field_score)

        # Return the average score across all fields
        return float(np.mean(scores)) if scores else 0.0
