"""
Streamlit Application for Multi-App Full-Text Search

This app supports multiple applications by loading the list of enabled apps from an
environment variable (ENABLED_APPS) and then allowing the user to select one.
Once an app is selected, the UI displays:
  - Search Controls (e.g. available tables, fields to search, etc.)
  - Admin Tools for viewing, creating, and dropping FTS indexes
  - A chat-style interface for running full-text search queries

All API calls are made to namespaced endpoints (e.g. /v1/{app}/db/...) so that
each application uses its own database configuration.
"""

import os
import html
import streamlit as st

# 1. Import the shared logger configuration
from stuff.shared.logging_config import configure_logging, get_logger

# 2. Import utility functions for interacting with the FastAPI backend.
#    These functions expect an "app" parameter to use namespaced endpoints.
from stuff.ui.utils.fts_utils import (
    get_tables,
    get_table_schema,
    get_fts_indexes,
    create_index,
    query_index,
    drop_index,
)

from stuff.ui.utils.trace_utils import TracingSession

session = TracingSession()
# ---------------------------------------------------
# Configure Structured Logging for Streamlit
# ---------------------------------------------------
configure_logging("streamlit")
logger = get_logger("streamlit")
logger.info("streamlit_app started")


def display_assistant_panel(body_text: str, heading: str = "Top Result:"):
    """
    Renders a panel with a bold heading and escaped body text.

    This panel is used to display the assistant's response.
    """
    safe_body = html.escape(body_text)
    panel_html = f"""
    <div style="
        background-color: #2b2b2b;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 0.75rem;
    ">
      <p style="
         font-size: 15px;
         line-height: 1.5em;
         font-weight: bold;
         color: #FAD105;
         margin: 0 0 0.5em 0;
      ">{heading}</p>
      <p style="
         margin: 20px;
         border-radius: 10px;
         background-color: #444;
         padding: 10px;
      ">{safe_body}</p>
    </div>
    """
    st.markdown(panel_html, unsafe_allow_html=True)


def display_response_as_panel(response_text: str):
    """
    Renders a panel to display user messages or responses.
    """
    safe_content = html.escape(response_text)
    panel_html = f"""
    <div style="
      background-color: #2b2b2b;
      padding: 1rem;
      border-radius: 6px;
      margin-bottom: 0.75rem;
    ">
      <p style="
         font-size: 14px;
         line-height: 1.5em;
         color: #DDD;
         white-space: pre-wrap;
         word-wrap: break-word;
         margin: 0;
      ">{safe_content}</p>
    </div>
    """
    st.markdown(panel_html, unsafe_allow_html=True)


def clear_chat():
    """
    Clears the conversation history and forces a rerun so that the chat area updates.
    """
    st.session_state["messages"] = []
    st.rerun()


