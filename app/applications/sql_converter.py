from typing import Type, Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from pydantic import create_model


class SignatureToSQLModel:
    """Helper class to convert DSPy Signatures to SQLModel classes."""

    @classmethod
    def to_sqlmodel(
        cls,
        signature_cls,
        table_name: Optional[str] = None,
        base_fields: Optional[Dict[str, Any]] = None,
    ) -> Type[SQLModel]:
        """
        Convert a DSPy Signature class to a SQLModel class.

        Args:
            signature_cls: The DSPy Signature class to convert
            table_name: Optional table name for the SQLModel
            base_fields: Optional dictionary of base fields to include in all models
                        e.g., {'id': (int, Field(primary_key=True))}

        Returns:
            A new SQLModel class
        """
        # Get fields from the signature
        fields = {}

        # Add base fields if provided
        if base_fields:
            fields.update(base_fields)
        else:
            # Default to just an auto-incrementing ID if no base fields provided
            fields["id"] = (int, Field(primary_key=True))

        # Map signature fields to SQLModel fields
        for name, field_info in signature_cls.model_fields.items():
            # Get the annotation type, defaulting to str if none
            field_type = field_info.annotation or str

            # Make the field optional unless it's marked as required
            if not field_info.is_required():
                field_type = Optional[field_type]

            # Create the SQLModel Field with appropriate settings
            sqlmodel_field = Field(
                default=None if not field_info.is_required() else ...,
                description=field_info.json_schema_extra.get("desc", ""),
            )

            fields[name] = (field_type, sqlmodel_field)

        # Create the model name
        model_name = f"{signature_cls.__name__}SQLModel"

        # Create the SQLModel class
        model = create_model(
            model_name, __base__=SQLModel, __module__=signature_cls.__module__, **fields
        )

        # Add table_name if provided
        if table_name:
            model.__table_name__ = table_name

        # Add table=True to make it a proper SQLModel table
        setattr(model, "__table__", True)

        return model
