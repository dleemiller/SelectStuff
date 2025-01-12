"""Database operations and full-text search routes.

This module provides FastAPI routes for database operations including:
- Table listing
- Query execution
- Natural language search
- Full-text search index management
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request

from app.database import DuckDBManager
from app.models.db_models import (
    ExecuteQueryRequest,
    SearchRequest,
    CreateFTSIndexRequest,
    QueryFTSIndexRequest,
)


def get_db_manager(request: Request) -> DuckDBManager:
    """Get the DuckDB manager instance from the application state.

    Args:
        request: FastAPI request object containing application state.

    Returns:
        DuckDBManager: Instance of the database manager.
    """
    return request.app.state.db_manager


router = APIRouter()


@router.get("/tables")
def get_tables(db_manager: DuckDBManager = Depends(get_db_manager)) -> dict:
    """List all tables in the database.

    Args:
        db_manager: Database manager instance (injected dependency).

    Returns:
        dict: Dictionary containing list of table names.

    Raises:
        HTTPException: If table retrieval fails.
    """
    try:
        rows = db_manager.connection.execute("SHOW TABLES").fetchall()
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
    table_name: str, db_manager: DuckDBManager = Depends(get_db_manager)
):
    """
    Retrieve the schema of a specific table.

    Args:
        table_name (str): Name of the table.
        db_manager (DuckDBManager): Injected database manager instance.

    Returns:
        dict: Dictionary containing column names and types.

    Raises:
        HTTPException: If schema retrieval fails.
    """
    try:
        query = f"DESCRIBE {table_name}"
        results = db_manager.connection.execute(query).fetchall()
        schema = [{"column_name": row[0], "type": row[1]} for row in results]
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve schema for table '{table_name}': {e}",
        )


@router.post("/query")
def query(
    request: ExecuteQueryRequest, db_manager: DuckDBManager = Depends(get_db_manager)
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


@router.post("/search")
def search_endpoint(
    search_request: SearchRequest, db_manager: DuckDBManager = Depends(get_db_manager)
) -> dict:
    """Convert natural language to SQL and execute the query.

    Args:
        search_request: Search request containing natural language query.
        db_manager: Database manager instance (injected dependency).

    Returns:
        dict: Dictionary containing generated SQL and query results.

    Raises:
        HTTPException: If search operation fails.
    """
    try:
        # TODO: Implement LLM query conversion
        sql_query = "SELECT * FROM your_table LIMIT 10"  # Stub for demonstration
        results = db_manager.connection.execute(sql_query).fetchall()

        return {"generated_sql": sql_query, "results": results}
    except Exception as e:
        logging.error(f"Error in search endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform search.")


@router.post("/fts/create")
def create_fts_index(
    request: CreateFTSIndexRequest, db_manager: DuckDBManager = Depends(get_db_manager)
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
            input_table=request.input_table,
            input_id=request.input_id,
            input_values=request.input_values,
            stemmer=request.stemmer,
            stopwords=request.stopwords,
            ignore=request.ignore,
            strip_accents=request.strip_accents,
            lower=request.lower,
            overwrite=request.overwrite,
        )
        return {"message": f"FTS index created for table '{request.input_table}'."}
    except Exception as e:
        logging.error(f"Error creating FTS index: {e}")
        raise HTTPException(status_code=500, detail="Failed to create FTS index.")


@router.post("/fts/refresh")
def refresh_fts_index(
    request: CreateFTSIndexRequest, db_manager: DuckDBManager = Depends(get_db_manager)
) -> dict:
    """Refresh an existing full-text search index.

    Args:
        request: Index refresh request with table and configuration details.
        db_manager: Database manager instance (injected dependency).

    Returns:
        dict: Success message.

    Raises:
        HTTPException: If index refresh fails.
    """
    try:
        db_manager.create_fts_index(
            input_table=request.input_table,
            input_id=request.input_id,
            input_values=request.input_values,
            stemmer=request.stemmer,
            stopwords=request.stopwords,
            ignore=request.ignore,
            strip_accents=request.strip_accents,
            lower=request.lower,
            overwrite=True,
        )
        return {"message": f"FTS index refreshed for table '{request.input_table}'."}
    except Exception as e:
        logging.error(f"Error refreshing FTS index: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh FTS index.")


@router.post("/fts/drop")
def drop_fts_index(
    input_table: str, db_manager: DuckDBManager = Depends(get_db_manager)
) -> dict:
    """Drop an existing full-text search index.

    Args:
        input_table: Name of the table whose index should be dropped.
        db_manager: Database manager instance (injected dependency).

    Returns:
        dict: Success message.

    Raises:
        HTTPException: If index deletion fails.
    """
    try:
        db_manager.drop_fts_index(input_table=input_table)
        return {"message": f"FTS index dropped for table '{input_table}'."}
    except Exception as e:
        logging.error(f"Error dropping FTS index: {e}")
        raise HTTPException(status_code=500, detail="Failed to drop FTS index.")


@router.get(
    "/fts/list",
    summary="List FTS Indexes",
    description="List all available FTS indexes with their indexed fields.",
)
def list_fts_indexes(db_manager: DuckDBManager = Depends(get_db_manager)):
    """
    List all available FTS indexes and their indexed fields.

    Args:
        db_manager (DuckDBManager): Injected database manager instance.

    Returns:
        dict: Dictionary containing index details.
    """
    try:
        # Query DuckDB's information schema for FTS indexes.
        query = """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema LIKE 'fts_main_%'
          AND table_name = 'fields'
        """
        fts_schemas = db_manager.connection.execute(query).fetchall()

        indexes = {}
        for schema, _table_name in fts_schemas:
            # The schema is named fts_main_<original_table>, so extract the table name:
            table_name = schema.replace("fts_main_", "")

            # Query the 'fields' table in the FTS schema to get indexed columns
            fields_query = f"SELECT field FROM {schema}.fields"
            fields = [
                row[0] for row in db_manager.connection.execute(fields_query).fetchall()
            ]
            indexes[table_name] = fields

        return {"indexes": indexes}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list FTS indexes: {e}")


@router.post("/fts/query")
def query_fts_index(
    request: QueryFTSIndexRequest, db_manager: DuckDBManager = Depends(get_db_manager)
) -> dict:
    """Query a full-text search index using BM25 ranking.

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
            input_table=request.input_table,
            input_id=request.input_id,
            query_string=request.query_string,
            fields=request.fields,
            k=request.k,
            b=request.b,
            conjunctive=request.conjunctive,
        )
        return {"results": results}
    except Exception as e:
        logging.error(f"Error querying FTS index: {e}")
        raise HTTPException(status_code=500, detail="Failed to query FTS index.")
