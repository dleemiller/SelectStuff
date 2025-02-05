import pytest
import tempfile
from pathlib import Path
import json


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield Path(tmpdirname)


@pytest.fixture
def sample_json_file(temp_dir):
    """Create a sample JSON file for testing"""
    file_path = temp_dir / "test.json"
    data = {
        "article_text": "Sample article text",
        "publication_date": "2024-01-01",
        "keywords": ["test", "sample"],
        "sentiment_tone": "neutral",
    }
    with open(file_path, "w") as f:
        json.dump(data, f)
    return file_path


@pytest.fixture
def app_config(temp_dir):
    """Create test configuration"""
    from review.config import AppConfig

    return AppConfig(
        input_dir=temp_dir,
        accepted_dir=temp_dir / "accepted",
        rejected_dir=temp_dir / "rejected",
        file_pattern="*.json",
        copy_mode=False,
        auto_backup=True,
        backup_interval=5,
        dark_mode=False,
        wide_mode=True,
        app_title="Test App",
        debug=True,
    )
