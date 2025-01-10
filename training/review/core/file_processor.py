# core/file_processor.py
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Any, Optional, Generator
import json
import shutil
import logging
import hashlib
from datetime import datetime
import os
from threading import Lock
import tempfile
from concurrent.futures import ThreadPoolExecutor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .types import FileAction
from ..config import AppConfig


class FileChangeHandler(FileSystemEventHandler):
    """Handler for file system events"""

    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory:
            self.callback(event.src_path)


@lru_cache(maxsize=1)
def get_observer():
    return Observer()


class FileProcessor:
    """
    Handles all file operations including reading, writing, moving,
    and monitoring files with backup support and error handling.
    """

    def __init__(self, config: AppConfig):
        """
        Initialize the file processor

        Args:
            config: Application configuration
        """
        self.config = config
        self.file_lock = Lock()
        self._setup_directories()
        self._setup_logging()
        self.observer = get_observer()
        self._setup_file_monitoring()
        self.backup_hashes = {}  # Track file hashes for backup

    def _setup_directories(self) -> None:
        """Create and validate all necessary directories"""
        try:
            # Ensure all directories exist
            directories = [
                self.config.input_dir,
                self.config.accepted_dir,
                self.config.rejected_dir,
                self._get_backup_dir(),
                self._get_temp_dir(),
            ]

            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)

            # Validate write permissions
            for directory in directories:
                if not os.access(directory, os.W_OK):
                    raise PermissionError(f"No write permission for {directory}")

        except Exception as e:
            logging.error(f"Error setting up directories: {e}")
            raise

    def _setup_logging(self) -> None:
        """Configure logging for file operations"""
        log_file = self.config.input_dir / "file_operations.log"
        logging.basicConfig(
            level=logging.DEBUG if self.config.debug else logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        )

    def _setup_file_monitoring(self) -> None:
        """Setup file system monitoring for changes"""
        if not self.observer.is_alive():
            self.observer.start()

        event_handler = FileChangeHandler(self._on_file_changed)
        try:
            self.observer.schedule(
                event_handler, str(self.config.input_dir), recursive=False
            )
        except Exception as e:
            logging.warning(f"Watch already exists for {self.config.input_dir}: {e}")

    def _get_backup_dir(self) -> Path:
        """Get backup directory path with timestamp-based subdirectory"""
        timestamp = datetime.now().strftime("%Y%m%d")
        backup_dir = self.config.input_dir / "backups" / timestamp
        return backup_dir

    def _get_temp_dir(self) -> Path:
        """Get temporary directory path"""
        return self.config.input_dir / "temp"

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file contents"""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _on_file_changed(self, file_path: str) -> None:
        """Handle file change events"""
        logging.debug(f"File changed: {file_path}")
        # Implement any necessary file change handling

    def get_files(self) -> List[Path]:
        """
        Get list of files matching pattern in input directory

        Returns:
            List of Path objects for matching files
        """
        try:
            files = list(self.config.input_dir.glob(self.config.file_pattern))
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return files
        except Exception as e:
            logging.error(f"Error listing files: {e}")
            return []

    def load_json(self, file_path: Path, validate: bool = True) -> Dict[str, Any]:
        """
        Load and parse JSON file

        Args:
            file_path: Path to JSON file
            validate: Whether to validate JSON schema

        Returns:
            Parsed JSON data
        """
        try:
            with self.file_lock:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

            if validate:
                self._validate_json_schema(data)

            return data

        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in {file_path}: {e}")
            raise
        except Exception as e:
            logging.error(f"Error loading {file_path}: {e}")
            raise

    def save_json(
        self, data: Dict[str, Any], file_path: Path, create_backup: bool = True
    ) -> None:
        """
        Save JSON data to file

        Args:
            data: JSON data to save
            file_path: Path to save file
            create_backup: Whether to create backup before saving
        """
        try:
            if create_backup:
                self.create_backup(file_path)

            # Write to temporary file first
            temp_file = self._get_temp_dir() / f"{file_path.name}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomically replace original file
            with self.file_lock:
                temp_file.replace(file_path)

            logging.info(f"Successfully saved {file_path}")

        except Exception as e:
            logging.error(f"Error saving {file_path}: {e}")
            raise

    def create_backup(self, file_path: Path) -> Optional[Path]:
        """
        Create backup of a file if needed

        Args:
            file_path: Path to file to backup

        Returns:
            Path to backup file if created, None otherwise
        """
        try:
            current_hash = self._calculate_file_hash(file_path)

            # Check if backup needed
            if self.backup_hashes.get(file_path) == current_hash:
                return None

            # Create backup
            backup_dir = self._get_backup_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"

            shutil.copy2(file_path, backup_path)
            self.backup_hashes[file_path] = current_hash

            logging.info(f"Created backup: {backup_path}")
            return backup_path

        except Exception as e:
            logging.error(f"Error creating backup of {file_path}: {e}")
            return None

    def move_file(self, source: Path, action: FileAction) -> None:
        """
        Move file to appropriate directory based on action

        Args:
            source: Source file path
            action: FileAction enum indicating destination
        """
        try:
            destination_dir = (
                self.config.accepted_dir
                if action == FileAction.ACCEPT
                else self.config.rejected_dir
            )

            # Create unique filename if needed
            destination = destination_dir / source.name
            if destination.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                destination = (
                    destination_dir / f"{source.stem}_{timestamp}{source.suffix}"
                )

            # Move or copy based on configuration
            with self.file_lock:
                if self.config.copy_mode:
                    shutil.copy2(source, destination)
                    logging.info(f"Copied {source.name} to {destination_dir.name}/")
                else:
                    shutil.move(str(source), str(destination))
                    logging.info(f"Moved {source.name} to {destination_dir.name}/")

        except Exception as e:
            logging.error(f"Error moving file {source}: {e}")
            raise

        except Exception as e:
            logging.error(f"Error moving file {source}: {e}")
            raise

    def _validate_json_schema(self, data: Dict[str, Any]) -> None:
        """
        Validate JSON data against schema

        Args:
            data: JSON data to validate
        """
        # Add schema validation if needed
        pass

    def cleanup_old_backups(self, days: int = 30) -> None:
        """
        Clean up backup files older than specified days

        Args:
            days: Number of days to keep backups
        """
        try:
            backup_dir = self.config.input_dir / "backups"
            cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)

            for path in backup_dir.rglob("*"):
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
                    logging.info(f"Removed old backup: {path}")

        except Exception as e:
            logging.error(f"Error cleaning up backups: {e}")

    def get_file_status(self, file_path: Path) -> Dict[str, Any]:
        """
        Get status information about a file

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file status information
        """
        try:
            stats = file_path.stat()
            return {
                "size": stats.st_size,
                "modified": datetime.fromtimestamp(stats.st_mtime),
                "created": datetime.fromtimestamp(stats.st_ctime),
                "backup_exists": any(
                    self._get_backup_dir().glob(f"{file_path.stem}_*")
                ),
                "hash": self._calculate_file_hash(file_path),
            }
        except Exception as e:
            logging.error(f"Error getting file status for {file_path}: {e}")
            return {}

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        try:
            # Don't stop the observer since it's shared
            for path in self._get_temp_dir().glob("*.tmp"):
                path.unlink()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
