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


def main():
    st.title("DuckDB Full-Text Search Manager")

    # Sidebar for navigation
    st.sidebar.title("Actions")
    menu = st.sidebar.radio(
        "Select an Action", ["Explore", "Create Index", "Query Index", "Drop Index"]
    )

    fts_indexes = get_fts_indexes()
    indexed_tables = list(fts_indexes.keys())

    if menu == "Explore":
        st.subheader("Explore FTS Indexes")
        if fts_indexes:
            st.write("Available Indexes:")
            st.json(fts_indexes)
        else:
            st.info("No indexes available.")

    elif menu == "Create Index":
        st.subheader("Create a Full-Text Search Index")

        # Fetch list of tables
        tables = get_tables()
        selected_table = st.selectbox("Select Table", tables)

        if selected_table:
            # Fetch table schema
            schema = get_table_schema(selected_table)
            if schema:
                st.write("Table Schema:")
                st.json(schema)

                # Infer Document ID Column
                inferred_id = next(
                    (
                        col["column_name"]
                        for col in schema
                        if col["column_name"].lower() in ["id", "doc_id", "article_id"]
                    ),
                    schema[0]["column_name"] if schema else None,
                )
                input_id = st.selectbox(
                    "Document ID Column",
                    [col["column_name"] for col in schema],
                    index=0 if inferred_id else -1,
                )

                # Select columns to index (exclude the Document ID column)
                indexable_columns = [
                    col["column_name"]
                    for col in schema
                    if col["column_name"] != input_id
                ]
                input_values = st.multiselect("Columns to Index", indexable_columns)

                # FTS options
                stemmer = st.selectbox(
                    "Stemmer", ["porter", "english", "none"], index=0
                )
                stopwords = st.text_input(
                    "Stopwords (leave blank for 'english')", placeholder="e.g., none"
                )
                strip_accents = st.checkbox("Strip Accents", value=True)
                lower = st.checkbox("Convert to Lowercase", value=True)
                overwrite = st.checkbox("Overwrite Existing Index", value=False)

                # Trigger FTS index creation
                if st.button("Create Index"):
                    response = create_index(
                        input_table=selected_table,
                        input_id=input_id,
                        input_values=input_values,
                        stemmer=stemmer,
                        stopwords=stopwords or "english",
                        strip_accents=strip_accents,
                        lower=lower,
                        overwrite=overwrite,
                    )
                    if response.status_code == 200:
                        st.success("FTS index created successfully!")
                    else:
                        st.error(f"Failed to create index: {response.json()}")

    elif menu == "Query Index":
        st.subheader("Query a Full-Text Search Index")

        # Fetch indexed tables
        fts_indexes = get_fts_indexes()
        indexed_tables = list(fts_indexes.keys())

        if not indexed_tables:
            st.warning("No indexed tables available for querying.")
            return

        selected_table = st.selectbox("Select Indexed Table", indexed_tables)
        if selected_table:
            # Fetch indexed fields and table schema
            indexed_fields = fts_indexes[selected_table]
            schema = get_table_schema(selected_table)

            # Infer Document ID Column from table schema
            inferred_id = next(
                (
                    col["column_name"]
                    for col in schema
                    if col["column_name"].lower() in ["id", "doc_id", "article_id"]
                ),
                schema[0]["column_name"] if schema else None,
            )
            input_id = st.selectbox(
                "Document ID Column", [inferred_id] if inferred_id else []
            )

            # Allow search over indexed fields only
            st.write(f"Indexed Fields: {', '.join(indexed_fields)}")
            query_string = st.text_input(
                "Query String", placeholder="Enter search terms"
            )
            fields = st.multiselect("Fields to Search (optional)", indexed_fields)
            k = st.number_input(
                "BM25 k Parameter", min_value=0.1, max_value=10.0, value=1.2
            )
            b = st.number_input(
                "BM25 b Parameter", min_value=0.1, max_value=1.0, value=0.75
            )
            conjunctive = st.checkbox("Require All Query Terms", value=False)

            # Trigger FTS query
            if st.button("Search"):
                response = query_index(
                    input_table=selected_table,
                    input_id=input_id,
                    query_string=query_string,
                    fields=fields if fields else None,
                    k=k,
                    b=b,
                    conjunctive=conjunctive,
                )
                if response.status_code == 200:
                    results = response.json()
                    st.write("Query Results:")
                    st.write(results)
                else:
                    st.error(f"Failed to query index: {response.json()}")

    elif menu == "Drop Index":
        st.subheader("Drop a Full-Text Search Index")

        if not indexed_tables:
            st.warning("No indexed tables available for dropping.")
            return

        selected_table = st.selectbox("Select Indexed Table", indexed_tables)

        if st.button("Drop Index"):
            response = requests.post(
                f"{API_BASE_URL}/fts/drop", json={"input_table": selected_table}
            )
            if response.status_code == 200:
                st.success("Index dropped successfully!")
            else:
                st.error(f"Failed to drop index: {response.json()}")


if __name__ == "__main__":
    main()
