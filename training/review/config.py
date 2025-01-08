from dataclasses import dataclass
from pathlib import Path
import argparse


@dataclass
class AppConfig:
    """Application configuration"""

    input_dir: Path
    accepted_dir: Path
    rejected_dir: Path
    file_pattern: str
    copy_mode: bool
    auto_backup: bool
    backup_interval: int
    dark_mode: bool
    wide_mode: bool
    app_title: str
    debug: bool

    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.backup_interval <= 0:
            raise ValueError("backup_interval must be greater than 0")

        if not self.app_title:
            raise ValueError("app_title cannot be empty")

        if not self.file_pattern:
            raise ValueError("file_pattern cannot be empty")

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "AppConfig":
        """Create config from parsed arguments"""
        print(args)
        config = cls(
            input_dir=Path(args.input_dir),
            accepted_dir=Path(args.input_dir) / args.accepted_dir,
            rejected_dir=Path(args.input_dir) / args.rejected_dir,
            file_pattern=args.file_pattern,
            copy_mode=args.copy_mode,
            auto_backup=args.auto_backup,
            backup_interval=args.backup_interval,
            dark_mode=args.dark_mode,
            wide_mode=args.wide_mode,
            app_title=args.title,
            debug=args.debug,
        )
        return config
