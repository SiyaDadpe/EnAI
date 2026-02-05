"""
Logging configuration and utilities.

Provides:
- Standardized logging setup
- File and console handlers
- Log formatting
- Log rotation

WHY: Consistent logging across all modules makes debugging and
monitoring much easier.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from config.pipeline_config import LOG_LEVEL, LOG_FORMAT, LOG_FILE


def setup_logging(
    log_file: Path = None,
    log_level: str = None,
    log_format: str = None
) -> logging.Logger:
    """
    Configure logging for the pipeline.
    
    Creates both file and console handlers with appropriate formatting.
    
    Args:
        log_file: Path to log file (default from config)
        log_level: Logging level (default from config)
        log_format: Log message format (default from config)
    
    Returns:
        Configured root logger
    """
    # Use defaults from config if not provided
    log_file = log_file or LOG_FILE
    log_level = log_level or LOG_LEVEL
    log_format = log_format or LOG_FORMAT
    
    # Create log directory if needed
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # File handler with rotation (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    root_logger.info(f"Logging configured: level={log_level}, file={log_file}")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for temporary log level changes.
    
    Useful for making specific operations more or less verbose.
    """
    
    def __init__(self, logger: logging.Logger, level: str):
        """
        Initialize context.
        
        Args:
            logger: Logger to modify
            level: Temporary log level
        """
        self.logger = logger
        self.new_level = getattr(logging, level.upper())
        self.old_level = None
    
    def __enter__(self):
        """Save current level and set new level."""
        self.old_level = self.logger.level
        self.logger.setLevel(self.new_level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore original level."""
        self.logger.setLevel(self.old_level)
        return False


def log_dataframe_info(df, name: str = "DataFrame", logger: logging.Logger = None):
    """
    Log summary information about a DataFrame.
    
    Args:
        df: DataFrame to summarize
        name: Name for the DataFrame in logs
        logger: Logger to use (creates new one if None)
    """
    if logger is None:
        logger = get_logger(__name__)
    
    logger.info(f"{name}: {len(df)} rows × {len(df.columns)} columns")
    logger.debug(f"{name} columns: {list(df.columns)}")
    logger.debug(f"{name} memory: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
    
    # Log null counts if there are any
    null_counts = df.isnull().sum()
    if null_counts.any():
        logger.debug(f"{name} null values:\n{null_counts[null_counts > 0]}")
