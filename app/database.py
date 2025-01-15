import os
from typing import List, Optional, Any
import sqlite3
from sqlmodel import SQLModel, create_engine


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

        # Create raw SQLite connection for FTS functionality
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.execute("PRAGMA foreign_keys = ON;")

    def create_all(self, *models):
        """Create all tables for the given models."""
        SQLModel.metadata.create_all(self.engine)

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
        try:
            with self.connection:
                self.connection.execute(create_query)
        except Exception as e:
            raise RuntimeError(f"Failed to create FTS table '{fts_table}': {e}")

    def drop_fts_index(self, fts_table: str):
        """Drop an FTS virtual table."""
        query = f"DROP TABLE IF EXISTS {fts_table};"
        try:
            with self.connection:
                self.connection.execute(query)
        except Exception as e:
            raise RuntimeError(f"Failed to drop FTS table '{fts_table}': {e}")

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
        select_cols = "*"
        if columns:
            select_cols = ", ".join(columns) + f", bm25({fts_table}) AS rank"
        else:
            select_cols = f"*, bm25({fts_table}) AS rank"

        query = f"""
            SELECT {select_cols}
            FROM {fts_table}
            WHERE {fts_table} MATCH ?
            ORDER BY bm25({fts_table}) ASC
        """
        if limit:
            query += f" LIMIT {limit}"

        try:
            cursor = self.connection.execute(query, (query_string,))
            return cursor.fetchall()
        except Exception as e:
            raise RuntimeError(f"Failed to perform FTS search on '{fts_table}': {e}")

    def __del__(self):
        """Ensure the SQLite connection is closed."""
        if hasattr(self, "connection"):
            self.connection.close()
