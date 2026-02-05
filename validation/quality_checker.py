"""
Data quality checking utilities.

Implements checks for:
- Missing values
- Duplicate rows
- Data completeness
- Statistical anomalies (basic)

WHY: Beyond schema validation, we need to check for data quality issues
that indicate collection problems or corruption.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Tuple

from config.pipeline_config import MAX_MISSING_RATIO, DUPLICATE_ACTION

logger = logging.getLogger(__name__)


def check_missing_values(df: pd.DataFrame, max_missing_ratio: float = MAX_MISSING_RATIO) -> pd.Series:
    """
    Identify rows with excessive missing values.
    
    WHY: Rows with too many missing values are likely corrupted or incomplete
    and should be quarantined rather than used for analysis.
    
    Args:
        df: DataFrame to check
        max_missing_ratio: Maximum allowed ratio of missing values (0-1)
    
    Returns:
        Boolean Series indicating valid rows (True = acceptable missing values)
    """
    missing_per_row = df.isnull().sum(axis=1)
    missing_ratio = missing_per_row / len(df.columns)
    
    valid_rows = missing_ratio <= max_missing_ratio
    
    excessive_missing = (~valid_rows).sum()
    if excessive_missing > 0:
        logger.warning(
            f"Found {excessive_missing} rows with >{max_missing_ratio:.0%} missing values"
        )
    
    return valid_rows


def check_completeness_by_column(df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate completeness (non-null ratio) for each column.
    
    WHY: Track which columns have the most missing data for governance reporting.
    
    Args:
        df: DataFrame to analyze
        schema: Schema definition to identify required columns
    
    Returns:
        Dictionary mapping column names to completeness ratios
    """
    completeness = {}
    
    for col in df.columns:
        non_null_count = df[col].notna().sum()
        completeness[col] = non_null_count / len(df) if len(df) > 0 else 0.0
    
    # Log warning for required columns with low completeness
    for col_name, col_def in schema.get("columns", {}).items():
        if col_def.get("required", False) and col_name in completeness:
            if completeness[col_name] < 0.9:  # Less than 90% complete
                logger.warning(
                    f"Required column '{col_name}' is only {completeness[col_name]:.1%} complete"
                )
    
    return completeness


def check_exact_duplicates(df: pd.DataFrame, action: str = DUPLICATE_ACTION) -> pd.Series:
    """
    Identify and handle exact duplicate rows.
    
    WHY: Exact duplicates indicate data loading errors or multiple exports
    of the same data.
    
    Args:
        df: DataFrame to check
        action: How to handle duplicates
            - 'flag': Mark all duplicates as invalid
            - 'keep_first': Keep first occurrence, flag rest
            - 'keep_last': Keep last occurrence, flag rest
            - 'drop_all': Flag all occurrences (even first)
    
    Returns:
        Boolean Series indicating valid rows (True = not a duplicate to remove)
    """
    if action == "flag" or action == "drop_all":
        # Mark all duplicates as invalid
        is_duplicate = df.duplicated(keep=False)
        valid_rows = ~is_duplicate
    
    elif action == "keep_first":
        # Keep first occurrence
        is_duplicate = df.duplicated(keep='first')
        valid_rows = ~is_duplicate
    
    elif action == "keep_last":
        # Keep last occurrence
        is_duplicate = df.duplicated(keep='last')
        valid_rows = ~is_duplicate
    
    else:
        logger.warning(f"Unknown duplicate action '{action}', defaulting to 'flag'")
        is_duplicate = df.duplicated(keep=False)
        valid_rows = ~is_duplicate
    
    dup_count = is_duplicate.sum()
    if dup_count > 0:
        logger.warning(f"Found {dup_count} exact duplicate rows (action: {action})")
    
    return valid_rows


def check_null_in_required_fields(df: pd.DataFrame, schema: Dict[str, Any]) -> pd.Series:
    """
    Check for null values in required fields.
    
    WHY: Required fields must have values. Nulls here indicate data collection issues.
    
    Args:
        df: DataFrame to check
        schema: Schema definition with required field specifications
    
    Returns:
        Boolean Series indicating valid rows (True = no nulls in required fields)
    """
    valid_rows = pd.Series([True] * len(df), index=df.index)
    
    for col_name, col_def in schema.get("columns", {}).items():
        if col_def.get("required", False) and col_name in df.columns:
            has_null = df[col_name].isnull()
            if has_null.any():
                logger.warning(
                    f"Required field '{col_name}' has {has_null.sum()} null values"
                )
                valid_rows &= ~has_null
    
    return valid_rows


def get_quality_metrics(df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate comprehensive data quality metrics.
    
    WHY: Quality metrics are essential for governance reporting and
    monitoring pipeline health over time.
    
    Args:
        df: DataFrame to analyze
        schema: Schema definition
    
    Returns:
        Dictionary of quality metrics
    """
    completeness_by_col = check_completeness_by_column(df, schema)
    metrics = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "completeness_by_column": completeness_by_col if isinstance(completeness_by_col, dict) else {},
        "overall_completeness": df.notna().sum().sum() / (len(df) * len(df.columns)) if len(df) > 0 else 0,
        "duplicate_count": int(df.duplicated().sum()),
        "missing_values_total": int(df.isnull().sum().sum()),
    }
    
    # Calculate rows with excessive missing values
    excessive_missing = check_missing_values(df)
    metrics["rows_with_excessive_missing"] = int((~excessive_missing).sum())
    
    # Calculate rows with nulls in required fields
    required_nulls = check_null_in_required_fields(df, schema)
    metrics["rows_with_required_nulls"] = int((~required_nulls).sum())
    
    return metrics


def run_quality_checks(df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run all data quality checks and compile results.
    
    Args:
        df: DataFrame to check
        schema: Schema definition
    
    Returns:
        Quality check report with row-level validity flags
    """
    logger.info(f"Running quality checks on {len(df)} rows")
    
    # Run individual checks
    check_results = {
        "missing_values_check": check_missing_values(df),
        "duplicate_check": check_exact_duplicates(df),
        "required_fields_check": check_null_in_required_fields(df, schema),
    }
    
    # Combine all checks (row is valid only if it passes ALL checks)
    all_checks_valid = pd.Series([True] * len(df), index=df.index)
    for check_name, check_result in check_results.items():
        all_checks_valid &= check_result
        failed_count = (~check_result).sum()
        if failed_count > 0:
            logger.info(f"{check_name}: {failed_count} rows failed")
    
    # Compile report
    report = {
        "total_rows": len(df),
        "passed_all_checks": all_checks_valid.sum(),
        "failed_checks": (~all_checks_valid).sum(),
        "individual_checks": {
            name: int(result.sum()) for name, result in check_results.items()
        },
        "quality_metrics": get_quality_metrics(df, schema),
        "valid_rows": all_checks_valid,
    }
    
    logger.info(
        f"Quality checks complete: {report['passed_all_checks']}/{len(df)} rows passed"
    )
    
    return report
