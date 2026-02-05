"""
Schema validation utilities.

Validates that DataFrames conform to their expected schemas:
- Required columns present
- Data types correct
- Value ranges valid
- Business keys unique

WHY: Schema validation catches data quality issues early, preventing
bad data from propagating through the pipeline.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Tuple

from config.schema_config import get_schema, get_required_columns

logger = logging.getLogger(__name__)


def validate_required_columns(df: pd.DataFrame, schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Check that all required columns are present.
    
    Args:
        df: DataFrame to validate
        schema: Schema definition
    
    Returns:
        Tuple of (is_valid, list_of_missing_columns)
    """
    required_cols = get_required_columns(schema)
    actual_cols = set(df.columns)
    missing_cols = [col for col in required_cols if col not in actual_cols]
    
    is_valid = len(missing_cols) == 0
    
    if not is_valid:
        logger.error(f"Missing required columns: {missing_cols}")
    
    return is_valid, missing_cols


def validate_value_ranges(df: pd.DataFrame, schema: Dict[str, Any]) -> pd.Series:
    """
    Validate that numeric values fall within expected ranges.
    
    WHY: Out-of-range values (e.g., temperature = 1000°C) indicate
    data quality issues or measurement errors.
    
    Args:
        df: DataFrame to validate
        schema: Schema definition with range specifications
    
    Returns:
        Boolean Series indicating which rows have valid ranges (True = valid)
    """
    valid_rows = pd.Series([True] * len(df), index=df.index)
    
    for col_name, col_def in schema["columns"].items():
        if col_name not in df.columns:
            continue
        
        if "range" not in col_def:
            continue
        
        range_spec = col_def["range"]
        min_val, max_val = range_spec
        
        col_data = df[col_name]
        
        # Check min value if specified
        if min_val is not None:
            out_of_range = col_data.notna() & (col_data < min_val)
            if out_of_range.any():
                logger.warning(
                    f"Column '{col_name}': {out_of_range.sum()} values below minimum {min_val}"
                )
                valid_rows &= ~out_of_range
        
        # Check max value if specified
        if max_val is not None:
            out_of_range = col_data.notna() & (col_data > max_val)
            if out_of_range.any():
                logger.warning(
                    f"Column '{col_name}': {out_of_range.sum()} values above maximum {max_val}"
                )
                valid_rows &= ~out_of_range
    
    invalid_count = (~valid_rows).sum()
    if invalid_count > 0:
        logger.warning(f"Found {invalid_count} rows with out-of-range values")
    
    return valid_rows


def validate_unique_keys(df: pd.DataFrame, schema: Dict[str, Any]) -> pd.Series:
    """
    Validate uniqueness of business key combinations.
    
    WHY: Duplicate business keys indicate either data duplication issues
    or problems with our understanding of the data model.
    
    Args:
        df: DataFrame to validate
        schema: Schema definition with unique_keys specification
    
    Returns:
        Boolean Series indicating which rows have unique keys (True = unique)
    """
    if "unique_keys" not in schema or not schema["unique_keys"]:
        return pd.Series([True] * len(df), index=df.index)
    
    unique_key_cols = schema["unique_keys"]
    
    # Check if all key columns exist
    missing_key_cols = [col for col in unique_key_cols if col not in df.columns]
    if missing_key_cols:
        logger.error(f"Unique key columns missing: {missing_key_cols}")
        return pd.Series([False] * len(df), index=df.index)
    
    # Find duplicates based on unique keys
    is_duplicate = df.duplicated(subset=unique_key_cols, keep=False)
    
    if is_duplicate.any():
        dup_count = is_duplicate.sum()
        logger.warning(
            f"Found {dup_count} rows with duplicate keys on {unique_key_cols}"
        )
    
    return ~is_duplicate


def validate_data_types(df: pd.DataFrame, schema: Dict[str, Any]) -> pd.Series:
    """
    Validate that columns have the expected data types after conversion.
    
    WHY: Type validation catches conversion failures (e.g., 'abc' parsed as date).
    
    Args:
        df: DataFrame to validate
        schema: Schema definition with type specifications
    
    Returns:
        Boolean Series indicating which rows have valid types (True = valid)
    """
    valid_rows = pd.Series([True] * len(df), index=df.index)
    
    for col_name, col_def in schema["columns"].items():
        if col_name not in df.columns:
            continue
        
        expected_type = col_def["type"]
        
        # For datetime and numeric types, check for NaT/NaN from failed conversions
        if expected_type == "datetime":
            # Only flag as invalid if value was non-null but failed to parse
            failed_conversion = df[col_name].isna()
            if failed_conversion.any():
                logger.debug(f"Column '{col_name}': {failed_conversion.sum()} failed datetime conversions")
        
        elif expected_type in ["int", "float"]:
            # Check for non-numeric values (would be NaN after conversion)
            # But only if the original field was required and non-null
            if col_def.get("required", False):
                invalid_values = df[col_name].isna()
                valid_rows &= ~invalid_values
    
    invalid_count = (~valid_rows).sum()
    if invalid_count > 0:
        logger.warning(f"Found {invalid_count} rows with type validation failures")
    
    return valid_rows


def validate_schema(df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive schema validation.
    
    Runs all validation checks and compiles results.
    
    Args:
        df: DataFrame to validate
        schema: Schema definition
    
    Returns:
        Validation report with results and row-level flags
    """
    logger.info(f"Running schema validation for {schema['name']}")
    
    validation_report = {
        "schema_name": schema["name"],
        "total_rows": len(df),
        "validation_passed": True,
        "errors": [],
        "warnings": [],
    }
    
    # 1. Check required columns
    cols_valid, missing_cols = validate_required_columns(df, schema)
    if not cols_valid:
        validation_report["validation_passed"] = False
        validation_report["errors"].append(f"Missing required columns: {missing_cols}")
        # Can't continue validation without required columns
        return validation_report
    
    # 2. Validate value ranges
    range_valid = validate_value_ranges(df, schema)
    range_invalid_count = (~range_valid).sum()
    if range_invalid_count > 0:
        validation_report["warnings"].append(
            f"{range_invalid_count} rows have out-of-range values"
        )
    
    # 3. Validate unique keys
    unique_valid = validate_unique_keys(df, schema)
    duplicate_count = (~unique_valid).sum()
    if duplicate_count > 0:
        validation_report["warnings"].append(
            f"{duplicate_count} rows have duplicate business keys"
        )
    
    # 4. Validate data types
    type_valid = validate_data_types(df, schema)
    type_invalid_count = (~type_valid).sum()
    if type_invalid_count > 0:
        validation_report["warnings"].append(
            f"{type_invalid_count} rows have type validation failures"
        )
    
    # Combine all validation flags
    # Row is valid only if it passes ALL checks
    all_valid = range_valid & unique_valid & type_valid
    validation_report["valid_rows"] = all_valid
    validation_report["valid_count"] = all_valid.sum()
    validation_report["invalid_count"] = (~all_valid).sum()
    
    logger.info(
        f"Validation complete: {validation_report['valid_count']}/{len(df)} rows valid"
    )
    
    return validation_report
