# fts_utils.py
import requests
import streamlit as st
from typing import List, Optional

# This can be loaded from config if you like, or passed in:
API_BASE_URL = "http://127.0.0.1:8000"


def get_tables() -> list:
    """Fetches the list of available tables from the backend."""
    try:
        resp = requests.get(f"{API_BASE_URL}/tables")
        resp.raise_for_status()
    except requests.RequestException as e:
        st.error(f"Error fetching tables: {e}")
        return []

    return resp.json().get("tables", [])


def get_table_schema(table_name: str) -> list:
    """Fetch the schema for a given table."""
    try:
        resp = requests.get(f"{API_BASE_URL}/tables/{table_name}/schema")
        resp.raise_for_status()
    except requests.RequestException as e:
        st.error(f"Error fetching schema for table '{table_name}': {e}")
        return []
    return resp.json().get("schema", [])


def create_index(
    fts_table: str, input_id: str, input_values: list, **kwargs
) -> requests.Response:
    """Create a fulltext search index for a given table."""
    payload = {
        "fts_table": fts_table,
        "input_id": input_id,
        "input_values": input_values,
    }
    payload.update(kwargs)
    try:
        return requests.post(f"{API_BASE_URL}/fts/create", json=payload)
    except requests.RequestException as e:
        st.error(f"Error creating index: {e}")
        # Return a dummy response with error code
        return requests.Response()


def query_index(
    fts_table: str, input_id: str, query_string: str, **kwargs
) -> requests.Response:
    """Query the fulltext search index for a given query."""
    payload = {
        "fts_table": fts_table,
        "input_id": input_id,
        "query_string": query_string,
    }
    payload.update(kwargs)

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
    return resp.json().get("indexes", {})


def drop_index(table_name: str) -> requests.Response:
    """Drop the fulltext search index for a specific table."""
    try:
        return requests.post(f"{API_BASE_URL}/fts/drop", json={"fts_table": table_name})
    except requests.RequestException as e:
        st.error(f"Error dropping index: {e}")
        return requests.Response()
