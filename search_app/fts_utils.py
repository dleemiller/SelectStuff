import requests
import streamlit as st
from typing import List, Optional

API_BASE_URL = "http://127.0.0.1:8000"


def get_tables() -> list:
    """Fetches the list of available tables from the backend."""
    try:
        resp = requests.get(f"{API_BASE_URL}/tables")
        resp.raise_for_status()
    except requests.RequestException as e:
        st.error(f"Error fetching tables: {e}")
        return []

    # Adjust if your backend returns a different key (e.g. "tables")
    return resp.json().get("tables", [])


def get_table_schema(table_name: str) -> list:
    """Fetch the schema for a given table."""
    try:
        resp = requests.get(f"{API_BASE_URL}/tables/{table_name}/schema")
        resp.raise_for_status()
    except requests.RequestException as e:
        st.error(f"Error fetching schema for table '{table_name}': {e}")
        return []
    # Adjust if your backend returns a different key
    return resp.json().get("schema", [])


def create_index(fts_table: str, input_values: list, **kwargs) -> requests.Response:
    """Create a fulltext search index for a given table."""
    payload = {
        "fts_table": fts_table,
        "input_values": input_values,
    }
    # Optional fields: stemmer, stopwords, ignore, strip_accents, lower, overwrite
    # are passed via **kwargs
    payload.update(kwargs)

    try:
        return requests.post(f"{API_BASE_URL}/fts/create", json=payload)
    except requests.RequestException as e:
        st.error(f"Error creating index: {e}")
        # Return a dummy response with error code
        return requests.Response()


def query_index(
    fts_table: str,
    query_string: str,
    fields: Optional[List[str]] = None,
    limit: Optional[int] = 1,
) -> requests.Response:
    """Query the fulltext search index for a given query."""
    payload = {
        "fts_table": fts_table,
        "query_string": query_string,
        "limit": limit if limit else 1,
    }
    if fields:
        payload["fields"] = fields

    try:
        return requests.post(f"{API_BASE_URL}/fts/query", json=payload)
    except requests.RequestException as e:
        st.error(f"Error querying index: {e}")
        return requests.Response()


def get_fts_indexes() -> dict:
    """List the existing fulltext indexes on the server."""
    try:
        resp = requests.get(f"{API_BASE_URL}/fts/list")
        resp.raise_for_status()
    except requests.RequestException as e:
        st.error(f"Error fetching FTS indexes: {e}")
        return {}
    # Adjust if your backend returns a different key
    return resp.json().get("indexes", {})


def drop_index(table_name: str) -> requests.Response:
    """Drop the fulltext search index for a specific table."""
    try:
        # The API uses a query param named "fts_table"
        return requests.post(
            f"{API_BASE_URL}/fts/drop", params={"fts_table": table_name}
        )
    except requests.RequestException as e:
        st.error(f"Error dropping index: {e}")
        return requests.Response()
