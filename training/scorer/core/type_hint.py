from __future__ import annotations
from typing import Any, Optional, Literal, get_args, get_origin, Union


class TypeHintUtils:
    """
    A mixin or utility class that provides helpful static methods for analyzing and
    interpreting Python type annotations.
    """

    @staticmethod
    def get_base_type(type_hint: Any) -> Any:
        """
        Extract the base type from potentially nested type hints.
        e.g.:
          - Optional[str] -> str
          - Union[str, None] -> str
          - List[str] -> (list, str)
          - Optional[List[str]] -> (list, str)
        """
        origin = get_origin(type_hint)

        # Handle Optional types (Union[T, None])
        if origin is Union:
            args = get_args(type_hint)
            # Exactly two args and the second is None -> an Optional scenario
            if len(args) == 2 and args[1] is type(None):
                return TypeHintUtils.get_base_type(args[0])

        # If it's a container type (e.g. List, Dict, etc.), capture its first generic arg
        if origin is not None:
            args = get_args(type_hint)
            if args:
                return (origin, TypeHintUtils.get_base_type(args[0]))

        # Otherwise, just return the original type
        return type_hint

    @staticmethod
    def is_literal_type(type_hint: Any) -> bool:
        """Check if a type hint is a Literal type (possibly nested in Optional)."""
        origin = get_origin(type_hint)
        if origin is Literal:
            return True
        if origin is Union:
            args = get_args(type_hint)
            if len(args) == 2 and args[1] is type(None):
                return TypeHintUtils.is_literal_type(args[0])
        return False

    @staticmethod
    def get_literal_values(type_hint: Any) -> Optional[tuple]:
        """
        Extract the allowed literal values from a Literal type (possibly nested in Optional).
        Returns None if the type is not a Literal.
        """
        origin = get_origin(type_hint)
        if origin is Literal:
            return get_args(type_hint)

        if origin is Union:
            args = get_args(type_hint)
            if len(args) == 2 and args[1] is type(None):
                return TypeHintUtils.get_literal_values(args[0])

        return None

    @staticmethod
    def is_optional_type(type_hint: Any) -> bool:
        """
        Check if a type hint is Optional (i.e. Union[..., None]).
        """
        origin = get_origin(type_hint)
        if origin is Union:
            args = get_args(type_hint)
            return len(args) == 2 and args[1] is type(None)
        return False
