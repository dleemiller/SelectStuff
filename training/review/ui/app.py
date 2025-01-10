import streamlit as st
from pathlib import Path
from typing import Dict, Any, List
import random
import logging
import json

from ..core.file_processor import FileProcessor
from ..core.data_editor import DataEditor
from ..core.types import FileAction
from ..config import AppConfig


class JSONReviewApp:
    """Main application class for the JSON Review Tool"""

    __version__ = "0.1"

    def __init__(self, config: AppConfig):
        self.config = config
        self.file_processor = FileProcessor(config)
        self.data_editor = DataEditor()

    def _setup_ui(self):
        """Configure the Streamlit UI"""
        st.set_page_config(
            page_title=self.config.app_title,
            layout="wide" if self.config.wide_mode else "centered",
            initial_sidebar_state="expanded",
            menu_items={
                "About": f"JSON Review Tool v{self.__version__}",
                "Report a bug": "https://github.com/yourusername/json-review/issues",
            },
        )

    def _render_sidebar(self, input_dir: Path, accepted_dir: Path, rejected_dir: Path):
        """Render the sidebar with statistics"""
        accepted_files = len(list(accepted_dir.glob("*.json")))
        rejected_files = len(list(rejected_dir.glob("*.json")))
        remaining_files = len(list(input_dir.glob("*.json")))

        # Total files is the sum of accepted, rejected, and remaining
        total_files = accepted_files + rejected_files + remaining_files

        with st.sidebar:
            st.header("Statistics")
            st.write(f"Total files: {total_files}")
            st.write(f"Accepted: {accepted_files}")
            st.write(f"Rejected: {rejected_files}")
            st.write(f"Remaining: {remaining_files}")

    def _random_file(self, input_dir: Path) -> Path:
        """Randomly pick a file from the input directory"""
        files = list(input_dir.glob("*.json"))
        if not files:
            return None
        return random.choice(files)

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
        edited_data = {}

        with st.form(f"edit_form_{current_file.name}"):
            fields = self._group_fields(data)

            for category, category_fields in fields.items():
                st.subheader(category)
                for key, value in category_fields.items():
                    edited_data[key] = self.data_editor.render_field(key, value)

            submitted = st.form_submit_button("Save Changes", type="primary")

            if submitted:
                try:
                    self.file_processor.save_json(edited_data, current_file)
                    st.success("Changes saved successfully!")
                    return edited_data
                except Exception as e:
                    st.error(f"Error saving changes: {str(e)}")
                    return data

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
                try:
                    self.file_processor.move_file(current_file, FileAction.ACCEPT)
                    st.success(f"Moved {current_file.name} to accepted/")
                    del st.session_state.current_file  # Clear the current file
                    st.rerun()
                except Exception as e:
                    st.error(f"Error accepting file: {str(e)}")

        with col2:
            if st.button("Reject", type="secondary"):
                try:
                    self.file_processor.move_file(current_file, FileAction.REJECT)
                    st.success(f"Moved {current_file.name} to rejected/")
                    del st.session_state.current_file  # Clear the current file
                    st.rerun()
                except Exception as e:
                    st.error(f"Error rejecting file: {str(e)}")

    def run(self):
        """Run the main application"""
        self._setup_ui()

        input_dir = Path(self.config.input_dir)
        accepted_dir = Path(self.config.accepted_dir)
        rejected_dir = Path(self.config.rejected_dir)

        # Render the sidebar
        self._render_sidebar(input_dir, accepted_dir, rejected_dir)

        # Get a random file or use the one stored in session state
        if (
            "current_file" not in st.session_state
            or not st.session_state.current_file.exists()
        ):
            current_file = self._random_file(input_dir)
            if current_file:
                st.session_state.current_file = current_file
            else:
                st.info("No files left to review.")
                return

        # Review the file stored in session state
        current_file = st.session_state.current_file
        self._handle_file_review(current_file)
