"""
Schema definitions and validation rules for each dataset.

This module defines the expected structure for each input CSV:
- Column names and types
- Required vs optional fields
- Valid value ranges
- Business rules

WHY: Explicit schema definitions enable early detection of data drift
and make the pipeline self-documenting.
"""

from typing import Dict, List, Any


# Weather.csv schema (actual column names from provided dataset)
WEATHER_SCHEMA = {
    "name": "Weather",
    "columns": {
        "stationid": {"type": "string", "required": True},
        "observationdate": {"type": "datetime", "required": True},
        "rainfall": {"type": "float", "required": False, "range": [0, 1000]},
        "rain_unit": {"type": "string", "required": False},
        "temperature": {"type": "float", "required": True, "range": [-50, 60]},
        "temperature_unit": {"type": "string", "required": False},
    },
    "unique_keys": ["stationid", "observationdate"],  # Business key for deduplication
}


# Station_Region.csv schema (actual column names from provided dataset)
STATION_REGION_SCHEMA = {
    "name": "Station_Region",
    "columns": {
        "stationcode": {"type": "string", "required": True},
        "region": {"type": "string", "required": True},
        "region_type": {"type": "string", "required": False},
    },
    "unique_keys": ["stationcode"],
}


# Activity_Logs.csv schema (actual column names from provided dataset)
ACTIVITY_LOGS_SCHEMA = {
    "name": "Activity_Logs",
    "columns": {
        "region": {"type": "string", "required": True},
        "activitydate": {"type": "datetime", "required": True},
        "croptype": {"type": "string", "required": False},
        "irrigationhours": {"type": "float", "required": False, "range": [0, 24]},
        "fertilizer_amount": {"type": "float", "required": False, "range": [0, None]},
    },
    "unique_keys": [],  # No unique key in this dataset
}


# Reference_Units.csv schema (actual column names from provided dataset)
REFERENCE_UNITS_SCHEMA = {
    "name": "Reference_Units",
    "columns": {
        "unit": {"type": "string", "required": True},
        "standard_unit": {"type": "string", "required": False},
        "conversion_factor": {"type": "float", "required": False, "range": [0, None]},
    },
    "unique_keys": ["unit"],
}


# Master schema registry
# WHY: Centralized registry makes it easy to add new datasets and
# ensures consistent validation across the pipeline
SCHEMA_REGISTRY = {
    "Weather.csv": WEATHER_SCHEMA,
    "Station Region.csv": STATION_REGION_SCHEMA,  # Note: space in filename
    "Activity Logs.csv": ACTIVITY_LOGS_SCHEMA,    # Note: space in filename
    "Reference Units.csv": REFERENCE_UNITS_SCHEMA,  # Note: space in filename
}


def get_schema(filename: str) -> Dict[str, Any]:
    """
    Retrieve schema definition for a given CSV filename.
    
    Args:
        filename: Name of the CSV file (e.g., 'Weather.csv')
    
    Returns:
        Schema dictionary with column definitions and rules
    
    Raises:
        KeyError: If schema not found for the given filename
    """
    if filename not in SCHEMA_REGISTRY:
        raise KeyError(f"No schema defined for {filename}. Available: {list(SCHEMA_REGISTRY.keys())}")
    return SCHEMA_REGISTRY[filename]


def get_required_columns(schema: Dict[str, Any]) -> List[str]:
    """Extract list of required column names from schema."""
    return [
        col_name 
        for col_name, col_def in schema["columns"].items() 
        if col_def.get("required", False)
    ]


def get_column_types(schema: Dict[str, Any]) -> Dict[str, str]:
    """Extract column name to type mapping from schema."""
    return {
        col_name: col_def["type"] 
        for col_name, col_def in schema["columns"].items()
    }
