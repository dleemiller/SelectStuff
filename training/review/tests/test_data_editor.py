import pytest
import streamlit as st
from review.core.data_editor import DataEditor, WidgetType, FieldConfig


class TestDataEditor:
    def test_field_config_initialization(self):
        """Test default field configurations"""
        editor = DataEditor()

        assert "article_text" in editor.field_configs
        assert editor.field_configs["article_text"].widget_type == WidgetType.TEXT_AREA
        assert editor.field_configs["article_text"].height == 300

    def test_detect_field_type_date(self):
        """Test field type detection for dates"""
        editor = DataEditor({"publication_date": FieldConfig(WidgetType.DATE)})

        config = editor.detect_field_type("publication_date", "2024-01-01")
        assert config.widget_type == WidgetType.DATE

    def test_detect_field_type_number(self):
        """Test field type detection for numbers"""
        editor = DataEditor()

        # Numbers are handled as text input in your implementation
        config = editor.detect_field_type("amount", "123.45")
        assert config.widget_type == WidgetType.TEXT_INPUT

    def test_detect_field_type_list(self):
        """Test field type detection for lists"""
        editor = DataEditor()
        test_list = ["item1", "item2", "item3"]

        config = editor.detect_field_type("test_list", test_list)
        assert config.widget_type == WidgetType.TEXT_AREA
        assert config.height == 100

    def test_render_field_list(self):
        """Test rendering list fields"""
        editor = DataEditor()
        test_list = ["item1", "item2", "item3"]

        # Mock st.text_area
        with pytest.MonkeyPatch().context() as m:

            def mock_text_area(*args, **kwargs):
                return "\n".join(test_list)

            m.setattr(st, "text_area", mock_text_area)

            result = editor.render_field("test_list", test_list)

        assert isinstance(result, list)
        assert len(result) == 3
        assert result == test_list

    def test_edit_data(self):
        """Test editing complete data dictionary"""
        editor = DataEditor()
        test_data = {
            "title": "Test Title",
            "tags": ["tag1", "tag2"],
            "content": "Test content",
        }

        # Mock streamlit inputs
        with pytest.MonkeyPatch().context() as m:

            def mock_text_input(*args, **kwargs):
                return test_data["title"]

            def mock_text_area(*args, **kwargs):
                if args[1] == "\n".join(test_data["tags"]):
                    return "\n".join(test_data["tags"])
                return test_data["content"]

            m.setattr(st, "text_input", mock_text_input)
            m.setattr(st, "text_area", mock_text_area)

            result = editor.edit_data(test_data)

        assert result["title"] == test_data["title"]
        assert result["tags"] == test_data["tags"]
        assert result["content"] == test_data["content"]
