"""
Schema inference and initial type conversion utilities.

Handles:
- Automatic data type detection
- Smart type conversion with error handling
- Schema drift detection
- Column name normalization

WHY: Input CSVs may have inconsistent types (e.g., dates as strings,
numbers with commas). This module standardizes types early in the pipeline.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from config.schema_config import get_schema, get_column_types
from config.pipeline_config import DATE_FORMATS

logger = logging.getLogger(__name__)


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names for consistency.
    
    WHY: CSVs may have inconsistent column naming (spaces, case, etc.).
    Normalization prevents downstream errors from mismatched names.
    
    Transformations:
    - Convert to lowercase
    - Replace spaces with underscores
    - Remove special characters
    
    Args:
        df: Input DataFrame
    
    Returns:
        DataFrame with normalized column names
    """
    original_cols = df.columns.tolist()
    
    normalized_cols = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(' ', '_')
        .str.replace(r'[^a-z0-9_]', '', regex=True)
    )
    
    df.columns = normalized_cols
    
    # Log any changes
    changes = {orig: norm for orig, norm in zip(original_cols, normalized_cols) if orig != norm}
    if changes:
        logger.info(f"Normalized column names: {changes}")
    
    return df


def parse_date_column(series: pd.Series, formats: List[str] = None) -> pd.Series:
    """
    Parse a date column with multiple format attempts.
    
    WHY: Date formats vary across sources. Try multiple formats before failing.
    
    Args:
        series: Series containing date strings
        formats: List of date format strings to try
    
    Returns:
        Series with datetime values
    """
    if formats is None:
        formats = DATE_FORMATS
    
    # First, try pandas' smart parser
    try:
        return pd.to_datetime(series, errors='coerce')
    except Exception:
        pass
    
    # Try each format explicitly
    for fmt in formats:
        try:
            result = pd.to_datetime(series, format=fmt, errors='coerce')
            # If most values parsed successfully, use this format
            if result.notna().sum() / len(result) > 0.8:
                logger.debug(f"Successfully parsed dates using format: {fmt}")
                return result
        except Exception:
            continue
    
    # If all else fails, return with coercion
    logger.warning(f"Could not find good date format. Many NaT values may result.")
    return pd.to_datetime(series, errors='coerce')


