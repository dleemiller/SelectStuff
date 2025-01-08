import argparse
from typing import Dict, Any
import logging
from pathlib import Path
import yaml


def setup_argparse() -> argparse.ArgumentParser:
    """
    Setup command line argument parsing with comprehensive options for the JSON Review Tool.
    Returns an configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="JSON Review Tool - Interactive UI for reviewing JSON files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Input/Output options
    io_group = parser.add_argument_group("Input/Output Options")
    io_group.add_argument(
        "input_dir", type=str, help="Input directory containing JSON files"
    )
    io_group.add_argument(
        "--accepted-dir",
        dest="accepted_dir",
        default="accepted",
        help="Directory name for accepted files",
    )
    io_group.add_argument(
        "--rejected-dir",
        dest="rejected_dir",
        default="rejected",
        help="Directory name for rejected files",
    )
    io_group.add_argument(
        "--file-pattern",
        default="*.json",
        help="File pattern to match (e.g., *.json, *.txt)",
    )

    # Operation mode options
    mode_group = parser.add_argument_group("Operation Mode")
    mode_group.add_argument(
        "--copy-mode",
        action="store_true",
        help="Copy instead of move files when accepting/rejecting",
    )
    mode_group.add_argument(
        "--port", type=int, default=8501, help="Port for Streamlit server"
    )

    # Backup options
    backup_group = parser.add_argument_group("Backup Options")
    backup_group.add_argument(
        "--auto-backup",
        action="store_true",
        help="Automatically backup files before modifications",
    )
    backup_group.add_argument(
        "--backup-interval", type=int, default=5, help="Minutes between auto-backups"
    )
    backup_group.add_argument(
        "--backup-dir", default="backups", help="Directory for storing backups"
    )

    # UI options
    ui_group = parser.add_argument_group("UI Options")
    ui_group.add_argument("--dark-mode", action="store_true", help="Enable dark mode")
    ui_group.add_argument(
        "--title", default="JSON Data Review Tool", help="Application title"
    )
    ui_group.add_argument(
        "--wide-mode", action="store_true", help="Use wide layout mode"
    )

    # Debug options
    debug_group = parser.add_argument_group("Debug Options")
    debug_group.add_argument("--debug", action="store_true", help="Enable debug mode")
    debug_group.add_argument("--log-file", default="app.log", help="Log file location")

    # Config file option
    parser.add_argument(
        "--config", type=str, help="Path to YAML config file for default settings"
    )

    return parser


def load_config_file(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Dictionary containing configuration values
    """
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.warning(f"Error loading config file: {e}")
        return {}


def merge_config_with_args(
    args: argparse.Namespace, config: Dict[str, Any]
) -> argparse.Namespace:
    """
    Merge command line arguments with configuration file values.
    Command line arguments take precedence over config file values.

    Args:
        args: Parsed command line arguments
        config: Configuration dictionary from file

    Returns:
        Updated argument namespace
    """
    for key, value in config.items():
        if not hasattr(args, key) or getattr(args, key) is None:
            setattr(args, key, value)
    return args


def process_args() -> argparse.Namespace:
    """
    Process command line arguments and configuration file.

    Returns:
        Processed and merged arguments
    """
    parser = setup_argparse()
    args = parser.parse_args()

    # Load config file if specified
    if args.config:
        config = load_config_file(args.config)
        args = merge_config_with_args(args, config)

    # Convert input_dir to absolute path
    args.input_dir = str(Path(args.input_dir).resolve())

    return args
