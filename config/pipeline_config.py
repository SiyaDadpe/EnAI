"""
Pipeline-level configuration and settings.

Defines behavior for the entire data pipeline including:
- File paths and directories
- Processing parameters
- Quality thresholds
- Logging configuration

WHY: Centralized config makes the pipeline easy to tune without
changing code, and supports different environments (dev/prod).
"""

import os
from pathlib import Path


# Base directories
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
VALIDATED_DATA_DIR = DATA_DIR / "validated"
OUTPUT_DIR = DATA_DIR / "output"

# Expected input files
EXPECTED_FILES = [
    "Weather.csv",
    "Station Region.csv",
    "Activity Logs.csv",
    "Reference Units.csv",
]

# Ingestion settings
CHUNK_SIZE = 10000  # WHY: Process large files in chunks to avoid memory issues
ENCODING = "utf-8"  # Default encoding; will auto-detect if this fails
ENCODING_FALLBACKS = ["latin-1", "iso-8859-1", "cp1252"]

# Validation settings
MAX_MISSING_RATIO = 0.5  # WHY: Rows with >50% missing values are likely corrupted
DUPLICATE_ACTION = "flag"  # Options: "flag", "drop_all", "keep_first", "keep_last"

# Quality thresholds (for governance reporting)
MIN_COMPLETENESS_THRESHOLD = 0.8  # 80% of required fields must be present

# Date parsing
DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m-%d-%Y",
    "%m/%d/%Y",
]

# Logging
LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = PROJECT_ROOT / "pipeline.log"

# Governance
ENABLE_LINEAGE_TRACKING = True
ENABLE_AUDIT_LOGGING = True
METADATA_OUTPUT_PATH = OUTPUT_DIR / "metadata.json"

# Idempotency
# WHY: Track which files have been processed to support incremental updates
PROCESSED_FILES_REGISTRY = DATA_DIR / ".processed_registry.json"


def ensure_directories():
    """Create necessary directories if they don't exist."""
    for directory in [RAW_DATA_DIR, VALIDATED_DATA_DIR, OUTPUT_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