def main():
    """
    Main function to run the multi-app FTS Streamlit interface.

    Loads the enabled apps from the environment variable, provides a sidebar to select
    an application and various operations (view tables, view schema, create/drop index,
    query search, etc.), and displays a chat-like conversation for full-text search.
    """
    # ---------------------------------------------------
    # 1. Page & Style Config
    # ---------------------------------------------------
    st.set_page_config(
        page_title="Select Stuff Search",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        div[data-testid="stStatusWidget"] {visibility: hidden;}
        footer {visibility: hidden;}
        [data-testid="stMessageAvatar"] svg {
            width: 24px !important;
            height: 24px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------
    # 2. Enabled Apps & Sidebar Configuration
    # ---------------------------------------------------
    enabled_apps_env = os.environ.get("ENABLED_APPS", "news")
    enabled_apps = [app.strip() for app in enabled_apps_env.split(",") if app.strip()]

    st.sidebar.title("Application Selector")
    selected_app = st.sidebar.selectbox("Select Application", enabled_apps)

    st.sidebar.title("Search Controls")
    # Fetch FTS indexes for the selected app
    fts_indexes = get_fts_indexes(app=selected_app)
    indexed_tables = list(fts_indexes.keys()) if fts_indexes else []

    # ---------------------------------------------------
    # 3. Handle Indexed Tables & Field Selection
    # ---------------------------------------------------
    if not indexed_tables:
        st.sidebar.warning("No indexed tables found. Please create one in Admin Tools.")
        selected_table = None
        schema = []
        fields = []
        display_column = None
        limit_val = 1
    else:
        selected_table = st.sidebar.selectbox("Indexed Table", indexed_tables)

        schema = (
            get_table_schema(selected_table, app=selected_app) if selected_table else []
        )
        all_columns = [c["column_name"] for c in schema] if schema else []
        display_column = (
            st.sidebar.selectbox("Display Column (chat response)", all_columns)
            if all_columns
            else None
        )

        # Number of rows to retrieve from FTS query
        limit_val = st.sidebar.number_input("Number of Rows to Retrieve", 1, 50, 1)

        # Let the user select which fields to search (restoring the toggles).
        st.sidebar.write("**Fields to Search**")
        fields = []
        # If the user wants to toggle fields for a given indexed table:
        if selected_table in fts_indexes:
            possible_fields = fts_indexes[selected_table]
            for field in possible_fields:
                toggled = st.sidebar.checkbox(field, value=True, key=f"toggle_{field}")
                if toggled:
                    fields.append(field)
        else:
            # If there's an edge case where the table isn't in the dict,
            # 'possible_fields' won't exist, so we skip
            pass

    # ---------------------------------------------------
    # 4. Admin Tools (Index Creation, Dropping)
    # ---------------------------------------------------
    with st.sidebar.expander("Admin Tools"):
        st.write("**Existing FTS Indexes**")
        if fts_indexes:
            st.json(fts_indexes)
        else:
            st.write("No indexes found.")

        st.write("---")
        st.write("**Create an Index**")
        all_db_tables = get_tables(app=selected_app)
        create_table_sel = st.selectbox(
            "Table to Index", all_db_tables, key="create_table_sel"
        )
        if create_table_sel:
            schema_create = get_table_schema(create_table_sel, app=selected_app)
            if schema_create:
                if st.checkbox("Show table schema?", key="chk_show_schema"):
                    st.json(schema_create)

                input_values_create = st.multiselect(
                    "Columns to Index", [x["column_name"] for x in schema_create]
                )

                col_a, col_b = st.columns(2)
                with col_a:
                    stemmer = st.selectbox(
                        "Stemmer", ["porter", "english", "none"], index=0
                    )
                    lower = st.checkbox("Lowercase", value=True)
                with col_b:
                    stopwords = st.text_input("Stopwords", placeholder="english")
                    strip_accents = st.checkbox("Strip Accents", value=True)

                ignore_pattern = st.text_input(
                    "Ignore Regex (Optional)", r"(\.|[^a-z])+"
                )
                overwrite = st.checkbox("Overwrite Existing Index", value=False)

                if st.button("Create Index"):
                    logger.info(
                        "admin.create_index.clicked",
                        table=create_table_sel,
                        columns=input_values_create,
                    )
                    resp = create_index(
                        fts_table=create_table_sel,
                        input_values=input_values_create,
                        app=selected_app,
                        stemmer=stemmer if stemmer != "none" else None,
                        stopwords=stopwords or None,
                        ignore=ignore_pattern or None,
                        strip_accents=strip_accents,
                        lower=lower,
                        overwrite=overwrite,
                    )
                    if resp.status_code == 200:
                        st.success("Index created successfully!")
                        logger.info(
                            "admin.create_index.success", table=create_table_sel
                        )
                    else:
                        st.error(f"Error creating index: {resp.text}")
                        logger.error("admin.create_index.failed", error=resp.text)
            else:
                st.info("No schema available for the selected table.")

        st.write("---")
        st.write("**Drop an Index**")
        if indexed_tables:
            drop_sel = st.selectbox(
                "Select Index to Drop", indexed_tables, key="drop_table_sel"
            )
            if st.button("Drop Index"):
                logger.info("admin.drop_index.clicked", table=drop_sel)
                drop_resp = drop_index(drop_sel, app=selected_app)
                if drop_resp.status_code == 200:
                    st.success(f"Index on '{drop_sel}' dropped successfully!")
                    logger.info("admin.drop_index.success", table=drop_sel)
                else:
                    st.error(f"Failed to drop index: {drop_resp.text}")
                    logger.error("admin.drop_index.failed", error=drop_resp.text)

    # ---------------------------------------------------
    # 5. Chat-Style Search Experience
    # ---------------------------------------------------
    st.title("Select Stuff Search")

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Display past messages
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            with st.chat_message("user"):
                display_response_as_panel(msg["content"])
        else:
            with st.chat_message("assistant"):
                query_text = st.session_state.get("query_text")
                heading = (
                    f"Top result for: {query_text}" if query_text else "Top result:"
                )
                display_assistant_panel(msg["content"], heading=heading)

    # Chat input
    user_query = st.chat_input("Type your search here...")
    st.session_state["query_text"] = user_query

    # Process new user query
    if user_query and selected_table and display_column:
        logger.info("chat.user_query_submitted", query=user_query, table=selected_table)

        # Add user message
        st.session_state["messages"].append({"role": "user", "content": user_query})

        # Prepare FTS query
        query_params = {
            "fts_table": selected_table,
            "query_string": user_query,
            "limit": limit_val if limit_val else 1,
        }

        # If the user toggled specific fields to search, include them
        if fields:
            query_params["fields"] = fields

        # Execute the query
        resp = query_index(app=selected_app, **query_params)
        if resp and resp.status_code == 200:
            logger.info("chat.query_index.success", query=user_query)
            results = resp.json().get("results", [])
            if results:
                # Take the first row as top result
                top_row = results[0]
                if schema:
                    col_names = ["rowid"] + [c["column_name"] for c in schema]
                    if "score" not in col_names:
                        col_names.append("score")
                    row_dict = dict(zip(col_names, top_row))
                    display_val = row_dict.get(display_column, "(No content)")
                    row_id_val = row_dict.get("rowid", None)
                    assistant_text = f"{display_val}\n\n_rowid: {row_id_val}_"
                else:
                    assistant_text = str(top_row)
            else:
                assistant_text = f"No results found for '{user_query}'."
        else:
            assistant_text = "Search failed or server error."
            logger.error(
                "chat.query_index.failed",
                query=user_query,
                status=resp.status_code if resp else "No response",
            )

        # Add assistant message
        st.session_state["messages"].append(
            {"role": "assistant", "content": assistant_text}
        )
        st.rerun()

    # Button to clear chat
    st.button("Clear Chat", on_click=clear_chat, key="clear_chat_btn")


if __name__ == "__main__":
    main()