def convert_to_schema_types(df: pd.DataFrame, schema: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert DataFrame columns to types specified in schema.
    
    WHY: Ensures data types match expectations before validation.
    Catches type mismatches early.
    
    Args:
        df: Input DataFrame
        schema: Schema definition with type specifications
    
    Returns:
        DataFrame with converted types
    """
    df = df.copy()
    column_types = get_column_types(schema)
    
    for col_name, expected_type in column_types.items():
        if col_name not in df.columns:
            logger.warning(f"Expected column '{col_name}' not found in data")
            continue
        
        try:
            if expected_type == "string":
                df[col_name] = df[col_name].astype(str)
                # Replace 'nan' string with actual NaN
                df[col_name] = df[col_name].replace('nan', np.nan)
            
            elif expected_type == "int":
                # Convert to float first to handle NaN, then to int
                df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                # Keep as float if there are NaN values (int doesn't support NaN)
                if df[col_name].isna().any():
                    logger.debug(f"Column '{col_name}' has NaN values, keeping as float")
                else:
                    df[col_name] = df[col_name].astype(int)
            
            elif expected_type == "float":
                df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
            
            elif expected_type == "datetime":
                formats = schema["columns"][col_name].get("format", None)
                if formats:
                    formats = [formats] if isinstance(formats, str) else formats
                df[col_name] = parse_date_column(df[col_name], formats)
            
            elif expected_type == "bool":
                # Handle various boolean representations
                df[col_name] = df[col_name].map({
                    'true': True, 'True': True, 'TRUE': True, '1': True, 1: True,
                    'false': False, 'False': False, 'FALSE': False, '0': False, 0: False,
                })
            
            logger.debug(f"Converted column '{col_name}' to type '{expected_type}'")
        
        except Exception as e:
            logger.error(f"Failed to convert column '{col_name}' to {expected_type}: {e}")
            # Keep original type but log the issue
    
    return df


def detect_schema_drift(df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect differences between actual data and expected schema.
    
    WHY: Schema drift (new columns, missing columns, type changes) can
    indicate upstream data issues or needed pipeline updates.
    
    Args:
        df: DataFrame to check
        schema: Expected schema definition
    
    Returns:
        Dictionary describing any schema drift detected
    """
    drift_report = {
        "has_drift": False,
        "missing_columns": [],
        "unexpected_columns": [],
        "type_mismatches": [],
    }
    
    expected_columns = set(schema["columns"].keys())
    actual_columns = set(df.columns)
    
    # Check for missing columns
    missing = expected_columns - actual_columns
    if missing:
        drift_report["missing_columns"] = list(missing)
        drift_report["has_drift"] = True
        logger.warning(f"Schema drift: Missing columns: {missing}")
    
    # Check for unexpected columns
    unexpected = actual_columns - expected_columns
    if unexpected:
        drift_report["unexpected_columns"] = list(unexpected)
        drift_report["has_drift"] = True
        logger.warning(f"Schema drift: Unexpected columns: {unexpected}")
    
    # Check for type mismatches (after attempting conversion)
    for col_name, expected_type in get_column_types(schema).items():
        if col_name in df.columns:
            actual_type = str(df[col_name].dtype)
            
            # Map pandas dtypes to our schema types
            type_compatible = False
            if expected_type == "string" and actual_type == "object":
                type_compatible = True
            elif expected_type == "int" and "int" in actual_type:
                type_compatible = True
            elif expected_type == "float" and "float" in actual_type:
                type_compatible = True
            elif expected_type == "datetime" and "datetime" in actual_type:
                type_compatible = True
            elif expected_type == "bool" and actual_type == "bool":
                type_compatible = True
            
            if not type_compatible:
                drift_report["type_mismatches"].append({
                    "column": col_name,
                    "expected": expected_type,
                    "actual": actual_type,
                })
    
    if drift_report["type_mismatches"]:
        drift_report["has_drift"] = True
        logger.warning(f"Schema drift: Type mismatches detected")
    
    return drift_report


def ingest_csv_with_schema(file_path, schema_name: str = None) -> tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Main ingestion function: read CSV and apply schema.
    
    Combines:
    1. Robust CSV reading
    2. Column name normalization
    3. Schema-based type conversion
    4. Drift detection
    
    Args:
        file_path: Path to CSV file
        schema_name: Name of schema to use (e.g., 'Weather.csv')
    
    Returns:
        Tuple of (DataFrame, metadata_dict)
    """
    from ingestion.csv_reader import read_csv_robust, get_basic_stats
    from pathlib import Path
    
    file_path = Path(file_path)
    
    # Use filename as schema name if not provided
    if schema_name is None:
        schema_name = file_path.name
    
    logger.info(f"Ingesting {file_path.name} with schema '{schema_name}'")
    
    # Step 1: Read CSV
    df = read_csv_robust(file_path)
    initial_stats = get_basic_stats(df)
    
    # Step 2: Normalize column names
    df = normalize_column_names(df)
    
    # Step 3: Get schema and convert types
    try:
        schema = get_schema(schema_name)
        df = convert_to_schema_types(df, schema)
        
        # Step 4: Detect schema drift
        drift_report = detect_schema_drift(df, schema)
    
    except KeyError as e:
        logger.warning(f"No schema found for {schema_name}: {e}")
        schema = None
        drift_report = {"has_drift": False, "error": str(e)}
    
    # Compile metadata
    metadata = {
        "filename": file_path.name,
        "schema_name": schema_name,
        "ingestion_time": datetime.now().isoformat(),
        "initial_stats": initial_stats,
        "final_stats": get_basic_stats(df),
        "schema_drift": drift_report,
    }
    
    logger.info(f"Successfully ingested {file_path.name}: {len(df)} rows, {len(df.columns)} columns")
    
    return df, metadata
