import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
from app.main import app
from app.database import SQLiteManager
from app.routes.db_routes import get_db_manager

client = TestClient(app)


@pytest.fixture
def mock_db_manager(mocker):
    """Fixture to mock the SQLiteManager dependency."""
    db_manager = mocker.Mock(spec=SQLiteManager)

    # Also mock the connection attribute
    mock_connection = mocker.Mock()
    db_manager.connection = mock_connection

    app.dependency_overrides[get_db_manager] = lambda: db_manager
    return db_manager


def test_get_tables(mock_db_manager):
    """Test the GET /tables endpoint."""
    # Arrange
    mock_db_manager.connection.execute.return_value.fetchall.return_value = [
        ("table1",),
        ("table2",),
    ]

    # Act
    response = client.get("/tables")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"tables": ["table1", "table2"]}


def test_get_tables_empty(mock_db_manager):
    """Test GET /tables when there are no tables."""
    # Arrange
    mock_db_manager.connection.execute.return_value.fetchall.return_value = []

    # Act
    response = client.get("/tables")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"tables": []}


def test_get_table_schema(mock_db_manager):
    """Test the GET /tables/{table_name}/schema endpoint."""
    # Arrange
    mock_db_manager.connection.execute.return_value.fetchall.return_value = [
        (0, "id", "INTEGER", 1, None, 1),
        (1, "name", "TEXT", 0, None, 0),
    ]

    # Act
    response = client.get("/tables/test_table/schema")

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "schema": [
            {"column_name": "id", "type": "INTEGER"},
            {"column_name": "name", "type": "TEXT"},
        ]
    }


def test_get_table_schema_error(mock_db_manager):
    """Test GET /tables/{table_name}/schema when the query fails."""
    # Arrange
    mock_db_manager.connection.execute.side_effect = Exception("Database error")

    # Act
    response = client.get("/tables/non_existent_table/schema")

    # Assert
    assert response.status_code == 500
    assert "Failed to retrieve schema" in response.json()["detail"]


def test_query(mock_db_manager):
    """Test the POST /query endpoint."""
    # Arrange
    mock_db_manager.connection.execute.return_value.fetchall.return_value = [
        (1, "Test"),
        (2, "Example"),
    ]

    # Act
    response = client.post("/query", json={"query": "SELECT * FROM test_table;"})

    # Assert
    assert response.status_code == 200
    print(response.json())
    assert response.json() == {"results": [[1, "Test"], [2, "Example"]]}


def test_query_error(mock_db_manager):
    """Test POST /query with an invalid query."""
    # Arrange
    mock_db_manager.connection.execute.side_effect = Exception("Syntax error")

    # Act
    response = client.post("/query", json={"query": "INVALID QUERY"})

    # Assert
    assert response.status_code == 400
    assert "Failed to execute query" in response.json()["detail"]


def test_drop_fts_index(mock_db_manager):
    """Test the POST /fts/drop endpoint."""
    # Arrange
    mock_db_manager.drop_fts_index.return_value = None

    # Act
    response = client.post("/fts/drop?fts_table=test_table_fts")

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": "FTS index dropped for table 'test_table_fts'."
    }


def test_drop_fts_index_error(mock_db_manager):
    """Test POST /fts/drop when dropping the index fails."""
    # Arrange
    mock_db_manager.drop_fts_index.side_effect = Exception("Index drop error")

    # Act
    response = client.post("/fts/drop?fts_table=test_table_fts")

    # Assert
    assert response.status_code == 500
    assert "Failed to drop FTS index" in response.json()["detail"]


def test_query_fts_index(mock_db_manager):
    """Test the POST /fts/query endpoint."""
    # Arrange
    mock_db_manager.search_fts.return_value = [{"id": 1, "title": "Test"}]

    # Act
    response = client.post(
        "/fts/query",
        json={
            "fts_table": "test_table_fts",
            "query_string": "Test",
            "fields": ["title"],
            "limit": 10,
        },
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {"results": [{"id": 1, "title": "Test"}]}


def test_query_fts_index_empty(mock_db_manager):
    """Test POST /fts/query with no results."""
    # Arrange
    mock_db_manager.search_fts.return_value = []

    # Act
    response = client.post(
        "/fts/query",
        json={
            "fts_table": "test_table_fts",
            "query_string": "Nonexistent",
            "fields": ["title"],
            "limit": 10,
        },
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {"results": []}


def test_list_fts_indexes(mock_db_manager):
    """Test the GET /fts/list endpoint."""
    # Arrange
    mock_db_manager.list_fts_indexes.return_value = [
        {"table_name": "test_table_fts", "indexed_columns": ["column1", "column2"]}
    ]

    # Act
    response = client.get("/fts/list")

    # Assert
    assert response.status_code == 200
    assert response.json() == [
        {"table_name": "test_table_fts", "indexed_columns": ["column1", "column2"]}
    ]
