from typing import (
    Any,
    Dict,
    Optional,
    Type,
    Union,
    get_args,
    get_origin,
)
from datetime import datetime
from sqlmodel import SQLModel, Field
from pydantic import BaseModel
import json


def _normalize_sqlmodel_type(annotation: Any) -> Any:
    """
    Normalize a given type annotation to something SQLModel can handle.
    Fallback is `str`.
    """
    if annotation is None:
        return str

    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return Optional[_normalize_sqlmodel_type(non_none_args[0])]
        return str

    if origin in (list, dict, set, tuple):
        return str

    if isinstance(annotation, type):
        return annotation

    return str


class SignatureToSQLModel:
    """Helper class to convert DSPy Signatures to SQLModel classes."""

    @classmethod
    def to_sqlmodel(
        cls,
        signature_cls: Type[BaseModel],
        table_name: Optional[str] = None,
        base_fields: Optional[Dict[str, Any]] = None,
    ) -> Type[SQLModel]:
        """
        Convert a Pydantic-based signature class into a SQLModel class.
        """
        annotations: Dict[str, Any] = {}
        field_definitions: Dict[str, Any] = {}

        # Add base fields (e.g., default id field) if provided
        if base_fields:
            for field_name, (annot, field_obj) in base_fields.items():
                annotations[field_name] = annot
                field_definitions[field_name] = field_obj
        else:
            annotations["id"] = Optional[int]
            field_definitions["id"] = Field(default=None, primary_key=True)

        # Map the signature class fields to SQLModel fields
        for name, field_info in signature_cls.model_fields.items():
            raw_annotation = field_info.annotation
            is_required = field_info.is_required()
            final_annotation = _normalize_sqlmodel_type(raw_annotation)

            # Mark as optional if not required
            if not is_required and not str(final_annotation).startswith(
                "typing.Optional"
            ):
                final_annotation = Optional[final_annotation]

            # Add to model's annotations
            annotations[name] = final_annotation

            # Build the Field(...) definition
            field_definitions[name] = Field(
                default=None if not is_required else ...,
                description=(
                    field_info.json_schema_extra.get("desc", "")
                    if field_info.json_schema_extra
                    else ""
                ),
            )

        # Create the model name
        model_name = f"{signature_cls.__name__}SQLModel"

        # Define a custom `__init__` to handle serialization of complex fields
        def __init__(self, **data):
            for field_name, field_value in data.items():
                # Serialize lists, dicts, etc., into JSON strings
                if isinstance(field_value, (list, dict, set)):
                    data[field_name] = json.dumps(field_value)
            super(self.__class__, self).__init__(**data)

        # Define the SQLModel class dynamically
        model = type(
            model_name,
            (SQLModel,),
            {
                "__tablename__": table_name or model_name.lower(),
                "__annotations__": annotations,
                **field_definitions,
                "__module__": signature_cls.__module__,
                "__init__": __init__,
                "model_config": {"table": True},
            },
        )

        return model
