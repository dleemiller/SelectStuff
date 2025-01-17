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
        page_title="DuckDB FTS Chat Search",
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
    /* Make the user/assistant icons smaller. 
       The elements have testid="stMessageAvatar" or you can target the SVG. */
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
        input_id = None
        fields = []
        display_column = None
        k_val = 1.2
        b_val = 0.75
        conjunctive_val = False
    else:
        selected_table = st.sidebar.selectbox("Indexed Table", indexed_tables)
        # Fetch the schema for the selected table
        schema = get_table_schema(selected_table) if selected_table else []

        # Find a likely "ID" column
        input_id = None
        if schema:
            inferred_id = next(
                (
                    col["column_name"]
                    for col in schema
                    if col["column_name"].lower() in ["id", "doc_id", "article_id"]
                ),
                schema[0]["column_name"],  # fallback
            )
            input_id = st.sidebar.selectbox("Document ID Column", [inferred_id])

        # Fields to search (toggles)
        st.sidebar.write("**Fields to Search**")
        fields = []
        if selected_table:
            possible_fields = fts_indexes.get(selected_table, [])
            for field in possible_fields:
                toggled = st.sidebar.toggle(field, value=True, key=f"toggle_{field}")
                if toggled:
                    fields.append(field)

        # Choose which column to display in chat
        all_columns = [c["column_name"] for c in schema] if schema else []
        display_column = st.sidebar.selectbox(
            "Display Column (chat response)", all_columns if all_columns else []
        )

        # Advanced search
        with st.sidebar.expander("Advanced Search Options", expanded=False):
            k_val = st.number_input("BM25 k", 0.1, 10.0, 1.2)
            b_val = st.number_input("BM25 b", 0.1, 1.0, 0.75)
            conjunctive_val = st.checkbox("Require All Terms", value=False)

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

                # Infer doc ID for create
                inferred_id_create = next(
                    (
                        col["column_name"]
                        for col in schema_create
                        if col["column_name"].lower() in ["id", "doc_id", "article_id"]
                    ),
                    schema_create[0]["column_name"],
                )
                input_id_create = st.selectbox(
                    "Document ID Column",
                    [col["column_name"] for col in schema_create],
                    index=0,
                )

                # Columns to index
                indexable_columns = [
                    col["column_name"]
                    for col in schema_create
                    if col["column_name"] != input_id_create
                ]
                input_values_create = st.multiselect(
                    "Columns to Index", indexable_columns
                )

                col_a, col_b = st.columns(2)
                with col_a:
                    stemmer = st.selectbox("Stemmer", ["porter", "english", "none"], 0)
                    lower = st.checkbox("Lowercase", True)
                with col_b:
                    stopwords = st.text_input("Stopwords", placeholder="english")
                    strip_accents = st.checkbox("Strip Accents", True)

                overwrite = st.checkbox("Overwrite Existing Index", False)
                if st.button("Create Index"):
                    resp = create_index(
                        fts_table=create_table_sel,
                        input_id=input_id_create,
                        input_values=input_values_create,
                        stemmer=stemmer,
                        stopwords=stopwords or "english",
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
    st.title("DuckDB FTS: Chat-Style Search")

    # Keep all conversation messages in session.
    # Each message is a dict: {"role": "user"|"assistant", "content": str}
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
    if user_query and selected_table and input_id and display_column:
        # 1) User's message
        st.session_state["messages"].append({"role": "user", "content": user_query})

        # 2) Perform the search
        # Build query params
        query_params = {
            "fts_table": selected_table,
            "input_id": input_id,
            "query_string": user_query,
            "fields": fields if fields else None,
            "k": k_val,
            "b": b_val,
            "conjunctive": conjunctive_val,
        }

        resp = query_index(**query_params)  # from fts_utils
        if resp and resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                # Show top result (or all if you like)
                top_row = results[0]
                # Reconstruct columns from schema plus "score"
                col_names = [c["column_name"] for c in schema] if schema else []
                if "score" not in col_names:
                    col_names.append("score")
                row_dict = dict(zip(col_names, top_row))

                # Format the content to show back to user
                display_val = row_dict.get(display_column, "(No content)")
                score_val = row_dict.get("score", 0.0)
                doc_id_val = row_dict.get(input_id, None)

                # Build a text response (you can fancy it up with markdown)
                assistant_text = f"{display_val}\n\n" f"_score: {score_val:.4f}_ | " + (
                    f"    _doc_id: {doc_id_val}_" if doc_id_val else ""
                )
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
