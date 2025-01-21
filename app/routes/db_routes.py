"""Database operations and full-text search routes.

This module provides FastAPI routes for database operations including:
- Table listing
- Query execution
- Natural language search
- Full-text search index management
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional

from app.database import SQLiteManager
from app.models.db_models import (
    ExecuteQueryRequest,
    SearchRequest,
    CreateFTSIndexRequest,
    QueryFTSIndexRequest,
)


def get_db_manager(request: Request) -> SQLiteManager:
    """Get the SQLite manager instance from the application state.

    Args:
        request: FastAPI request object containing application state.

    Returns:
        SQLiteManager: Instance of the database manager.
    """
    return request.app.state.db_manager


router = APIRouter()


@router.get("/tables")
def get_tables(db_manager: SQLiteManager = Depends(get_db_manager)) -> dict:
    """List all tables in the database.

    Args:
        db_manager: Database manager instance (injected dependency).

    Returns:
        dict: Dictionary containing list of table names.

    Raises:
        HTTPException: If table retrieval fails.
    """
    try:
        query = """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
        """
        rows = db_manager.connection.execute(query).fetchall()
        tables = [r[0] for r in rows]
        return {"tables": tables}
    except Exception as e:
        logging.error(f"Error retrieving tables: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tables.")


@router.get(
    "/tables/{table_name}/schema",
    summary="Get Table Schema",
    description="Retrieve the schema of a specific table.",
)
def get_table_schema(
    table_name: str, db_manager: SQLiteManager = Depends(get_db_manager)
):
    """
    Retrieve the schema of a specific table.

    Args:
        table_name (str): Name of the table.
        db_manager (SQLiteManager): Injected database manager instance.

    Returns:
        dict: Dictionary containing column names and types.

    Raises:
        HTTPException: If schema retrieval fails.
    """
    try:
        query = f"PRAGMA table_info({table_name});"
        results = db_manager.connection.execute(query).fetchall()
        schema = [{"column_name": row[1], "type": row[2]} for row in results]
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve schema for table '{table_name}': {e}",
        )


@router.post("/query")
def query(
    request: ExecuteQueryRequest, db_manager: SQLiteManager = Depends(get_db_manager)
) -> dict:
    """Execute a read-only SQL query.

    Args:
        request: Query execution request containing SQL statement.
        db_manager: Database manager instance (injected dependency).

    Returns:
        dict: Dictionary containing query results.

    Raises:
        HTTPException: If query execution fails.
    """
    try:
        results = db_manager.connection.execute(request.query).fetchall()
        return {"results": results}
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        raise HTTPException(status_code=400, detail="Failed to execute query.")


@router.post("/fts/create")
def create_fts_index(
    request: CreateFTSIndexRequest, db_manager: SQLiteManager = Depends(get_db_manager)
) -> dict:
    """Create a full-text search index for specified table and columns.

    Args:
        request: Index creation request with table and configuration details.
        db_manager: Database manager instance (injected dependency).

    Returns:
        dict: Success message.

    Raises:
        HTTPException: If index creation fails.
    """
    try:
        db_manager.create_fts_index(
            fts_table=request.fts_table + "_fts",
            columns=request.input_values,
            content_table=request.fts_table,
            overwrite=request.overwrite,
        )
        return {"message": f"FTS index created for table '{request.fts_table}'."}
    except Exception as e:
        logging.error(f"Error creating FTS index: {e}")
        raise HTTPException(status_code=500, detail="Failed to create FTS index.")


@router.post("/fts/query")
def query_fts_index(
    request: QueryFTSIndexRequest, db_manager: SQLiteManager = Depends(get_db_manager)
) -> dict:
    """Query a full-text search index.

    Args:
        request: Search request with query string and configuration.
        db_manager: Database manager instance (injected dependency).

    Returns:
        dict: Dictionary containing search results.

    Raises:
        HTTPException: If search query fails.
    """
    try:
        results = db_manager.search_fts(
            fts_table=request.fts_table,
            query_string=request.query_string,
            columns=request.fields,
            limit=request.limit,
        )
        return {"results": results}
    except Exception as e:
        logging.error(f"Error querying FTS index: {e}")
        raise HTTPException(status_code=500, detail="Failed to query FTS index.")


@router.post("/fts/update")
def update_fts_index(
    table_name: str,
    fts_table_name: Optional[str] = None,
    db_manager: SQLiteManager = Depends(get_db_manager),
) -> dict:
    """Update the full-text search index for new rows added to the table.

    Args:
        table_name (str): Name of the main table containing new rows.
        fts_table_name (Optional[str]): Name of the FTS table. Defaults to table_name + '_fts'.
        db_manager (SQLiteManager): Database manager instance (injected dependency).

    Returns:
        dict: Success message with the number of rows added to the index.

    Raises:
        HTTPException: If the update process fails.
    """
    try:
        # Determine the FTS table name
        fts_table_name = fts_table_name or f"{table_name}_fts"

        # Query to insert new rows into the FTS table
        update_query = f"""
        INSERT INTO {fts_table_name}(rowid, title, body)
        SELECT id, title, body
        FROM {table_name}
        WHERE id NOT IN (SELECT rowid FROM {fts_table_name});
        """

        with db_manager.connection:
            result = db_manager.connection.execute(update_query)
            rows_updated = result.rowcount

        return {
            "message": f"FTS index updated for table '{table_name}'.",
            "rows_updated": rows_updated,
        }
    except Exception as e:
        logging.error(f"Error updating FTS index for table '{table_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update FTS index: {e}")


@router.post("/fts/drop")
def drop_fts_index(
    fts_table: str, db_manager: SQLiteManager = Depends(get_db_manager)
) -> dict:
    """Drop an existing full-text search index.
    Args:
        fts_table: Name of the table whose index should be dropped.
        db_manager: Database manager instance (injected dependency).
    Returns:
        dict: Success message.
    Raises:
        HTTPException: If index deletion fails.
    """
    try:
        db_manager.drop_fts_index(fts_table=fts_table)
        return {"message": f"FTS index dropped for table '{fts_table}'."}
    except Exception as e:
        logging.error(f"Error dropping FTS index: {e}")
        raise HTTPException(status_code=500, detail="Failed to drop FTS index.")


@router.get(
    "/fts/list",
    summary="List FTS Indexes",
    description="List all available FTS indexes with their indexed fields.",
)
def list_fts_indexes(db: SQLiteManager = Depends(get_db_manager)):
    """
    List all available FTS indexes and their indexed fields.

    Args:
        db (DatabaseConfig): Injected database configuration instance.

    Returns:
        dict: Dictionary containing index details.
    """
    try:
        return db.list_fts_indexes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
