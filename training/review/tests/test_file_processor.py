import pytest
from pathlib import Path
import json
import shutil
from datetime import datetime
from review.core.file_processor import FileProcessor
from review.core.types import FileAction


class TestFileProcessor:
    def test_initialization(self, app_config, temp_dir):
        """Test FileProcessor initialization creates required directories"""
        processor = FileProcessor(app_config)

        assert app_config.input_dir.exists()
        assert app_config.accepted_dir.exists()
        assert app_config.rejected_dir.exists()
        assert (app_config.input_dir / "backups").exists()
        assert (app_config.input_dir / "temp").exists()

    def test_load_json(self, app_config, sample_json_file):
        """Test loading JSON file"""
        processor = FileProcessor(app_config)
        data = processor.load_json(sample_json_file)

        assert isinstance(data, dict)
        assert "article_text" in data
        assert data["article_text"] == "Sample article text"

    def test_load_invalid_json(self, app_config, temp_dir):
        """Test loading invalid JSON file"""
        invalid_file = temp_dir / "invalid.json"
        invalid_file.write_text("{invalid json")

        processor = FileProcessor(app_config)
        with pytest.raises(json.JSONDecodeError):
            processor.load_json(invalid_file)

    def test_save_json(self, app_config, temp_dir):
        """Test saving JSON file"""
        processor = FileProcessor(app_config)
        file_path = temp_dir / "save_test.json"
        test_data = {"test": "data"}

        processor.save_json(test_data, file_path)

        assert file_path.exists()
        with open(file_path) as f:
            saved_data = json.load(f)
        assert saved_data == test_data

    def test_backup_creation(self, app_config, sample_json_file):
        """Test backup creation"""
        processor = FileProcessor(app_config)
        backup_path = processor.create_backup(sample_json_file)

        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.parent.name == datetime.now().strftime("%Y%m%d")

    def test_move_file(self, app_config, sample_json_file):
        """Test moving file to accepted directory"""
        processor = FileProcessor(app_config)
        processor.move_file(sample_json_file, FileAction.ACCEPT)

        new_path = app_config.accepted_dir / sample_json_file.name
        assert not sample_json_file.exists()
        assert new_path.exists()

    def test_copy_mode(self, app_config, sample_json_file):
        """Test copy mode instead of move"""
        app_config.copy_mode = True
        processor = FileProcessor(app_config)
        processor.move_file(sample_json_file, FileAction.ACCEPT)

        new_path = app_config.accepted_dir / sample_json_file.name
        assert sample_json_file.exists()
        assert new_path.exists()

    def test_get_files(self, app_config, temp_dir):
        """Test getting list of files"""
        # Create some test files
        for i in range(3):
            file_path = temp_dir / f"test_{i}.json"
            file_path.write_text("{}")

        processor = FileProcessor(app_config)
        files = processor.get_files()

        assert len(files) == 3
        assert all(f.suffix == ".json" for f in files)

    def test_cleanup_old_backups(self, app_config, temp_dir):
        """Test cleanup of old backups"""
        processor = FileProcessor(app_config)
        backup_dir = temp_dir / "backups" / datetime.now().strftime("%Y%m%d")
        backup_dir.mkdir(parents=True, exist_ok=True)  # Added exist_ok=True

        # Create some backup files
        for i in range(3):
            file_path = backup_dir / f"backup_{i}.json"
            file_path.write_text("{}")

        processor.cleanup_old_backups(days=0)  # Immediate cleanup

        remaining_files = list(backup_dir.glob("*.json"))
        assert len(remaining_files) == 0
