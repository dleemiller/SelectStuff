from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Callable, TypeVar, Type
import streamlit as st
import json
from datetime import datetime
import re
from enum import Enum, auto

T = TypeVar("T")


class WidgetType(Enum):
    """Types of input widgets available"""

    TEXT_INPUT = auto()
    TEXT_AREA = auto()
    NUMBER = auto()
    DATE = auto()
    SELECT = auto()
    MULTISELECT = auto()
    TOGGLE = auto()
    JSON = auto()
    CODE = auto()


@dataclass
class FieldValidator:
    """Validation rules for a field"""

    func: Callable[[Any], bool]
    error_message: str


@dataclass
class FieldConfig:
    """Configuration for how a field should be displayed and edited"""

    widget_type: WidgetType
    height: Optional[int] = None
    help_text: Optional[str] = None
    validators: List[FieldValidator] = field(default_factory=list)
    options: Optional[List[str]] = None  # For select/multiselect
    default_value: Any = None
    placeholder: Optional[str] = None
    key_prefix: str = ""  # For unique Streamlit keys
    min_value: Optional[float] = None  # For number inputs
    max_value: Optional[float] = None  # For number inputs
    language: Optional[str] = None  # For code editor


class DataEditor:
    """Handles data editing and form management with validation and type conversion"""

    def __init__(self):
        """Initialize the data editor with default field configurations"""
        self.field_configs = self._setup_default_configs()
        self._setup_validators()

    def _setup_default_configs(self) -> Dict[str, FieldConfig]:
        """Set up default configurations for common field types"""
        return {
            # Content fields
            "article_text": FieldConfig(
                widget_type=WidgetType.TEXT_AREA,
                height=300,
                help_text="Main article content",
            ),
            "extracted_quotes": FieldConfig(
                widget_type=WidgetType.TEXT_AREA,
                height=150,
                help_text="Extracted quotes from the article",
            ),
            "summary": FieldConfig(
                widget_type=WidgetType.TEXT_AREA,
                height=150,
                help_text="Article summary",
            ),
            # Metadata fields
            "publication_date": FieldConfig(
                widget_type=WidgetType.DATE, help_text="Article publication date"
            ),
            "primary_category": FieldConfig(
                widget_type=WidgetType.SELECT,
                options=["news", "sports", "entertainment", "technology", "business"],
                help_text="Primary article category",
            ),
            "keywords": FieldConfig(
                widget_type=WidgetType.TEXT_AREA,
                height=100,
                help_text="Keywords (one per line)",
            ),
            # List fields
            "mentioned_people": FieldConfig(
                widget_type=WidgetType.TEXT_AREA,
                height=100,
                help_text="People mentioned (one per line)",
            ),
            "mentioned_organizations": FieldConfig(
                widget_type=WidgetType.TEXT_AREA,
                height=100,
                help_text="Organizations mentioned (one per line)",
            ),
            # Special fields
            "sentiment_tone": FieldConfig(
                widget_type=WidgetType.SELECT,
                options=["positive", "negative", "neutral"],
                help_text="Overall sentiment tone",
            ),
        }

    def _setup_validators(self):
        """Set up validation rules for fields"""
        # Date validator
        self.field_configs["publication_date"].validators.append(
            FieldValidator(
                func=lambda x: bool(re.match(r"^\d{4}-\d{2}-\d{2}$", x)),
                error_message="Date must be in YYYY-MM-DD format",
            )
        )

        # Non-empty validators
        for field in ["article_text", "primary_category"]:
            self.field_configs[field].validators.append(
                FieldValidator(
                    func=lambda x: bool(x and x.strip()),
                    error_message="This field cannot be empty",
                )
            )

    def _validate_field(self, key: str, value: Any) -> List[str]:
        """
        Validate a field value against its validators

        Args:
            key: Field name
            value: Field value

        Returns:
            List of error messages (empty if validation passed)
        """
        errors = []
        config = self.field_configs.get(key)
        if config and config.validators:
            for validator in config.validators:
                try:
                    if not validator.func(value):
                        errors.append(validator.error_message)
                except Exception as e:
                    errors.append(f"Validation error: {str(e)}")
        return errors

    def _convert_value(self, value: Any, widget_type: WidgetType) -> Any:
        """Convert value to appropriate type based on widget type"""
        try:
            if widget_type == WidgetType.NUMBER:
                return float(value)
            elif widget_type == WidgetType.DATE:
                return datetime.strptime(value, "%Y-%m-%d").date()
            elif widget_type == WidgetType.JSON:
                return json.loads(value)
            return value
        except Exception as e:
            st.error(f"Error converting value: {str(e)}")
            return value

    def render_field(
        self, key: str, value: Any, override_config: Optional[FieldConfig] = None
    ) -> Any:
        """
        Render an input field based on its configuration

        Args:
            key: Field name
            value: Current field value
            override_config: Optional configuration override

        Returns:
            Edited field value
        """
        config = override_config or self.field_configs.get(
            key, FieldConfig(widget_type=WidgetType.TEXT_INPUT)
        )

        # Create unique key for Streamlit
        widget_key = f"{config.key_prefix}{key}"

        # Add help text if available
        if config.help_text:
            st.help(config.help_text)

        # Render appropriate widget based on type
        try:
            if config.widget_type == WidgetType.TEXT_AREA:
                edited_value = st.text_area(
                    key,
                    value=str(value) if value is not None else "",
                    height=config.height,
                    placeholder=config.placeholder,
                    key=widget_key,
                )

            elif config.widget_type == WidgetType.SELECT:
                edited_value = st.selectbox(
                    key,
                    options=config.options or [],
                    index=(
                        config.options.index(value)
                        if value in (config.options or [])
                        else 0
                    ),
                    key=widget_key,
                )

            elif config.widget_type == WidgetType.MULTISELECT:
                edited_value = st.multiselect(
                    key,
                    options=config.options or [],
                    default=value if isinstance(value, list) else [],
                    key=widget_key,
                )

            elif config.widget_type == WidgetType.NUMBER:
                edited_value = st.number_input(
                    key,
                    value=float(value) if value is not None else 0.0,
                    min_value=config.min_value,
                    max_value=config.max_value,
                    key=widget_key,
                )

            elif config.widget_type == WidgetType.DATE:
                edited_value = st.date_input(
                    key,
                    value=(
                        datetime.strptime(value, "%Y-%m-%d").date()
                        if value
                        else datetime.now().date()
                    ),
                    key=widget_key,
                )

            elif config.widget_type == WidgetType.TOGGLE:
                edited_value = st.toggle(key, value=bool(value), key=widget_key)

            elif config.widget_type == WidgetType.CODE:
                edited_value = st.code(
                    value or "", language=config.language, key=widget_key
                )

            elif config.widget_type == WidgetType.JSON:
                edited_value = st.text_area(
                    key,
                    value=json.dumps(value, indent=2) if value else "{}",
                    height=config.height,
                    key=widget_key,
                )

            else:  # Default to TEXT_INPUT
                edited_value = st.text_input(
                    key,
                    value=str(value) if value is not None else "",
                    placeholder=config.placeholder,
                    key=widget_key,
                )

            # Validate and convert value
            errors = self._validate_field(key, edited_value)
            if errors:
                for error in errors:
                    st.error(error)

            return self._convert_value(edited_value, config.widget_type)

        except Exception as e:
            st.error(f"Error rendering field {key}: {str(e)}")
            return value

    def render_list_field(
        self, key: str, values: List[Any], config: Optional[FieldConfig] = None
    ) -> List[Any]:
        """
        Render a list of values as a multi-line text area

        Args:
            key: Field name
            values: List of values
            config: Optional field configuration

        Returns:
            Edited list of values
        """
        text_value = "\n".join(str(v) for v in values)
        edited_text = st.text_area(
            key,
            value=text_value,
            height=config.height if config else 150,
            help=config.help_text if config else None,
        )
        return [v.strip() for v in edited_text.split("\n") if v.strip()]

    def render_dict_field(
        self, key: str, value: Dict[str, Any], config: Optional[FieldConfig] = None
    ) -> Dict[str, Any]:
        """
        Render a dictionary as a JSON editor

        Args:
            key: Field name
            value: Dictionary value
            config: Optional field configuration

        Returns:
            Edited dictionary
        """
        try:
            json_str = st.text_area(
                key,
                value=json.dumps(value, indent=2),
                height=config.height if config else 150,
                help=config.help_text if config else None,
            )
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {str(e)}")
            return value
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return value
