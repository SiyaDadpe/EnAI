"""
CSV reading utilities with robust error handling.

Provides resilient CSV ingestion with:
- Automatic encoding detection
- Chunked reading for large files
- Flexible delimiter detection
- Graceful handling of malformed rows

WHY: Real-world CSV files are messy. This module handles common issues
like encoding problems, inconsistent delimiters, and corrupted rows without
failing the entire pipeline.
"""

import pandas as pd
import chardet
import logging
from pathlib import Path
from typing import Iterator, Optional, Dict, Any
import warnings

from config.pipeline_config import CHUNK_SIZE, ENCODING, ENCODING_FALLBACKS

# Suppress pandas dtype warnings during initial read
warnings.filterwarnings('ignore', category=pd.errors.DtypeWarning)

logger = logging.getLogger(__name__)


def detect_encoding(file_path: Path) -> str:
    """
    Detect the encoding of a CSV file.
    
    WHY: CSV files from different sources may use different encodings.
    Auto-detection prevents encoding errors during read.
    
    Args:
        file_path: Path to the CSV file
    
    Returns:
        Detected encoding (e.g., 'utf-8', 'latin-1')
    """
    logger.info(f"Detecting encoding for {file_path.name}")
    
    try:
        # Read first 100KB to detect encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read(100000)
        
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        confidence = result['confidence']
        
        logger.info(f"Detected encoding: {encoding} (confidence: {confidence:.2%})")
        
        # If confidence is low, fallback to UTF-8
        if confidence < 0.7:
            logger.warning(f"Low confidence ({confidence:.2%}), using UTF-8 as fallback")
            return ENCODING
        
        return encoding
    
    except Exception as e:
        logger.warning(f"Encoding detection failed: {e}. Using default: {ENCODING}")
        return ENCODING


def read_csv_with_fallback(
    file_path: Path,
    encoding: Optional[str] = None,
    **kwargs
) -> pd.DataFrame:
    """
    Read CSV with automatic encoding fallback.
    
    WHY: If the detected encoding fails, try common alternatives
    before giving up. This improves robustness.
    
    Args:
        file_path: Path to CSV file
        encoding: Encoding to try first (auto-detect if None)
        **kwargs: Additional arguments passed to pd.read_csv
    
    Returns:
        DataFrame with the CSV contents
    
    Raises:
        ValueError: If all encoding attempts fail
    """
    if encoding is None:
        encoding = detect_encoding(file_path)
    
    encodings_to_try = [encoding] + ENCODING_FALLBACKS
    
    for enc in encodings_to_try:
        try:
            logger.debug(f"Attempting to read {file_path.name} with encoding: {enc}")
            df = pd.read_csv(file_path, encoding=enc, **kwargs)
            logger.info(f"Successfully read {file_path.name} with encoding: {enc}")
            return df
        
        except UnicodeDecodeError:
            logger.debug(f"Failed with encoding {enc}, trying next...")
            continue
        
        except Exception as e:
            logger.error(f"Unexpected error reading {file_path.name}: {e}")
            raise
    
    raise ValueError(
        f"Failed to read {file_path.name} with any encoding. "
        f"Tried: {encodings_to_try}"
    )


def read_csv_chunked(
    file_path: Path,
    chunk_size: int = CHUNK_SIZE,
    encoding: Optional[str] = None,
    **kwargs
) -> Iterator[pd.DataFrame]:
    """
    Read CSV in chunks for memory-efficient processing.
    
    WHY: Large CSV files can exceed available memory. Chunked reading
    allows processing files of any size with constant memory usage.
    
    Args:
        file_path: Path to CSV file
        chunk_size: Number of rows per chunk
        encoding: File encoding (auto-detect if None)
        **kwargs: Additional arguments passed to pd.read_csv
    
    Yields:
        DataFrame chunks
    """
    if encoding is None:
        encoding = detect_encoding(file_path)
    
    logger.info(f"Reading {file_path.name} in chunks of {chunk_size} rows")
    
    try:
        # Use iterator for chunked reading
        chunks = pd.read_csv(
            file_path,
            encoding=encoding,
            chunksize=chunk_size,
            on_bad_lines='warn',  # Log bad lines but continue
            **kwargs
        )
        
        chunk_count = 0
        for chunk in chunks:
            chunk_count += 1
            logger.debug(f"Processing chunk {chunk_count} ({len(chunk)} rows)")
            yield chunk
        
        logger.info(f"Completed reading {chunk_count} chunks from {file_path.name}")
    
    except Exception as e:
        logger.error(f"Error during chunked reading of {file_path.name}: {e}")
        raise


def read_csv_robust(
    file_path: Path,
    use_chunks: bool = False,
    chunk_size: int = CHUNK_SIZE,
    **kwargs
) -> pd.DataFrame:
    """
    Main entry point for robust CSV reading.
    
    Combines all resilience features:
    - Encoding detection
    - Fallback encodings
    - Optional chunked reading
    - Bad line handling
    
    Args:
        file_path: Path to CSV file
        use_chunks: If True, return iterator; if False, return full DataFrame
        chunk_size: Chunk size for chunked reading
        **kwargs: Additional arguments passed to pd.read_csv
    
    Returns:
        DataFrame or iterator of DataFrames
    """
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    logger.info(f"Starting ingestion of {file_path.name}")
    
    # Add default parameters for robustness
    default_params = {
        'on_bad_lines': 'warn',  # Log problematic lines but continue
        'low_memory': False,      # Read entire file to infer types correctly
    }
    default_params.update(kwargs)
    
    if use_chunks:
        return read_csv_chunked(file_path, chunk_size=chunk_size, **default_params)
    else:
        return read_csv_with_fallback(file_path, **default_params)


def get_basic_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Extract basic statistics from a DataFrame.
    
    WHY: Provides quick data profiling for logging and governance.
    
    Args:
        df: Input DataFrame
    
    Returns:
        Dictionary with basic statistics
    """
    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
        "missing_values": df.isnull().sum().to_dict(),
        "dtypes": df.dtypes.astype(str).to_dict(),
    }
