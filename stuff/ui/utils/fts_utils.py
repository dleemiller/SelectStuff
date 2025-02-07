"""
Utility functions for interacting with the FastAPI backend.

This module defines functions to fetch tables, table schemas, full-text search
indexes, and to create, query, or drop FTS indexes for a given application.
Additionally, aggregator functions are provided to fetch data for all enabled apps.
"""

import requests
import streamlit as st
from typing import Optional
from .trace_utils import tracing_session
import os
# Base URL for your FastAPI server.
API_BASE_URL = os.getenv("API_BASE_URL", "http://fastapi-app:8000")


def get_tables(app: str) -> list[str]:
    """
    Fetches the list of available tables from the backend for a given application.

    Args:
        app (str): The application identifier (e.g. "news" or "blog").

    Returns:
        list[str]: A list of table names.
    """
    try:
        resp = tracing_session.get(f"{API_BASE_URL}/v1/{app}/db/tables")
        resp.raise_for_status()
    except requests.RequestException as e:
        st.error(f"Error fetching tables for app '{app}': {e}")
        return []
    return resp.json().get("tables", [])


def get_all_tables(enabled_apps: list[str]) -> dict[str, list[str]]:
    """
    Aggregates the list of available tables for all enabled applications.

    Args:
        enabled_apps (list[str]): A list of application identifiers.

    Returns:
        dict[str, list[str]]: A dictionary mapping each app to its list of tables.
    """
    aggregated = {}
    for app in enabled_apps:
        aggregated[app] = get_tables(app)
    return aggregated


def get_table_schema(table_name: str, app: str) -> list[dict]:
    """
    Fetches the schema for a given table from the backend for a specified application.

    Args:
        table_name (str): The name of the table.
        app (str): The application identifier.

    Returns:
        list[dict]: The schema of the table as a list of dictionaries.
    """
    try:
        resp = tracing_session.get(
            f"{API_BASE_URL}/v1/{app}/db/tables/{table_name}/schema"
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        st.error(f"Error fetching schema for table '{table_name}' in app '{app}': {e}")
        return []
    return resp.json().get("schema", [])


def get_fts_indexes(app: str) -> dict:
    """
    Fetches the full-text search indexes from the backend for a given application.

    Args:
        app (str): The application identifier.

    Returns:
        dict: A dictionary of full-text search indexes.
    """
    try:
        resp = tracing_session.get(f"{API_BASE_URL}/v1/{app}/db/fts/list")
        resp.raise_for_status()
    except requests.RequestException as e:
        st.error(f"Error fetching FTS indexes for app '{app}': {e}")
        return {}
    return resp.json().get("indexes", {})


def get_all_fts_indexes(enabled_apps: list[str]) -> dict[str, dict]:
    """
    Aggregates the full-text search indexes for all enabled applications.

    Args:
        enabled_apps (list[str]): A list of application identifiers.

    Returns:
        dict[str, dict]: A dictionary mapping each app to its FTS indexes.
    """
    aggregated = {}
    for app in enabled_apps:
        aggregated[app] = get_fts_indexes(app)
    return aggregated


def create_index(
    fts_table: str, input_values: list[str], app: str, **kwargs
) -> requests.Response:
    """
    Creates a full-text search index for a given table in a specified application.

    Args:
        fts_table (str): The name of the table to index.
        input_values (list[str]): list of columns to include in the index.
        app (str): The application identifier.
        **kwargs: Additional optional parameters (e.g., stemmer, stopwords).

    Returns:
        requests.Response: The HTTP response from the backend.
    """
    payload = {
        "fts_table": fts_table,
        "input_values": input_values,
    }
    payload.update(kwargs)
    try:
        return tracing_session.post(
            f"{API_BASE_URL}/v1/{app}/db/fts/create", json=payload
        )
    except requests.RequestException as e:
        st.error(f"Error creating index for app '{app}': {e}")
        return requests.Response()


def query_index(
    fts_table: str,
    query_string: str,
    app: str,
    fields: Optional[list[str]] = None,
    limit: Optional[int] = 1,
) -> requests.Response:
    """
    Queries the full-text search index for a given table in a specified application.

    Args:
        fts_table (str): The table to search.
        query_string (str): The search query.
        app (str): The application identifier.
        fields (Optional[list[str]]): Specific fields to search.
        limit (Optional[int]): The maximum number of results (default is 1).

    Returns:
        requests.Response: The HTTP response from the backend.
    """
    payload = {
        "fts_table": fts_table,
        "query_string": query_string,
        "limit": limit if limit else 1,
    }
    if fields:
        payload["fields"] = fields
    try:
        return tracing_session.post(
            f"{API_BASE_URL}/v1/{app}/db/fts/query", json=payload
        )
    except requests.RequestException as e:
        st.error(f"Error querying index for app '{app}': {e}")
        return requests.Response()


def drop_index(fts_table: str, app: str) -> requests.Response:
    """
    Drops the full-text search index for a specified table in a given application.

    Args:
        fts_table (str): The table whose index should be dropped.
        app (str): The application identifier.

    Returns:
        requests.Response: The HTTP response from the backend.
    """
    try:
        return tracing_session.post(
            f"{API_BASE_URL}/v1/{app}/db/fts/drop", params={"fts_table": fts_table}
        )
    except requests.RequestException as e:
        st.error(f"Error dropping index for app '{app}': {e}")
        return requests.Response()
