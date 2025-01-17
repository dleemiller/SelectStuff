"""Models for database operations and full-text search functionality.

This module contains all Pydantic models used for database operations, including
query execution and full-text search functionality. Each model includes detailed
field descriptions and examples for Swagger documentation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ExecuteQueryRequest(BaseModel):
    """Model for executing raw SQL queries against the database.

    Attributes:
        query: SQL query string to execute. Must be a SELECT statement or read-only query.

    Examples:
        >>> request = ExecuteQueryRequest(query="SELECT * FROM users LIMIT 5")
    """

    query: str = Field(
        ...,
        description="SQL query to execute (read-only)",
        example="SELECT * FROM users WHERE age > 21 LIMIT 5",
    )


class SearchRequest(BaseModel):
    """Model for natural language search queries.

    Attributes:
        query_text: Natural language query to be converted to SQL.
        schema_info: Optional database schema information to aid in query generation.

    Examples:
        >>> request = SearchRequest(
        ...     query_text="Find all users over 30 years old",
        ...     schema_info="users(id, name, age, email)"
        ... )
    """

    query_text: str = Field(
        ...,
        description="Natural language query to convert to SQL",
        example="Find all active users who joined in the last month",
    )
    schema_info: Optional[str] = Field(
        None,
        description="Database schema information to aid query generation",
        example="users(id, name, email, joined_date, status)",
    )


class CreateFTSIndexRequest(BaseModel):
    """Model for creating a full-text search index.

    Attributes:
        fts_table: Name of the table to index.
        input_id: Primary key column name.
        input_values: List of columns to include in the search index.
        stemmer: Stemming algorithm to use (default: 'porter').
        stopwords: Stopwords language set to use (default: 'english').
        ignore: Regex pattern for characters to ignore.
        strip_accents: Whether to remove diacritics from text.
        lower: Whether to convert text to lowercase.
        overwrite: Whether to overwrite existing index.

    Examples:
        >>> request = CreateFTSIndexRequest(
        ...     fts_table="articles",
        ...     input_id="article_id",
        ...     input_values=["title", "content"],
        ...     stemmer="porter",
        ...     stopwords="english"
        ... )
    """

    fts_table: str = Field(
        ..., description="Name of the table to index", example="articles"
    )
    input_id: str = Field(
        ..., description="Primary key column name", example="article_id"
    )
    input_values: List[str] = Field(
        ...,
        description="Columns to include in the search index",
        example=["title", "content", "tags"],
    )
    stemmer: Optional[str] = Field(
        "porter", description="Stemming algorithm to use", example="porter"
    )
    stopwords: Optional[str] = Field(
        "english", description="Stopwords language set", example="english"
    )
    ignore: Optional[str] = Field(
        r"(\.|[^a-z])+",
        description="Regex pattern for characters to ignore",
        example=r"(\.|[^a-z])+",
    )
    strip_accents: Optional[bool] = Field(
        True, description="Whether to remove diacritics from text", example=True
    )
    lower: Optional[bool] = Field(
        True, description="Whether to convert text to lowercase", example=True
    )
    overwrite: Optional[bool] = Field(
        False, description="Whether to overwrite existing index", example=False
    )


class QueryFTSIndexRequest(BaseModel):
    """Model for querying a full-text search index.

    Attributes:
        fts_table: Name of the table to search.
        query_string: Search query string.
        fields: Optional list of specific fields to search.

    Examples:
        >>> request = QueryFTSIndexRequest(
        ...     fts_table="articles",
        ...     query_string="machine learning artificial intelligence",
        ...     fields=["title", "content"]
        ... )
    """

    fts_table: str = Field(
        ..., description="Name of the table to search", example="articles"
    )
    query_string: str = Field(
        ...,
        description="Search query string",
        example="machine learning artificial intelligence",
    )
    fields: Optional[List[str]] = Field(
        None, description="Specific fields to search", example=["title", "content"]
    )
    k: Optional[float] = Field(1.2, description="BM25 parameter k1", example=1.2)
    b: Optional[float] = Field(0.75, description="BM25 parameter b", example=0.75)
    conjunctive: Optional[bool] = Field(
        False, description="Use AND between terms", example=False
    )
