from typing import (
    Any,
    Dict,
    Optional,
    Type,
    Union,
    get_args,
    get_origin,
)

import json
from pydantic import BaseModel
from sqlalchemy import Column, Text
from sqlmodel import SQLModel, Field


def _normalize_sqlmodel_type(annotation: Any) -> Any:
    """
    Normalize a given type annotation to something SQLModel can store
    natively, defaulting to `str` for collection types.

    Args:
        annotation (Any): The raw type annotation from a Pydantic field.

    Returns:
        Any: An appropriate Python type usable by SQLModel (e.g., Optional[str]).
    """
    if annotation is None:
        return str

    # If it's a collection type, store as JSON string
    if annotation in (list, dict, set, tuple):
        return str

    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return Optional[_normalize_sqlmodel_type(non_none_args[0])]
        return str

    # If it's a direct type (e.g., int, str, float, datetime), use as-is
    if isinstance(annotation, type):
        return annotation

    # Fallback
    return str


class SignatureToSQLModel:
    """Helper class to convert DSPy/Pydantic signature classes into SQLModel classes."""

    @classmethod
    def to_sqlmodel(
        cls,
        signature_cls: Type[BaseModel],
        table_name: Optional[str] = None,
        base_fields: Optional[Dict[str, Any]] = None,
    ) -> Type[SQLModel]:
        """
        Convert a Pydantic-based signature class into a SQLModel class.

        This method:
        - Dynamically creates a new SQLModel subclass.
        - Maps fields from the signature class (via Pydantic v2) to SQLModel fields.
        - Stores collection types as JSON text columns.

        Args:
            signature_cls (Type[BaseModel]): The Pydantic class to convert.
            table_name (Optional[str]): A custom table name, if desired. Defaults to `None`.
            base_fields (Optional[Dict[str, Any]]): Extra fields to add (e.g., an `id` field).

        Returns:
            Type[SQLModel]: A dynamically created SQLModel subclass.
        """
        annotations: Dict[str, Any] = {}
        field_definitions: Dict[str, Any] = {}

        # Optionally add base fields (e.g., an 'id' primary key)
        if base_fields:
            for field_name, (annot, field_obj) in base_fields.items():
                annotations[field_name] = annot
                field_definitions[field_name] = field_obj
        else:
            annotations["id"] = Optional[int]
            field_definitions["id"] = Field(default=None, primary_key=True)

        # Create a name for the new SQLModel class
        model_name = f"{signature_cls.__name__}SQLModel"

        # Collect field definitions from the Pydantic model
        for name, field_info in signature_cls.model_fields.items():
            raw_annotation = field_info.annotation
            is_required = field_info.is_required()

            # Convert to an SQLModel-friendly type
            final_annotation = _normalize_sqlmodel_type(raw_annotation)

            # Make it Optional if the field is not required
            if not is_required and not str(final_annotation).startswith(
                "typing.Optional"
            ):
                final_annotation = Optional[final_annotation]

            # Assign the final annotation
            annotations[name] = final_annotation

            # If we decided this field is actually a str, we might store it as TEXT
            # so we can keep JSON data inside.
            sa_column = None
            if final_annotation in (str, Optional[str]):
                # Use a TEXT column for string-based fields (including those storing JSON).
                sa_column = Column(Text)

            # Build the Field(...) parameters
            field_definitions[name] = Field(
                default=None if not is_required else ...,
                description=(
                    field_info.json_schema_extra.get("desc", "")
                    if field_info.json_schema_extra
                    else ""
                ),
                sa_column=sa_column,
            )

        # We define a custom __init__ to serialize JSON for collection types
        def init(self, **data):
            for field_name, field_value in data.items():
                # If the field is a collection, turn it into a JSON string
                if isinstance(field_value, (list, dict, set, tuple)):
                    data[field_name] = json.dumps(field_value)
            super(model, self).__init__(**data)

        # Dynamically create the SQLModel class
        model = type(
            model_name,
            (SQLModel,),
            {
                "__tablename__": table_name or model_name.lower(),
                "__annotations__": annotations,
                **field_definitions,
                "__module__": signature_cls.__module__,
                "__init__": init,
                # This ensures SQLModel treats it like a table by default
                "model_config": {"table": True},
            },
        )

        return model
