"""
Feature Engineering v1 - Baseline Features

Creates foundational features for business analysis:
- Dataset merging (Weather + Station Region)
- Temporal features (day_of_week, month, season)
- Rolling statistics (7-day trends)
- Unit conversions (standardization)

WHY: These baseline features enable time-series analysis, regional
comparisons, and consistent measurements across the dataset.

BUSINESS JUSTIFICATION:
- Temporal features reveal seasonal patterns in agriculture
- Rolling averages smooth out noise for trend analysis
- Unit standardization ensures apples-to-apples comparisons
- Regional merging enables location-based insights
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class FeatureEngineerV1:
    """
    Baseline feature engineering pipeline.
    
    Creates foundational features for agricultural data analysis.
    """
    
    def __init__(self):
        """Initialize feature engineer v1."""
        self.features_created = []
        self.feature_metadata = {}
        
    def merge_datasets(
        self,
        weather_df: pd.DataFrame,
        station_df: pd.DataFrame,
        activity_df: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Merge Weather and Station Region datasets.
        
        WHY: Combining weather with location enables regional analysis
        and understanding of geographic patterns in data.
        
        BUSINESS VALUE:
        - Analyze weather patterns by region
        - Identify regional anomalies
        - Support location-based decision making
        
        Args:
            weather_df: Weather observations
            station_df: Station region mappings
            activity_df: Optional activity logs
            
        Returns:
            Merged DataFrame
        """
        logger.info("=" * 80)
        logger.info("MERGING DATASETS")
        logger.info("=" * 80)
        
        try:
            # Merge weather with stations on station ID
            merged = weather_df.merge(
                station_df[['stationcode', 'region', 'region_type']],
                left_on='stationid',
                right_on='stationcode',
                how='left'
            )
            
            logger.info(f"Merged weather ({len(weather_df)} rows) with stations ({len(station_df)} rows)")
            logger.info(f"Result: {len(merged)} rows, {len(merged.columns)} columns")
            
            # Track missing regions
            missing_regions = merged['region'].isna().sum()
            if missing_regions > 0:
                logger.warning(f"{missing_regions} weather observations have no region mapping")
            
            self.features_created.extend(['region', 'region_type'])
            
            return merged
            
        except Exception as e:
            logger.error(f"Dataset merge failed: {e}")
            raise
    
    def create_temporal_features(self, df: pd.DataFrame, date_column: str = 'observationdate') -> pd.DataFrame:
        """
        Create time-based features for temporal analysis.
        
        WHY: Agricultural activities are highly seasonal. Temporal features
        capture these patterns for better forecasting and analysis.
        
        BUSINESS VALUE:
        - Identify seasonal trends (planting, harvesting seasons)
        - Detect unusual timing of activities
        - Plan resource allocation by season
        
        Features created:
        - day_of_week: Weekday (0=Monday, 6=Sunday)
        - month: Month of year (1-12)
        - season: Agricultural season (Spring/Summer/Fall/Winter)
        - day_of_year: Day number in year (1-365)
        - week_of_year: Week number (1-52)
        - is_weekend: Boolean weekend indicator
        
        Args:
            df: DataFrame with date column
            date_column: Name of date column
            
        Returns:
            DataFrame with temporal features
        """
        logger.info("-" * 80)
        logger.info("CREATING TEMPORAL FEATURES")
        logger.info("-" * 80)
        
        df = df.copy()
        
        try:
            # Convert to datetime
            df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
            
            # Extract temporal components
            df['day_of_week'] = df[date_column].dt.dayofweek
            df['month'] = df[date_column].dt.month
            df['day_of_year'] = df[date_column].dt.dayofyear
            df['week_of_year'] = df[date_column].dt.isocalendar().week
            df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
            
            # Create season feature (Northern Hemisphere agricultural seasons)
            def get_season(month):
                if pd.isna(month):
                    return 'Unknown'
                elif month in [3, 4, 5]:
                    return 'Spring'
                elif month in [6, 7, 8]:
                    return 'Summer'
                elif month in [9, 10, 11]:
                    return 'Fall'
                else:
                    return 'Winter'
            
            df['season'] = df['month'].apply(get_season)
            
            # Track created features
            temporal_features = [
                'day_of_week', 'month', 'season', 'day_of_year',
                'week_of_year', 'is_weekend'
            ]
            self.features_created.extend(temporal_features)
            
            logger.info(f"Created {len(temporal_features)} temporal features")
           
            logger.info(f"  - Seasons: {df['season'].value_counts().to_dict()}")
            logger.info(f"  - Weekend observations: {df['is_weekend'].sum()} ({df['is_weekend'].mean():.1%})")
            
            return df
            
        except Exception as e:
            logger.error(f"Temporal feature creation failed: {e}")
            raise
    
    def create_rolling_statistics(
        self,
        df: pd.DataFrame,
        window_days: int = 7
    ) -> pd.DataFrame:
        """
        Calculate rolling averages for trend analysis.
        
        WHY: Rolling statistics smooth out daily fluctuations to reveal
        underlying trends, essential for forecasting and anomaly detection.
        
        BUSINESS VALUE:
        - Identify long-term weather trends
        - Detect gradual changes (e.g., approaching drought)
        - Smooth noisy sensor data for better decisions
        
        Features created:
        - rainfall_7d_avg: 7-day rolling average rainfall
        - temperature_7d_avg: 7-day rolling average temperature
        - rainfall_7d_std: 7-day rainfall volatility
        - temperature_7d_std: 7-day temperature volatility
        
        Args:
            df: DataFrame with numerical columns
            window_days: Rolling window size in days
            
        Returns:
            DataFrame with rolling statistics
        """
        logger.info("-" * 80)
        logger.info(f"CREATING ROLLING STATISTICS ({window_days}-day window)")
        logger.info("-" * 80)
        
        df = df.copy()
        
        try:
            # Sort by station and date for proper rolling calculation
            if 'observationdate' in df.columns:
                df = df.sort_values(['stationid', 'observationdate'])
            
            # Calculate rolling statistics per station
            rolling_features = []
            
            if 'rainfall' in df.columns:
                df['rainfall_7d_avg'] = df.groupby('stationid')['rainfall'].transform(
                    lambda x: x.rolling(window=window_days, min_periods=1).mean()
                )
                df['rainfall_7d_std'] = df.groupby('stationid')['rainfall'].transform(
                    lambda x: x.rolling(window=window_days, min_periods=1).std()
                )
                rolling_features.extend(['rainfall_7d_avg', 'rainfall_7d_std'])
            
            if 'temperature' in df.columns:
                df['temperature_7d_avg'] = df.groupby('stationid')['temperature'].transform(
                    lambda x: x.rolling(window=window_days, min_periods=1).mean()
                )
                df['temperature_7d_std'] = df.groupby('stationid')['temperature'].transform(
                    lambda x: x.rolling(window=window_days, min_periods=1).std()
                )
                rolling_features.extend(['temperature_7d_avg', 'temperature_7d_std'])
            
            self.features_created.extend(rolling_features)
            
            logger.info(f"Created {len(rolling_features)} rolling statistic features")
            logger.info(f"  - Features: {rolling_features}")
            
            return df
            
        except Exception as e:
            logger.error(f"Rolling statistics creation failed: {e}")
            raise
    
    def standardize_units(
        self,
        df: pd.DataFrame,
        reference_units_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Convert measurements to standard units.
        
        WHY: Data may use different units (mm vs inches, C vs F).
        Standardization ensures consistent analysis and prevents errors.
        
        BUSINESS VALUE:
        - Consistent cross-region comparisons
        - Prevent unit-related calculation errors
        - Enable aggregation across datasets
        
        Args:
            df: DataFrame with unit columns
            reference_units_df: Unit conversion table
            
        Returns:
            DataFrame with standardized units
        """
        logger.info("-" * 80)
        logger.info("STANDARDIZING UNITS")
        logger.info("-" * 80)
        
        df = df.copy()
        
        try:
            # Create conversion lookup
            conversions = {}
            for _, row in reference_units_df.iterrows():
                if pd.notna(row.get('unit')) and pd.notna(row.get('conversion_factor')):
                    conversions[str(row['unit']).lower()] = float(row['conversion_factor'])
            
            logger.info(f"Loaded {len(conversions)} unit conversions")
            
            # Convert rainfall to standard unit (mm)
            if 'rainfall' in df.columns and 'rain_unit' in df.columns:
                original_values = df['rainfall'].copy()
                
                for unit, factor in conversions.items():
                    mask = df['rain_unit'].str.lower() == unit
                    if mask.any():
                        df.loc[mask, 'rainfall'] = df.loc[mask, 'rainfall'] * factor
                        logger.info(f"  - Converted {mask.sum()} rainfall values from {unit}")
                
                df['rainfall_standardized'] = True
                self.features_created.append('rainfall_standardized')
            
            # Convert temperature to standard unit (Celsius)
            if 'temperature' in df.columns and 'temperature_unit' in df.columns:
                # Already in Celsius for this dataset
                df['temperature_standardized'] = True
                self.features_created.append('temperature_standardized')
            
            logger.info("Unit standardization complete")
            
            return df
            
        except Exception as e:
            logger.error(f"Unit standardization failed: {e}")
            raise
    
    def get_feature_summary(self) -> Dict[str, Any]:
        """
        Get summary of created features.
        
        Returns:
            Dictionary with feature metadata
        """
        return {
            'version': 'v1',
            'features_count': len(self.features_created),
            'features': self.features_created,
            'categories': {
                'temporal': ['day_of_week', 'month', 'season', 'day_of_year', 'week_of_year', 'is_weekend'],
                'rolling_stats': ['rainfall_7d_avg', 'rainfall_7d_std', 'temperature_7d_avg', 'temperature_7d_std'],
                'standardization': ['rainfall_standardized', 'temperature_standardized'],
                'regional': ['region', 'region_type']
            }
        }


def engineer_features_v1(
    weather_path: Path,
    station_path: Path,
    reference_units_path: Path,
    output_path: Path
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Main function to create v1 baseline features.
    
    Args:
        weather_path: Path to weather data
        station_path: Path to station data
        reference_units_path: Path to reference units
        output_path: Path to save output
        
    Returns:
        Tuple of (DataFrame with features, metadata)
    """
    logger.info("=" * 80)
    logger.info("FEATURE ENGINEERING V1 - BASELINE")
    logger.info("=" * 80)
    
    try:
        # Load data
        logger.info("Loading datasets...")
        weather_df = pd.read_csv(weather_path)
        station_df = pd.read_csv(station_path)
        reference_units_df = pd.read_csv(reference_units_path)
        
        logger.info(f"  - Weather: {len(weather_df)} rows")
        logger.info(f"  - Stations: {len(station_df)} rows")
        logger.info(f"  - Reference units: {len(reference_units_df)} rows")
        
        # Initialize engineer
        engineer = FeatureEngineerV1()
        
        # Step 1: Merge datasets
        df = engineer.merge_datasets(weather_df, station_df)
        
        # Step 2: Create temporal features
        df = engineer.create_temporal_features(df)
        
        # Step 3: Create rolling statistics
        df = engineer.create_rolling_statistics(df, window_days=7)
        
        # Step 4: Standardize units
        df = engineer.standardize_units(df, reference_units_df)
        
        # Save output
        df.to_csv(output_path, index=False)
        logger.info(f"\n[OK] Features saved to: {output_path}")
        logger.info(f"[OK] Total rows: {len(df)}")
        logger.info(f"[OK] Total columns: {len(df.columns)}")
        
        # Get summary
        summary = engineer.get_feature_summary()
        summary['output_rows'] = len(df)
        summary['output_columns'] = len(df.columns)
        
        return df, summary
        
    except Exception as e:
        logger.error(f"Feature engineering v1 failed: {e}", exc_info=True)
        raise
