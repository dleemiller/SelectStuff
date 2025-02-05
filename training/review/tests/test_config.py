import pytest
from review.config import AppConfig


class TestAppConfig:
    def test_config_from_args(self):
        """Test creating config from arguments"""

        class Args:
            input_dir = "test_dir"
            accepted_dir = "accepted"
            rejected_dir = "rejected"
            file_pattern = "*.json"
            copy_mode = False
            auto_backup = True
            backup_interval = 5
            dark_mode = False
            wide_mode = True
            title = "Test App"
            debug = True

        config = AppConfig.from_args(Args())

        assert str(config.input_dir) == "test_dir"
        assert config.file_pattern == "*.json"
        assert config.auto_backup is True
        assert config.backup_interval == 5

    def test_config_validation(self):
        """Test config validation"""

        class Args:
            input_dir = "/nonexistent/path"
            accepted_dir = "accepted"
            rejected_dir = "rejected"
            file_pattern = "*.json"
            copy_mode = False
            auto_backup = True
            backup_interval = -1  # Invalid value
            dark_mode = False
            wide_mode = True
            title = "Test App"
            debug = True

        with pytest.raises(ValueError) as exc_info:
            AppConfig.from_args(Args())

        assert "backup_interval must be greater than 0" in str(exc_info.value)

    def test_empty_title_validation(self):
        """Test empty title validation"""

        class Args:
            input_dir = "/nonexistent/path"
            accepted_dir = "accepted"
            rejected_dir = "rejected"
            file_pattern = "*.json"
            copy_mode = False
            auto_backup = True
            backup_interval = 5
            dark_mode = False
            wide_mode = True
            title = ""  # Empty title
            debug = True

        with pytest.raises(ValueError) as exc_info:
            AppConfig.from_args(Args())

        assert "app_title cannot be empty" in str(exc_info.value)
