import streamlit as st
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json

from ..core.file_processor import FileProcessor
from ..core.data_editor import DataEditor
from ..core.types import FileAction, FieldConfig
from ..config import AppConfig


class JSONReviewApp:
    """Main application class for the JSON Review Tool"""
    __version__ = "0.1"

    def __init__(self, config: AppConfig):
        """
        Initialize the application with configuration.

        Args:
            config: Application configuration object
        """
        self.config = config
        self.file_processor = FileProcessor(config)
        self.data_editor = DataEditor()
        self._setup_session_state()

    def _setup_session_state(self):
        """Initialize Streamlit session state variables"""
        if "processed_files" not in st.session_state:
            st.session_state.processed_files = set()
        if "current_index" not in st.session_state:
            st.session_state.current_index = 0

    def _setup_ui(self):
        """Configure the Streamlit UI based on settings"""
        st.set_page_config(
            page_title=self.config.app_title,
            layout="wide" if self.config.wide_mode else "centered",
            initial_sidebar_state="expanded",
            menu_items={
                "About": f"JSON Review Tool v{self.__version__}",
                "Report a bug": "https://github.com/yourusername/json-review/issues",
            },
        )

    def _render_sidebar(self, files: List[Path]):
        """Render the sidebar with statistics and navigation"""
        with st.sidebar:
            st.header("Statistics")
            st.write(f"Total files: {len(files)}")
            st.write(f"Processed: {len(st.session_state.processed_files)}")
            st.write(f"Remaining: {len(files) - len(st.session_state.processed_files)}")

            st.header("Navigation")
            if st.button("Previous File") and st.session_state.current_index > 0:
                st.session_state.current_index -= 1
                st.rerun()
            if (
                st.button("Next File")
                and st.session_state.current_index < len(files) - 1
            ):
                st.session_state.current_index += 1
                st.rerun()

            st.header("Options")
            if st.button("Reset Progress"):
                st.session_state.processed_files.clear()
                st.session_state.current_index = 0
                st.rerun()

    def _handle_file_review(self, current_file: Path):
        """Handle the review of a single file"""
        try:
            data = self.file_processor.load_json(current_file)

            # Display file info
            st.subheader(f"Reviewing: {current_file.name}")

            # Create tabs for different views
            edit_tab, preview_tab, raw_tab = st.tabs(["Edit", "Preview", "Raw"])

            with edit_tab:
                edited_data = self._handle_editing(data, current_file)

            with preview_tab:
                st.json(edited_data)

            with raw_tab:
                st.text(json.dumps(edited_data, indent=2))

            # Action buttons
            self._handle_actions(current_file)

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            logging.exception("Error in file review")

    def _handle_editing(
        self, data: Dict[str, Any], current_file: Path
    ) -> Dict[str, Any]:
        """Handle the editing form for the data"""
        with st.form("edit_form"):
            edited_data = {}

            # Group fields by category if possible
            fields = self._group_fields(data)

            for category, category_fields in fields.items():
                st.subheader(category)
                for key, value in category_fields.items():
                    config = self.data_editor.field_configs.get(key)
                    height = config.height if config else None
                    edited_data[key] = self.data_editor.render_field(key, value, height)

            if st.form_submit_button("Save Changes"):
                self.file_processor.save_json(edited_data, current_file)
                st.success("Changes saved!")
                return edited_data

            return data

    def _group_fields(self, data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Group fields into categories for better organization"""
        groups = {"Content": {}, "Metadata": {}, "Other": {}}

        content_fields = {"article_text", "content", "extracted_quotes"}
        metadata_fields = {"title", "publication_date", "author", "keywords"}

        for key, value in data.items():
            if key in content_fields:
                groups["Content"][key] = value
            elif key in metadata_fields:
                groups["Metadata"][key] = value
            else:
                groups["Other"][key] = value

        return {k: v for k, v in groups.items() if v}

    def _handle_actions(self, current_file: Path):
        """Handle accept/reject actions"""
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Accept", type="primary"):
                self.file_processor.move_file(current_file, FileAction.ACCEPT)
                st.session_state.processed_files.add(current_file.name)
                st.success(f"Moved {current_file.name} to accepted/")
                self._advance_to_next()

        with col2:
            if st.button("Reject", type="secondary"):
                self.file_processor.move_file(current_file, FileAction.REJECT)
                st.session_state.processed_files.add(current_file.name)
                st.success(f"Moved {current_file.name} to rejected/")
                self._advance_to_next()

    def _advance_to_next(self):
        """Advance to the next file if available"""
        files = self.file_processor.get_files()
        if st.session_state.current_index < len(files) - 1:
            st.session_state.current_index += 1
        st.rerun()

    def run(self):
        """Run the main application"""
        self._setup_ui()

        files = self.file_processor.get_files()
        if not files:
            st.warning(
                f"No files matching '{self.config.file_pattern}' "
                f"found in {self.config.input_dir}"
            )
            return

        self._render_sidebar(files)

        # Display current file
        if files:
            current_file = files[st.session_state.current_index]
            self._handle_file_review(current_file)
