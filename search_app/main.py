import streamlit as st
import html
from fts_utils import (
    get_fts_indexes,
    get_tables,
    get_table_schema,
    create_index,
    drop_index,
    query_index,
)


def display_assistant_panel(body_text: str, heading: str = "Top Result:"):
    """
    Renders a panel with a bold heading and an escaped, wrapped body text so
    underscores or asterisks won't break formatting.
    """
    # Escape any user/content text so special chars don’t break HTML or Markdown:
    safe_body = html.escape(body_text)

    # Build the panel HTML:
    panel_html = f"""
    <div style="
        background-color: #2b2b2b;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 0.75rem;
    ">
      <!-- Heading Section -->
      <p style="
         font-size: 15px;
         line-height: 1.5em;
         font-weight: bold;
         color: #FAD105; /* or #DDD, your preference */
         margin: 0 0 0.5em 0;
      ">
        {heading}
       </p>
       <p style="margin: 20px; border-radius: 10px; background-color: #444; padding: 10px;">
        {safe_body}
      </p>
    </div>
    """

    # Render the HTML in Streamlit:
    st.markdown(panel_html, unsafe_allow_html=True)


def display_response_as_panel(response_text: str):
    safe_content = html.escape(response_text)
    st.markdown(
        f"""
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
          ">
            {safe_content}
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    # -------------------------
    # 1. Page Config & CSS
    # -------------------------
    st.set_page_config(
        page_title="SQLite FTS Chat Search",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Optional: Hide Streamlit menu & footer:
    st.markdown(
        """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Reduce the size (and overall presence) of the chat icons:
    st.markdown(
        """
        <style>
        /* Make the user/assistant icons smaller. */
        [data-testid="stMessageAvatar"] svg {
            width: 24px !important;
            height: 24px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------
    # 2. SIDEBAR: Controls
    # -------------------------
    st.sidebar.title("Search Controls")

    fts_indexes = get_fts_indexes()  # from fts_utils
    indexed_tables = list(fts_indexes.keys())

    if not indexed_tables:
        st.sidebar.warning("No indexed tables. Create one below.")
        selected_table = None
        schema = []
        fields = []
        display_column = None
        limit_val = 1
    else:
        selected_table = st.sidebar.selectbox("Indexed Table", indexed_tables)
        # Fetch the schema for the selected table
        schema = get_table_schema(selected_table) if selected_table else []

        # Guess a likely "ID" column for display (not used in query payload!)
        if schema:
            inferred_id = next(
                (
                    col["column_name"]
                    for col in schema
                    if col["column_name"].lower() in ["id", "doc_id", "article_id"]
                ),
                schema[0]["column_name"],  # fallback if no standard ID
            )

        # Fields to search
        st.sidebar.write("**Fields to Search**")
        fields = []
        if selected_table:
            possible_fields = fts_indexes.get(selected_table, [])
            for field in possible_fields:
                toggled = st.sidebar.checkbox(field, value=True, key=f"toggle_{field}")
                if toggled:
                    fields.append(field)

        # Choose which column to display in chat
        all_columns = [c["column_name"] for c in schema] if schema else []
        display_column = st.sidebar.selectbox(
            "Display Column (chat response)", all_columns if all_columns else []
        )

        limit_val = st.sidebar.number_input("Number of Rows to Retrieve", 1, 50, 1)

    # -------------------------
    # 3. SIDEBAR: Admin Tools
    # -------------------------
    with st.sidebar.expander("Admin Tools"):
        st.write("**Existing Indexes**")
        if fts_indexes:
            st.json(fts_indexes)
        else:
            st.write("No indexes found.")

        st.write("---")
        st.write("**Create an Index**")
        all_db_tables = get_tables()
        create_table_sel = st.selectbox(
            "Table to Index", all_db_tables, key="create_table_sel"
        )
        if create_table_sel:
            schema_create = get_table_schema(create_table_sel)
            if schema_create:
                if st.checkbox("Show table schema?", key="chk_show_schema"):
                    st.json(schema_create)

                # Columns to index
                input_values_create = st.multiselect(
                    "Columns to Index", [x["column_name"] for x in schema_create]
                )

                col_a, col_b = st.columns(2)
                with col_a:
                    stemmer = st.selectbox("Stemmer", ["porter", "english", "none"], 0)
                    lower = st.checkbox("Lowercase", True)
                with col_b:
                    stopwords = st.text_input("Stopwords", placeholder="english")
                    strip_accents = st.checkbox("Strip Accents", True)

                # If you want to allow a custom ignore regex:
                ignore_pattern = st.text_input(
                    "Ignore Regex (Optional)", "(\\.|[^a-z])+"
                )
                overwrite = st.checkbox("Overwrite Existing Index", False)

                if st.button("Create Index"):
                    resp = create_index(
                        fts_table=create_table_sel,
                        input_values=input_values_create,
                        stemmer=stemmer if stemmer != "none" else None,
                        stopwords=stopwords or None,
                        ignore=ignore_pattern or None,
                        strip_accents=strip_accents,
                        lower=lower,
                        overwrite=overwrite,
                    )
                    if resp.status_code == 200:
                        st.success("Index created successfully!")
                    else:
                        st.error(f"Error creating index: {resp.text}")

        st.write("---")
        st.write("**Drop an Index**")
        if indexed_tables:
            drop_sel = st.selectbox(
                "Indexed Table to Drop", indexed_tables, key="drop_table_sel"
            )
            if st.button("Drop Index"):
                drop_resp = drop_index(drop_sel)
                if drop_resp.status_code == 200:
                    st.success(f"Index on '{drop_sel}' dropped successfully!")
                else:
                    st.error(f"Failed to drop index: {drop_resp.text}")

    # -------------------------------------------
    # 4. MAIN: Chat-like Experience
    # -------------------------------------------
    st.title("Select Stuff Search")

    # Keep all conversation messages in session
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Display existing conversation
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

    # Chat input pinned at bottom
    user_query = st.chat_input("Type your search here...")
    st.session_state["query_text"] = user_query

    if user_query and selected_table and display_column:
        # 1) User's message
        st.session_state["messages"].append({"role": "user", "content": user_query})

        # 2) Perform the search
        query_params = {
            "fts_table": selected_table,
            "query_string": user_query,
            "limit": limit_val if limit_val else 1,
        }
        if fields:
            query_params["fields"] = fields

        resp = query_index(**query_params)
        if resp and resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                # Show top result (or all if you like)
                top_row = results[0]
                # Reconstruct columns from schema plus "score" if the server returns it
                col_names = (
                    ["row_id"] + [c["column_name"] for c in schema] if schema else []
                )
                if "score" not in col_names:
                    col_names.append("score")
                row_dict = dict(zip(col_names, top_row))

                # Format the content to show back to user
                display_val = row_dict.get(display_column, "(No content)")
                score_val = row_dict.get("score", 0.0)
                # doc_id_val is just for display
                # doc_id_val = row_dict.get(input_id, None) if input_id else None
                row_id_val = row_dict.get("row_id", None)

                # Build a text response
                assistant_text = f"{display_val}\n\n" f"_rowid: {row_id_val}_"
            else:
                assistant_text = f"No results found for '{user_query}'."
        else:
            assistant_text = "Search failed or server error."

        # 3) Assistant's message
        st.session_state["messages"].append(
            {"role": "assistant", "content": assistant_text}
        )
        st.rerun()  # Refresh page to show new messages

    # Optional: a button to clear the chat
    if st.button("Clear Chat"):
        st.session_state["messages"] = []
        st.rerun()


if __name__ == "__main__":
    main()
