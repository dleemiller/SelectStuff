from typing import List, Literal, Dict, Any, Union, TypeVar, Generic, Type
from collections import Counter
import itertools
from pydantic import BaseModel, ValidationError
from typing import get_origin, get_args
from enum import Enum
from dataclasses import dataclass

from aggregate.cluster import (
    ClusteringConfig,
    get_clustering_strategy,
    SemanticClustering,
)

T = TypeVar("T", bound=BaseModel)


class FieldType(Enum):
    """Enumeration of possible field types for aggregation"""

    LITERAL = "literal"
    STRING = "string"
    STRING_LIST = "string_list"
    OTHER = "other"


@dataclass
class FieldInfo:
    """Information about a field to be aggregated"""

    name: str
    type_hint: Any
    values: List[Any]
    is_optional: bool


class LLMOutputAggregator(Generic[T]):
    """Aggregates multiple LLM outputs into a single consistent output."""

    def __init__(self, model_class: Type[T], debug: bool = False):
        self.model_class = model_class
        self.debug = debug
        self.config = ClusteringConfig()

    @classmethod
    def aggregate(
        cls,
        model_class: Type[T],
        predictions: List[Any],
        threshold: int = 2,
        debug: bool = False,
    ) -> T:
        """Main entry point for aggregating predictions."""
        aggregator = cls(model_class, debug=debug)
        return aggregator._create_output(predictions, threshold)

    def _get_field_type(self, field_type: Any, sample_value: Any) -> FieldType:
        """Determine the type category of a field for aggregation"""
        origin_type = get_origin(field_type)

        if origin_type is Literal:
            return FieldType.LITERAL
        elif isinstance(sample_value, str):
            return FieldType.STRING
        elif isinstance(sample_value, list) and all(
            isinstance(x, str) for x in sample_value
        ):
            return FieldType.STRING_LIST
        else:
            return FieldType.OTHER

    def _prepare_field_info(
        self, field_name: str, field_type: Any, field_values: List[Any]
    ) -> FieldInfo:
        """Prepare field information for aggregation"""
        is_optional = get_origin(field_type) is Union and type(None) in get_args(
            field_type
        )

        # Filter out None values
        valid_values = [val for val in field_values if val is not None]

        return FieldInfo(
            name=field_name,
            type_hint=field_type,
            values=valid_values,
            is_optional=is_optional,
        )

    def _handle_empty_values(self, field_info: FieldInfo) -> Any:
        """Handle cases where no valid values are present"""
        if field_info.is_optional:
            return None
        raise ValueError(f"No values found for required field '{field_info.name}'")

    def _aggregate_literal_field(self, values: List[Any]) -> Any:
        """Aggregate a field with Literal type hint"""
        return self._majority_vote(values)

    def _aggregate_string_field(self, values: List[str], threshold: int) -> str:
        """Aggregate a string field using appropriate clustering"""
        strategy = get_clustering_strategy(values, self.config)

        if isinstance(strategy, SemanticClustering):
            clusters = strategy.cluster_strings(values, threshold, self.config)
            return clusters[0] if clusters else values[0]

        return self._majority_vote(values)

    def _aggregate_string_list_field(
        self, values: List[List[str]], threshold: int
    ) -> List[str]:
        """Aggregate a list of strings field"""
        # Flatten the list of lists
        flattened = list(itertools.chain.from_iterable(values))

        # Use appropriate clustering strategy
        strategy = get_clustering_strategy(flattened, self.config)
        return strategy.cluster_strings(flattened, threshold, self.config)

    def _majority_vote(self, values: List[Any]) -> Any:
        """Perform majority voting on a list of values"""
        counter = Counter(values)
        if self.debug:
            import logging

            logging.info(f"Majority vote counter: {counter}")
        return counter.most_common(1)[0][0]

    def _aggregate_field(
        self, field_name: str, field_type: Any, field_values: List[Any], threshold: int
    ) -> Any:
        """Aggregate a single field based on its type"""
        # Prepare field information
        field_info = self._prepare_field_info(field_name, field_type, field_values)

        # Handle empty values
        if not field_info.values:
            return self._handle_empty_values(field_info)

        # Determine field type and delegate to appropriate handler
        field_type = self._get_field_type(field_type, field_info.values[0])

        match field_type:
            case FieldType.LITERAL:
                return self._aggregate_literal_field(field_info.values)

            case FieldType.STRING:
                return self._aggregate_string_field(field_info.values, threshold)

            case FieldType.STRING_LIST:
                return self._aggregate_string_list_field(field_info.values, threshold)

            case FieldType.OTHER:
                return self._majority_vote(field_info.values)

    def _create_output(self, predictions: List[Any], threshold: int) -> T:
        """Creates the final output from aggregated fields."""
        if not predictions:
            raise ValueError("No predictions to aggregate.")

        aggregated_fields: Dict[str, Any] = {}

        for field_name, field_type in self.model_class.__annotations__.items():
            field_values = [
                getattr(pred, field_name, None) or pred.get(field_name)
                for pred in predictions
            ]

            aggregated_fields[field_name] = self._aggregate_field(
                field_name, field_type, field_values, threshold
            )

        try:
            return self.model_class(**aggregated_fields)
        except ValidationError as ve:
            raise ValueError(f"Error creating aggregated output: {ve}")
