import streamlit as st
import requests

API_BASE_URL = "http://127.0.0.1:8000"  # Replace with your FastAPI base URL


def get_tables():
    response = requests.get(f"{API_BASE_URL}/tables")
    if response.status_code == 200:
        return response.json().get("tables", [])
    st.error("Failed to fetch tables.")
    return []


def get_table_schema(table_name):
    response = requests.get(f"{API_BASE_URL}/tables/{table_name}/schema")
    if response.status_code == 200:
        return response.json().get("schema", [])
    st.error(f"Failed to fetch schema for table '{table_name}'.")
    return []


def create_index(input_table, input_id, input_values, **kwargs):
    payload = {
        "input_table": input_table,
        "input_id": input_id,
        "input_values": input_values,
    }
    payload.update(kwargs)
    response = requests.post(f"{API_BASE_URL}/fts/create", json=payload)
    return response


def query_index(input_table, input_id, query_string, **kwargs):
    payload = {
        "input_table": input_table,
        "input_id": input_id,
        "query_string": query_string,
    }
    payload.update(kwargs)
    response = requests.post(f"{API_BASE_URL}/fts/query", json=payload)
    return response


def get_fts_indexes():
    response = requests.get(f"{API_BASE_URL}/fts/list")
    if response.status_code == 200:
        return response.json().get("indexes", {})
    st.error("Failed to fetch FTS indexes.")
    return {}


def drop_index(table_name):
    response = requests.post(
        f"{API_BASE_URL}/fts/drop", json={"input_table": table_name}
    )
    return response


def main():
    # Configure the page to use a "wide" layout with minimal overhead
    st.set_page_config(
        page_title="DuckDB FTS",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 1. Minimal top-level heading to reduce vertical space
    st.subheader("DuckDB Full-Text Search")

    # -- Left Sidebar for Searching + Administration --
    st.sidebar.title("Search")

    # Pre-fetch indexes for query use
    fts_indexes = get_fts_indexes()
    indexed_tables = list(fts_indexes.keys())

    if not indexed_tables:
        st.sidebar.warning("No indexed tables found. Create one in 'Admin Tools'.")
        selected_table = None
    else:
        # Table + Document ID
        selected_table = st.sidebar.selectbox("Indexed Table", indexed_tables)
        schema = get_table_schema(selected_table) if selected_table else []
        if schema:
            # Infer Document ID Column
            inferred_id = next(
                (
                    col["column_name"]
                    for col in schema
                    if col["column_name"].lower() in ["id", "doc_id", "article_id"]
                ),
                schema[0]["column_name"] if schema else None,
            )
            input_id = st.sidebar.selectbox(
                "Document ID Column",
                [inferred_id] if inferred_id else [],
            )
        else:
            input_id = None

        # Choose which fields to search (optional)
        indexed_fields = fts_indexes.get(selected_table, []) if selected_table else []
        fields = st.sidebar.multiselect("Fields to Search (Optional)", indexed_fields)

        with st.sidebar.expander("Advanced Search Options", expanded=False):
            k = st.number_input("BM25 k", min_value=0.1, max_value=10.0, value=1.2)
            b = st.number_input("BM25 b", min_value=0.1, max_value=1.0, value=0.75)
            conjunctive = st.checkbox("Require All Query Terms", value=False)

    # -- ADMIN EXPANDER IN THE SIDEBAR --
    with st.sidebar.expander("Admin Tools"):
        # 1. Explore
        fts_indexes_current = get_fts_indexes()
        if fts_indexes_current:
            st.write("Existing Indexes:")
            st.json(fts_indexes_current)
        else:
            st.write("No indexes available.")

        # 2. Create Index
        st.write("**Create Index**")
        all_tables = get_tables()
        create_table_sel = st.selectbox(
            "Table to Index", all_tables, key="create_table_sel"
        )
        if create_table_sel:
            schema_create = get_table_schema(create_table_sel)
            if schema_create:
                # We won't show the entire schema by default, just a button:
                if st.checkbox("Show table schema?"):
                    st.json(schema_create)

                # Infer doc ID
                inferred_id_create = next(
                    (
                        col["column_name"]
                        for col in schema_create
                        if col["column_name"].lower() in ["id", "doc_id", "article_id"]
                    ),
                    schema_create[0]["column_name"] if schema_create else None,
                )
                input_id_create = st.selectbox(
                    "Document ID Column",
                    [col["column_name"] for col in schema_create],
                    index=0 if inferred_id_create else -1,
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

                # Additional FTS options
                st.write("**Additional Options**")
                col_a, col_b = st.columns(2)
                with col_a:
                    stemmer = st.selectbox(
                        "Stemmer", ["porter", "english", "none"], index=0
                    )
                    lower = st.checkbox("Lowercase", value=True)
                with col_b:
                    stopwords = st.text_input(
                        "Stopwords", placeholder="Default is 'english'"
                    )
                    strip_accents = st.checkbox("Strip Accents", value=True)

                overwrite = st.checkbox("Overwrite Existing Index", value=False)

                # Create Index Button
                if st.button("Create Index"):
                    resp = create_index(
                        input_table=create_table_sel,
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
                        st.error(f"Error creating index: {resp.json()}")

        # 3. Drop Index
        st.write("**Drop Index**")
        if indexed_tables:
            drop_sel = st.selectbox(
                "Drop from Indexed Table", indexed_tables, key="drop_sel"
            )
            if st.button("Drop Selected Index"):
                drop_resp = drop_index(drop_sel)
                if drop_resp.status_code == 200:
                    st.success("Index dropped successfully!")
                else:
                    st.error(f"Failed to drop index: {drop_resp.json()}")

    # -- MAIN BODY: Chat interface occupies the rest of the page --
    if selected_table and input_id:
        # Minimal label
        st.write("## Chat-Style Search")

        # Maintain a conversation in session state
        if "messages" not in st.session_state:
            st.session_state["messages"] = []

        # Display existing conversation
        for msg in st.session_state["messages"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # Chat input area at the bottom
        user_input = st.chat_input("Enter your search query")
        if user_input:
            # Show user message
            st.session_state["messages"].append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.write(user_input)

            # Perform the FTS query
            payload = {
                "input_table": selected_table,
                "input_id": input_id,
                "query_string": user_input,
            }
            if fields:
                payload["fields"] = fields
            if "k" in locals():
                payload["k"] = k
            if "b" in locals():
                payload["b"] = b
            if "conjunctive" in locals():
                payload["conjunctive"] = conjunctive

            resp = requests.post(f"{API_BASE_URL}/fts/query", json=payload)
            if resp.status_code == 200:
                # Suppose API returns { "text": "..." }
                text_result = resp.json().get("text", "")
                st.session_state["messages"].append(
                    {"role": "assistant", "content": text_result}
                )
                with st.chat_message("assistant"):
                    st.write(text_result)
            else:
                error_msg = f"Failed to query index: {resp.json()}"
                st.session_state["messages"].append(
                    {"role": "assistant", "content": error_msg}
                )
                with st.chat_message("assistant"):
                    st.write(error_msg)

    else:
        st.info("Select a table and document ID in the sidebar to begin searching.")


if __name__ == "__main__":
    main()
