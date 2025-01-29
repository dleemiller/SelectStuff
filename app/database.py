import os
import re
from typing import List, Optional
import sqlite3
from sqlmodel import SQLModel, create_engine
import logging

from opentelemetry import trace
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class SQLiteManager:
    """Configuration for database connections and SQLite-specific features."""

    def __init__(self, db_path: str):
        """
        Initialize database configuration.

        Args:
            db_path (str): Path to the SQLite database file.
        """
        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        # Create SQLModel engine
        self.engine = create_engine(
            f"sqlite:///{db_path}", echo=True, connect_args={"check_same_thread": False}
        )

        # 1. Instrument the SQLAlchemy engine
        #    This will produce spans for each query executed by this engine.
        SQLAlchemyInstrumentor().instrument(
            engine=self.engine
        )

        # Create raw SQLite connection for FTS functionality
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.execute("PRAGMA foreign_keys = ON;")

    def create_all(self, *models):
        """Create all tables for the given models."""
        with tracer.start_as_current_span("create_all_tables"):
            try:
                SQLModel.metadata.create_all(self.engine)
            except Exception as e:
                logger.error(f"Error creating tables: {e}")
                raise

    @tracer.start_as_current_span("create_fts_index")
    def create_fts_index(
        self,
        fts_table: str,
        columns: List[str],
        content_table: Optional[str] = None,
        overwrite: bool = False,
        tokenize: str = "unicode61",
        remove_accents: bool = True,
    ):
        """
        Create a full-text search (FTS5) virtual table.

        Args:
            fts_table (str): Name of the virtual table to create for FTS.
            columns (List[str]): List of columns to be indexed.
            content_table (Optional[str]): Name of the "content" table if using external content.
            overwrite (bool): Whether to overwrite existing FTS table.
            tokenize (str): Tokenizer to use ('unicode61', 'porter', etc.).
            remove_accents (bool): Whether to remove accents.
        """
        try:
            if overwrite:
                self.drop_fts_index(fts_table)

            columns_def = ", ".join(columns)
            content_clause = f", content='{content_table}'" if content_table else ""
            diacritic_clause = " remove_diacritics 1" if remove_accents else ""

            create_query = f"""
            CREATE VIRTUAL TABLE {fts_table}
            USING fts5 (
                {columns_def}
                {content_clause},
                tokenize='{tokenize}{diacritic_clause}'
            );
            """
            with self.connection:
                self.connection.execute(create_query)

            # Rebuild the FTS index if a content table is specified
            if content_table:
                self.rebuild_fts_index(fts_table)

        except Exception as e:
            logger.error(f"Failed to create FTS table '{fts_table}': {e}")
            raise RuntimeError(f"Failed to create FTS table '{fts_table}': {e}")

    @tracer.start_as_current_span("list_fts_indexes")
    def list_fts_indexes(self) -> dict:
        """
        List all available FTS indexes and their indexed fields.

        Returns:
            dict: Dictionary with table names as keys and lists of indexed fields as values
        """
        try:
            # Query SQLite's master table for FTS5 virtual tables
            query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND sql LIKE '%USING fts5%'
            """
            fts_tables = self.connection.execute(query).fetchall()

            indexes = {}
            for (table_name,) in fts_tables:
                # For each FTS table, get its column info from SQLite
                fields_query = f"SELECT name FROM pragma_table_info('{table_name}')"
                fields = [
                    row[0]
                    for row in self.connection.execute(fields_query).fetchall()
                    if not row[0].startswith("__")  # Skip internal FTS columns
                ]

                # If this is an external content FTS table, get the content table
                config_query = f"SELECT * FROM {table_name}('columnlist')"
                config = self.connection.execute(config_query).fetchone()
                if config:
                    config_str = config[0]
                    content_match = re.search(r"content='([^']*)'", config_str)
                    if content_match:
                        content_table = content_match.group(1)
                        table_name = f"{content_table} (FTS: {table_name})"

                indexes[table_name] = fields

            return {"indexes": indexes}

        except Exception as e:
            logger.error(f"Failed to list FTS indexes: {e}")
            raise RuntimeError(f"Failed to list FTS indexes: {e}")

    @tracer.start_as_current_span("rebuild_fts_index")
    def rebuild_fts_index(self, fts_table: str):
        """
        Rebuild the FTS index for the specified FTS table.

        Args:
            fts_table (str): Name of the FTS virtual table to rebuild.
        """
        try:
            rebuild_query = f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild');"
            with self.connection:
                self.connection.execute(rebuild_query)
            logger.info(f"Successfully rebuilt FTS index for table '{fts_table}'.")
        except Exception as e:
            logger.error(f"Failed to rebuild FTS index '{fts_table}': {e}")
            raise RuntimeError(f"Failed to rebuild FTS index '{fts_table}': {e}")

    @tracer.start_as_current_span("drop_fts_index")
    def drop_fts_index(self, fts_table: str):
        """Drop an FTS virtual table."""
        try:
            query = f"DROP TABLE IF EXISTS {fts_table};"
            with self.connection:
                self.connection.execute(query)
            logger.info(f"Successfully dropped FTS index '{fts_table}'.")
        except Exception as e:
            logger.error(f"Failed to drop FTS table '{fts_table}': {e}")
            raise RuntimeError(f"Failed to drop FTS table '{fts_table}': {e}")

    @tracer.start_as_current_span("search_fts")
    def search_fts(
        self,
        fts_table: str,
        query_string: str,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[tuple]:
        """
        Perform a full-text search using FTS5.

        Args:
            fts_table (str): Name of the FTS table to search.
            query_string (str): The query string to search for.
            columns (Optional[List[str]]): List of columns to return.
            limit (Optional[int]): Optional limit on results.

        Returns:
            List[tuple]: Search results as a list of tuples.
        """
        try:
            select_cols = "*"
            if columns:
                select_cols = ", ".join(columns) + f", bm25({fts_table}) AS rank"
            else:
                select_cols = f"*, bm25({fts_table}) AS rank"

            query = f"""
                SELECT 
                rowid, {select_cols}
                FROM {fts_table}
                WHERE {fts_table} MATCH ?
                ORDER BY bm25({fts_table}) ASC
            """
            if limit:
                query += f" LIMIT {limit}"

            cursor = self.connection.execute(query, (query_string,))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to perform FTS search on '{fts_table}': {e}")
            raise RuntimeError(f"Failed to perform FTS search on '{fts_table}': {e}")

    def __del__(self):
        """Ensure the SQLite connection is closed."""
        if hasattr(self, "connection"):
            self.connection.close()
            logger.info("SQLite connection closed.")
