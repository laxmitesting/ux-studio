import logging
import os
import sys
from pathlib import Path

# Resolve project root and ensure logs/ directory exists
PROJECT_ROOT = Path(__file__).resolve().parent
# If logger.py is inside a subfolder (like utils/ or core/), traverse up
if (PROJECT_ROOT / "db").exists() or (PROJECT_ROOT / "orchestrator").exists():
    ROOT_DIR = PROJECT_ROOT
else:
    ROOT_DIR = PROJECT_ROOT.parent

LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "ux_studio.log"

# Define log format
LOG_FORMAT = "%(asctime)s | %(levelname)-7s | [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str = "ux_studio", level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a thread-safe logger that streams to
    both standard output and logs/ux_studio.log.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if setup_logger is called repeatedly
    if logger.handlers:
        return logger

    # 1. Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 2. Rotating/File Handler
    try:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # Fallback gracefully if filesystem permissions prevent log creation
        print(f"Warning: Could not initialize file handler at {LOG_FILE}: {e}")

    logger.propagate = False
    return logger


# Default singleton instance for quick imports
logger = setup_logger("ux_studio")