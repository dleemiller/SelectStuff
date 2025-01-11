import hashlib
import os
from datetime import datetime

import duckdb


class DuckDBManager:
    def __init__(self, db_path: str):
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

        self.connection = duckdb.connect(db_path)

    @staticmethod
    def utcnow() -> datetime:
        return datetime.utcnow()

    @staticmethod
    def compute_hash(text) -> str:
        """Compute a SHA-256 hash of the text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def create_table(self, schema: str):
        """Execute a schema creation statement."""
        self.connection.execute(schema)

    def insert(self, table: str, data: dict, ignore_extra: bool = True):
        """Insert a record into the specified table, optionally ignoring extra columns."""
        if ignore_extra:
            # Get the column names for the target table
            table_columns = {
                row[0]
                for row in self.connection.execute(f"DESCRIBE {table}").fetchall()
            }
            # Filter the data to include only columns present in the table
            data = {key: value for key, value in data.items() if key in table_columns}

        placeholders = ", ".join(["?" for _ in data])
        keys = ", ".join(data.keys())
        values = tuple(data.values())

        query = f"INSERT INTO {table} ({keys}) VALUES ({placeholders})"
        self.connection.execute(query, values)
