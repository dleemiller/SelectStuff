from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import streamlit as st
import json
from datetime import datetime
from enum import Enum


class WidgetType(Enum):
    """Types of input widgets available"""

    TEXT_INPUT = "text_input"
    TEXT_AREA = "text_area"
    SELECT = "select"
    DATE = "date"
    JSON = "json"


@dataclass
class FieldConfig:
    """Configuration for how a field should be displayed and edited"""

    widget_type: WidgetType
    height: Optional[int] = None
    help_text: Optional[str] = None
    options: Optional[List[str]] = None


class DataEditor:
    """Handles data editing with automatic type detection and configurable fields"""

    # Default configurations for common fields
    DEFAULT_CONFIGS = {
        "article_text": FieldConfig(WidgetType.TEXT_AREA, height=300),
        "extracted_quotes": FieldConfig(WidgetType.TEXT_AREA, height=150),
        "content": FieldConfig(WidgetType.TEXT_AREA, height=300),
        "description": FieldConfig(WidgetType.TEXT_AREA, height=150),
        "summary": FieldConfig(WidgetType.TEXT_AREA, height=150),
    }

    # Fields that should use select boxes with predefined options
    SELECT_FIELDS = {
        "primary_category": [
            "world",
            "entertainment",
            "science",
            "health",
            "business",
            "sports",
            "politics",
            "technology",
            "legal",
            "community",
            "public_safety",
        ],
        "content_type": [
            "editorial",
            "opinion",
            "analysis",
            "reporting",
            "interview",
            "investigative",
            "press_release",
            "blog_post",
        ],
        "sentiment": ["positive", "negative", "neutral"],
        "status": ["draft", "published", "archived"],
    }

    def __init__(self, custom_configs: Optional[Dict[str, FieldConfig]] = None):
        """Initialize with optional custom field configurations"""
        self.field_configs = self.DEFAULT_CONFIGS.copy()
        if custom_configs:
            self.field_configs.update(custom_configs)

    def detect_field_type(self, key: str, value: Any) -> FieldConfig:
        """Automatically detect appropriate widget type for a field"""
        # Check if there's a predefined configuration
        if key in self.field_configs:
            return self.field_configs[key]

        # Check if it's a select field
        if key in self.SELECT_FIELDS:
            return FieldConfig(WidgetType.SELECT, options=self.SELECT_FIELDS[key])

        # Lists should be handled as text areas with one item per line
        if isinstance(value, list):
            return FieldConfig(WidgetType.TEXT_AREA, height=100)
        # Only use JSON widget for dictionaries
        elif isinstance(value, dict):
            return FieldConfig(WidgetType.JSON, height=150)
        elif isinstance(value, str):
            # Use text area for longer text fields or specific field names
            if len(value) > 200 or any(
                word in key for word in ["text", "content", "description", "summary"]
            ):
                return FieldConfig(WidgetType.TEXT_AREA, height=150)
            return FieldConfig(WidgetType.TEXT_INPUT)

        return FieldConfig(WidgetType.TEXT_INPUT)

    def render_field(self, key: str, value: Any) -> Any:
        """Render an input field with automatic type detection"""
        config = self.detect_field_type(key, value)
        display_label = key.replace("_", " ").title()

        try:
            if config.widget_type == WidgetType.TEXT_AREA:
                if isinstance(value, list):
                    # Convert list to multi-line string
                    text_value = "\n".join(
                        str(item).strip('"') for item in value if item
                    )
                    edited_value = st.text_area(
                        label=display_label,
                        value=text_value,
                        height=config.height,
                        help=config.help_text,
                    )
                    # Convert back to list, removing empty lines and extra whitespace
                    return [
                        item.strip()
                        for item in edited_value.split("\n")
                        if item.strip()
                    ]
                else:
                    return st.text_area(
                        label=display_label,
                        value=str(value) if value is not None else "",
                        height=config.height,
                        help=config.help_text,
                    )

            elif config.widget_type == WidgetType.SELECT:
                options = config.options or self.SELECT_FIELDS.get(key, [])
                current_idx = options.index(value) if value in options else 0
                return st.selectbox(
                    label=display_label,
                    options=options,
                    index=current_idx,
                    help=config.help_text,
                )

            elif config.widget_type == WidgetType.DATE:
                try:
                    date_value = (
                        datetime.strptime(value, "%Y-%m-%d").date()
                        if value
                        else datetime.now().date()
                    )
                except (TypeError, ValueError):
                    date_value = datetime.now().date()
                return st.date_input(
                    label=display_label, value=date_value, help=config.help_text
                )

            elif config.widget_type == WidgetType.JSON:
                if isinstance(value, (dict, list)):
                    json_str = json.dumps(value, indent=2)
                else:
                    json_str = "{}" if isinstance(value, dict) else "[]"

                edited_str = st.text_area(
                    label=display_label,
                    value=json_str,
                    height=config.height,
                    help=config.help_text,
                )

                try:
                    return json.loads(edited_str)
                except json.JSONDecodeError:
                    st.error(f"Invalid JSON in {key}")
                    return value

            else:  # Default to TEXT_INPUT
                return st.text_input(
                    label=display_label,
                    value=str(value) if value is not None else "",
                    help=config.help_text,
                )

        except Exception as e:
            st.error(f"Error rendering field {key}: {str(e)}")
            return value

    def edit_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Edit all fields in the data dictionary"""
        edited_data = {}

        for key, value in data.items():
            edited_data[key] = self.render_field(key, value)

        return edited_data
