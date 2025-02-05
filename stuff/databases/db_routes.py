"""
Database operations and full-text search routes.

This module provides FastAPI routes for database operations including:
- Table listing
- Query execution
- Natural language search
- Full-text search index management

This version uses a factory function to create an application-specific router.
Each router uses the provided SQLiteManager instance, rather than relying on a global
instance from app.state.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from stuff.databases.database import SQLiteManager
from stuff.databases.models import (
    ExecuteQueryRequest,
    CreateFTSIndexRequest,
    QueryFTSIndexRequest,
)
from opentelemetry import trace

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


def create_db_router(db_manager: SQLiteManager) -> APIRouter:
    """
    Create an APIRouter for database operations using the given SQLiteManager.

    This router provides endpoints for table listing, query execution, and full-text
    search operations, all of which use the supplied db_manager instance.

    Args:
        db_manager (SQLiteManager): The application-specific database manager.

    Returns:
        APIRouter: Router with namespaced database endpoints.
    """
    router = APIRouter(prefix="/db", tags=["Database"])

    def get_db_manager_override() -> SQLiteManager:
        """
        Dependency override that returns the application-specific SQLiteManager.

        Returns:
            SQLiteManager: The provided database manager.
        """
        return db_manager

    @tracer.start_as_current_span("get_tables")
    @router.get("/tables")
    def get_tables(manager: SQLiteManager = Depends(get_db_manager_override)) -> dict:
        """
        List all tables in the database.

        Args:
            manager (SQLiteManager): Injected database manager instance.

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
            rows = manager.connection.execute(query).fetchall()
            tables = [r[0] for r in rows]
            return {"tables": tables}
        except Exception as e:
            logger.error(f"Error retrieving tables: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve tables.")

    @tracer.start_as_current_span("get_table_schema")
    @router.get(
        "/tables/{table_name}/schema",
        summary="Get Table Schema",
        description="Retrieve the schema of a specific table.",
    )
    def get_table_schema(
        table_name: str, manager: SQLiteManager = Depends(get_db_manager_override)
    ):
        """
        Retrieve the schema of a specific table.

        Args:
            table_name (str): Name of the table.
            manager (SQLiteManager): Injected database manager instance.

        Returns:
            dict: Dictionary containing column names and types.

        Raises:
            HTTPException: If schema retrieval fails.
        """
        try:
            query = f"PRAGMA table_info({table_name});"
            results = manager.connection.execute(query).fetchall()
            schema = [{"column_name": row[1], "type": row[2]} for row in results]
            return {"schema": schema}
        except Exception as e:
            logger.error(f"Error retrieving schema for table '{table_name}': {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve schema for table '{table_name}': {e}",
            )

    @tracer.start_as_current_span("get_query")
    @router.post("/query")
    def query(
        request: ExecuteQueryRequest,
        manager: SQLiteManager = Depends(get_db_manager_override),
    ) -> dict:
        """
        Execute a read-only SQL query.

        Args:
            request (ExecuteQueryRequest): Query execution request containing SQL statement.
            manager (SQLiteManager): Injected database manager instance.

        Returns:
            dict: Dictionary containing query results.

        Raises:
            HTTPException: If query execution fails.
        """
        try:
            results = manager.connection.execute(request.query).fetchall()
            return {"results": results}
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise HTTPException(status_code=400, detail="Failed to execute query.")

    @tracer.start_as_current_span("post_fts_create")
    @router.post("/fts/create")
    def create_fts_index(
        request: CreateFTSIndexRequest,
        manager: SQLiteManager = Depends(get_db_manager_override),
    ) -> dict:
        """
        Create a full-text search index for specified table and columns.

        Args:
            request (CreateFTSIndexRequest): Index creation request with table and configuration details.
            manager (SQLiteManager): Injected database manager instance.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If index creation fails.
        """
        try:
            manager.create_fts_index(
                fts_table=request.fts_table + "_fts",
                columns=request.input_values,
                content_table=request.fts_table,
                overwrite=request.overwrite,
            )
            return {"message": f"FTS index created for table '{request.fts_table}'."}
        except Exception as e:
            logger.error(f"Error creating FTS index: {e}")
            raise HTTPException(status_code=500, detail="Failed to create FTS index.")

    @tracer.start_as_current_span("post_fts_query")
    @router.post("/fts/query")
    def query_fts_index(
        request: QueryFTSIndexRequest,
        manager: SQLiteManager = Depends(get_db_manager_override),
    ) -> dict:
        """
        Query a full-text search index.

        Args:
            request (QueryFTSIndexRequest): Search request with query string and configuration.
            manager (SQLiteManager): Injected database manager instance.

        Returns:
            dict: Dictionary containing search results.

        Raises:
            HTTPException: If search query fails.
        """
        try:
            results = manager.search_fts(
                fts_table=request.fts_table,
                query_string=request.query_string,
                columns=request.fields,
                limit=request.limit,
            )
            return {"results": results}
        except Exception as e:
            logger.error(f"Error querying FTS index: {e}")
            raise HTTPException(status_code=500, detail="Failed to query FTS index.")

    @tracer.start_as_current_span("post_fts_update")
    @router.post("/fts/update")
    def update_fts_index(
        table_name: str,
        fts_table_name: Optional[str] = None,
        manager: SQLiteManager = Depends(get_db_manager_override),
    ) -> dict:
        """
        Update the full-text search index for new rows added to the table.

        Args:
            table_name (str): Name of the main table containing new rows.
            fts_table_name (Optional[str]): Name of the FTS table. Defaults to table_name + '_fts'.
            manager (SQLiteManager): Injected database manager instance.

        Returns:
            dict: Success message with the number of rows added to the index.

        Raises:
            HTTPException: If the update process fails.
        """
        try:
            fts_table_name = fts_table_name or f"{table_name}_fts"
            update_query = f"""
            INSERT INTO {fts_table_name}(rowid, title, body)
            SELECT id, title, body
            FROM {table_name}
            WHERE id NOT IN (SELECT rowid FROM {fts_table_name});
            """
            with manager.connection:
                result = manager.connection.execute(update_query)
                rows_updated = result.rowcount
            return {
                "message": f"FTS index updated for table '{table_name}'.",
                "rows_updated": rows_updated,
            }
        except Exception as e:
            logger.error(f"Error updating FTS index for table '{table_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to update FTS index: {e}"
            )

    @tracer.start_as_current_span("post_fts_drop")
    @router.post("/fts/drop")
    def drop_fts_index(
        fts_table: str, manager: SQLiteManager = Depends(get_db_manager_override)
    ) -> dict:
        """
        Drop an existing full-text search index.

        Args:
            fts_table (str): Name of the table whose index should be dropped.
            manager (SQLiteManager): Injected database manager instance.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If index deletion fails.
        """
        try:
            manager.drop_fts_index(fts_table=fts_table)
            return {"message": f"FTS index dropped for table '{fts_table}'."}
        except Exception as e:
            logger.error(f"Error dropping FTS index: {e}")
            raise HTTPException(status_code=500, detail="Failed to drop FTS index.")

    @tracer.start_as_current_span("get_fts_list")
    @router.get(
        "/fts/list",
        summary="List FTS Indexes",
        description="List all available FTS indexes with their indexed fields.",
    )
    def list_fts_indexes(manager: SQLiteManager = Depends(get_db_manager_override)):
        """
        List all available FTS indexes and their indexed fields.

        Args:
            manager (SQLiteManager): Injected database manager instance.

        Returns:
            dict: Dictionary containing index details.

        Raises:
            HTTPException: If retrieval fails.
        """
        try:
            return manager.list_fts_indexes()
        except Exception as e:
            logger.error(f"Failed to list FTS indexes: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
