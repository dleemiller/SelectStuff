import os
import sqlite3
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any


class SQLiteManager:
    def __init__(self, db_path: str):
        """
        Initialize the SQLiteManager.

        Args:
            db_path (str): Path to the SQLite database file.
        """
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        # Establish a connection to the SQLite database
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.execute("PRAGMA foreign_keys = ON;")

    @staticmethod
    def utcnow() -> datetime:
        """
        Get the current UTC datetime.

        Returns:
            datetime: Current UTC datetime.
        """
        return datetime.utcnow()

    @staticmethod
    def compute_hash(text: str) -> str:
        """
        Compute a SHA-256 hash of the given text.

        Args:
            text (str): The input text to hash.

        Returns:
            str: The SHA-256 hash of the input text.
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def create_table(self, schema: str):
        """
        Create a table using the provided schema.

        Args:
            schema (str): SQL schema definition to create a table.

        Raises:
            RuntimeError: If the table creation fails.
        """
        try:
            with self.connection:
                self.connection.execute(schema)
        except Exception as e:
            raise RuntimeError(f"Failed to create table: {e}")

    def insert(self, table: str, data: Dict[str, Any], ignore_extra: bool = True):
        """
        Insert a record into the specified table.

        Args:
            table (str): The name of the table to insert into.
            data (Dict[str, Any]): The record data as a dictionary.
            ignore_extra (bool): Whether to ignore extra columns not in the table. Defaults to True.

        Raises:
            RuntimeError: If the insertion fails.
        """
        try:
            # If ignoring extra columns, fetch table info and filter the data
            if ignore_extra:
                cursor = self.connection.execute(f"PRAGMA table_info({table});")
                table_columns = {row[1] for row in cursor.fetchall()}
                data = {
                    key: value for key, value in data.items() if key in table_columns
                }

            placeholders = ", ".join(["?" for _ in data])
            keys = ", ".join(data.keys())
            values = tuple(data.values())

            query = f"INSERT INTO {table} ({keys}) VALUES ({placeholders})"
            with self.connection:
                self.connection.execute(query, values)
        except Exception as e:
            raise RuntimeError(f"Failed to insert data into table '{table}': {e}")

    def create_fts_index(
        self,
        fts_table: str,
        columns: List[str],
        content_table: Optional[str] = None,
        overwrite: bool = False,
        tokenize: str = "unicode61",  # e.g., 'unicode61', 'porter', etc. if compiled in
        remove_accents: bool = True,
    ):
        """
        Create a full-text search (FTS5) virtual table.

        Args:
            fts_table (str): Name of the virtual table to create for FTS.
            columns (List[str]): List of columns to be indexed.
            content_table (Optional[str]): Name of the "content" table if using external content. Defaults to None.
            overwrite (bool): Whether to overwrite an existing FTS table. Defaults to False.
            tokenize (str): Tokenizer to use ('unicode61', 'porter', etc.). Defaults to 'unicode61'.
            remove_accents (bool): Whether to remove accents. Defaults to True.

        Raises:
            RuntimeError: If the index creation fails.
        """
        # If overwrite=True, drop any existing FTS table
        if overwrite:
            drop_query = f"DROP TABLE IF EXISTS {fts_table};"
            try:
                with self.connection:
                    self.connection.execute(drop_query)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to drop existing FTS table '{fts_table}': {e}"
                )

        # Build column definitions for FTS
        # Example: "col1, col2, col3"
        columns_def = ", ".join(columns)

        # If using "external content" mode:
        #   CREATE VIRTUAL TABLE fts_table USING fts5(
        #       col1, col2, ...
        #       content='original_table',
        #       content_rowid='id',
        #       tokenize='unicode61 remove_diacritics 1'
        #   );
        #
        # Otherwise, just store text data inside the FTS table itself
        content_clause = ""
        if content_table:
            content_clause = f", content='{content_table}'"

        # If remove_accents:
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
        """
        Drop an FTS virtual table.

        Args:
            fts_table (str): Name of the FTS table to drop.

        Raises:
            RuntimeError: If the drop operation fails.
        """
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
        Perform a full-text search using the built-in FTS5 engine.

        Args:
            fts_table (str): Name of the FTS table to search.
            query_string (str): The query string to search for (FTS syntax).
            columns (Optional[List[str]]): List of columns to return. If None, returns all.
            limit (Optional[int]): Optional limit on the number of rows returned.

        Returns:
            List[tuple]: Search results as a list of tuples.

        Raises:
            RuntimeError: If the search fails.
        """
        # If columns is None, we select all columns: "SELECT *"
        # Otherwise, select the given columns plus a BM25 rank column for sorting
        select_cols = "*"
        if columns:
            # We can also add a rank column if we want: "bm25(fts_table) AS rank"
            select_cols = ", ".join(columns) + ", bm25({}) AS rank".format(fts_table)
        else:
            # By default, fetch all columns plus rank
            select_cols = "*, bm25({}) AS rank".format(fts_table)

        # Construct basic SELECT query
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
