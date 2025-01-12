import hashlib
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

import duckdb


class DuckDBManager:
    def __init__(self, db_path: str):
        """
        Initialize the DuckDBManager.

        Args:
            db_path (str): Path to the DuckDB database file.
        """
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

        self.connection = duckdb.connect(db_path)
        self._ensure_fts_extension()

    def _ensure_fts_extension(self):
        """
        Ensure the Full-Text Search (FTS) extension is installed and loaded.

        Raises:
            RuntimeError: If the extension cannot be loaded or installed.
        """
        try:
            # Attempt to load the FTS extension
            self.connection.load_extension("fts")
        except duckdb.IOException as load_error:
            if "not found" in str(load_error).lower():
                try:
                    # If not found, install the extension and retry loading
                    self.connection.install_extension("fts")
                    self.connection.load_extension("fts")
                except Exception as install_error:
                    raise RuntimeError(
                        f"Failed to install or load FTS extension: {install_error}"
                    )
            else:
                raise RuntimeError(f"Failed to load FTS extension: {load_error}")

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
            if ignore_extra:
                # Get the column names for the target table
                table_columns = {
                    row[0]
                    for row in self.connection.execute(f"DESCRIBE {table}").fetchall()
                }
                # Filter the data to include only columns present in the table
                data = {
                    key: value for key, value in data.items() if key in table_columns
                }

            placeholders = ", ".join(["?" for _ in data])
            keys = ", ".join(data.keys())
            values = tuple(data.values())

            query = f"INSERT INTO {table} ({keys}) VALUES ({placeholders})"
            self.connection.execute(query, values)
        except Exception as e:
            raise RuntimeError(f"Failed to insert data into table '{table}': {e}")

    def create_fts_index(
        self,
        input_table: str,
        input_id: str,
        input_values: List[str],
        stemmer: str = "porter",
        stopwords: str = "english",
        ignore: str = r"(\.|[^a-z])+",
        strip_accents: bool = True,
        lower: bool = True,
        overwrite: bool = False,
    ):
        """
        Create a full-text search (FTS) index on the specified table and columns.

        Args:
            input_table (str): Name of the table to index.
            input_id (str): Column name of the document identifier.
            input_values (List[str]): List of column names to be indexed.
            stemmer (str): Type of stemmer to use. Defaults to 'porter'.
            stopwords (str): Stopwords list. Defaults to 'english'.
            ignore (str): Regular expression of patterns to ignore. Defaults to r"(\\.|[^a-z])+"
            strip_accents (bool): Whether to remove accents. Defaults to True.
            lower (bool): Whether to lowercase text. Defaults to True.
            overwrite (bool): Whether to overwrite an existing index. Defaults to False.

        Raises:
            RuntimeError: If the index creation fails.
        """
        input_values_str = ", ".join(input_values)
        try:
            self.connection.execute(
                f"""
                PRAGMA create_fts_index(
                    '{input_table}',
                    '{input_id}',
                    {input_values_str},
                    stemmer = '{stemmer}',
                    stopwords = '{stopwords}',
                    ignore = '{ignore}',
                    strip_accents = {1 if strip_accents else 0},
                    lower = {1 if lower else 0},
                    overwrite = {1 if overwrite else 0}
                );
                """
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to create FTS index on table '{input_table}': {e}"
            )

    def drop_fts_index(self, input_table: str):
        """
        Drop an FTS index for the specified table.

        Args:
            input_table (str): Name of the table whose index should be dropped.

        Raises:
            RuntimeError: If the index drop operation fails.
        """
        try:
            self.connection.execute(f"PRAGMA drop_fts_index('{input_table}');")
        except Exception as e:
            raise RuntimeError(
                f"Failed to drop FTS index for table '{input_table}': {e}"
            )

    def search_fts(
        self,
        input_table: str,
        input_id: str,
        query_string: str,
        fields: Optional[List[str]] = None,
        k: float = 1.2,
        b: float = 0.75,
        conjunctive: bool = False,
    ) -> List[tuple]:
        """
        Perform a full-text search using the BM25 ranking model.

        Args:
            input_table (str): Name of the table to search.
            input_id (str): Identifier column in the table.
            query_string (str): Query string to search for.
            fields (Optional[List[str]]): List of fields to search in. Defaults to None (all indexed fields).
            k (float): BM25 parameter k1. Defaults to 1.2.
            b (float): BM25 parameter b. Defaults to 0.75.
            conjunctive (bool): Whether to require all query terms to be present. Defaults to False.

        Returns:
            List[tuple]: List of search results, including document identifiers and scores.

        Raises:
            RuntimeError: If the search fails.
        """
        fields_str = f"'{', '.join(fields)}'" if fields else "NULL"
        schema_name = f"fts_main_{input_table.replace('.', '_')}"  # Correct schema name

        try:
            query = f"""
            SELECT *
            FROM (
                SELECT *,
                       {schema_name}.match_bm25(
                           {input_id},
                           '{query_string}',
                           fields := {fields_str},
                           k := {k},
                           b := {b},
                           conjunctive := {1 if conjunctive else 0}
                       ) AS score
                FROM {input_table}
            ) sq
            WHERE score IS NOT NULL
            ORDER BY score DESC;
            """
            return self.connection.execute(query).fetchall()
        except Exception as e:
            raise RuntimeError(
                f"Failed to perform full-text search on table '{input_table}': {e}"
            )
