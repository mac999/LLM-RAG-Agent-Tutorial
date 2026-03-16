"""
Logging configuration utility
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(log_level: str = "INFO", log_file: Path = None) -> logging.Logger:
    """
    Initialize logging configuration
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Log file path (disable file logging if None)
        
    Returns:
        Configured logger instance
    """
    
    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Set log format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Setup file handler (if needed)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_log_file_path(base_dir: Path) -> Path:
    """
    Generate log file path
    
    Args:
        base_dir: Base directory
        
    Returns:
        Log file path with timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return base_dir / "logs" / f"ifc_import_{timestamp}.log"