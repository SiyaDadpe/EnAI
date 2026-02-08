"""
Feature Engineering v2 - Advanced Features

Creates sophisticated features for deeper business insights:
- Cross-dataset features (weather impact on irrigation)
- Lag features (temporal dependencies)
- Regional aggregations (area-wide patterns)
- Anomaly interaction features (flag combinations)

WHY: Advanced features capture complex relationships between weather,
location, and agricultural activities for predictive modeling.

BUSINESS JUSTIFICATION:
- Cross-dataset features link cause (weather) to effect (irrigation needs)
- Lag features capture delayed responses (rainfall yesterday → irrigation today)
- Regional aggregations reveal area-wide trends
- Anomaly interactions identify compound risks
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class FeatureEngineerV2:
    """
    Advanced feature engineering pipeline.
    
    Builds on v1 with sophisticated cross-dataset and interaction features.
    """
    
    def __init__(self):
        """Initialize feature engineer v2."""
        self.features_created = []
        self.feature_metadata = {}
        
    def create_cross_dataset_features(
        self,
        weather_df: pd.DataFrame,
        activity_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Create features linking weather to agricultural activities.
        
        WHY: Weather directly impacts irrigation and fertilizer needs.
        These features enable predictive models for resource planning.
        
        BUSINESS VALUE:
        - Predict irrigation needs based on weather
        - Optimize fertilizer application timing
        - Reduce water waste and over-irrigation
        
        Features created:
        - rainfall_irrigation_ratio: Rain vs irrigation comparison
        - temp_irrigation_correlation: Heat drives irrigation needs
        - activity_intensity: Combined resource usage metric
        
        Args:
            weather_df: Weather data with v1 features
            activity_df: Activity log data (anomaly-flagged)
            
        Returns:
            Combined DataFrame with cross-dataset features
        """
        logger.info("=" * 80)
        logger.info("CREATING CROSS-DATASET FEATURES")
        logger.info("=" * 80)
        
        try:
            # Merge on region + date
            weather_df['observationdate'] = pd.to_datetime(weather_df['observationdate'])
            activity_df['activitydate'] = pd.to_datetime(activity_df['activitydate'])
            
            # Aggregate weather by region and date
            weather_agg = weather_df.groupby(['region', 'observationdate']).agg({
                'rainfall': 'mean',
                'temperature': 'mean',
                'rainfall_7d_avg': 'mean'
            }).reset_index()
            
            # Aggregate activities by region and date
            activity_agg = activity_df.groupby(['region', 'activitydate']).agg({
                'irrigationhours': 'sum',
                'fertilizer_amount': 'sum'
            }).reset_index()
            
            # Merge weather with activities
            merged = activity_agg.merge(
                weather_agg,
                left_on=['region', 'activitydate'],
                right_on=['region', 'observationdate'],
                how='left'
            )
            
            # Create cross-dataset features
            
            # 1. Rainfall-Irrigation Ratio
            # High ratio = lots of rain, less irrigation needed (efficient)
            merged['rainfall_irrigation_ratio'] = merged['rainfall'] / (merged['irrigationhours'] + 1)
            
            # 2. Temperature-Irrigation Correlation
            # Higher temp usually requires more irrigation
            merged['temp_irrigation_product'] = merged['temperature'] * merged['irrigationhours']
            
            # 3. Activity Intensity Score
            # Combined metric of resource usage
            merged['activity_intensity'] = (
                merged['irrigationhours'] / merged['irrigationhours'].max() * 0.5 +
                merged['fertilizer_amount'] / merged['fertilizer_amount'].max() * 0.5
            )
            
            # 4. Weather Stress Index
            # High temp + low rain = stress conditions
            merged['weather_stress_index'] = (
                (merged['temperature'] - merged['temperature'].mean()) / merged['temperature'].std() -
                (merged['rainfall'] - merged['rainfall'].mean()) / merged['rainfall'].std()
            )
            
            cross_features = [
                'rainfall_irrigation_ratio',
                'temp_irrigation_product',
                'activity_intensity',
                'weather_stress_index'
            ]
            self.features_created.extend(cross_features)
            
            logger.info(f"Created {len(cross_features)} cross-dataset features")
            logger.info(f"  - Merged {len(merged)} region-date combinations")
            logger.info(f"  - Features: {cross_features}")
            
            return merged
            
        except Exception as e:
            logger.error(f"Cross-dataset feature creation failed: {e}")
            raise
    
    def create_lag_features(
        self,
        df: pd.DataFrame,
        lag_days: list = [1, 3, 7]
    ) -> pd.DataFrame:
        """
        Create lag features for temporal dependencies.
        
        WHY: Agricultural decisions often depend on recent history.
        Yesterday's rainfall affects today's irrigation needs.
        
        BUSINESS VALUE:
        - Capture delayed weather effects
        - Better irrigation scheduling
        - Predictive models for resource planning
        
        Features created:
        - rainfall_lag_1d: Yesterday's rainfall
        - rainfall_lag_3d: 3 days ago rainfall
        - rainfall_lag_7d: Last week's rainfall
        - temperature_lag_1d: Yesterday's temperature
        
        Args:
            df: DataFrame sorted by date
            lag_days: List of lag periods in days
            
        Returns:
            DataFrame with lag features
        """
        logger.info("-" * 80)
        logger.info("CREATING LAG FEATURES")
        logger.info("-" * 80)
        
        df = df.copy()
        
        try:
            # Sort by region and date
            if 'region' in df.columns and 'observationdate' in df.columns:
                df = df.sort_values(['region', 'observationdate'])
            
            lag_features = []
            
            # Create lag features for rainfall
            if 'rainfall' in df.columns:
                for lag in lag_days:
                    col_name = f'rainfall_lag_{lag}d'
                    df[col_name] = df.groupby('region')['rainfall'].shift(lag)
                    lag_features.append(col_name)
            
            # Create lag features for temperature
            if 'temperature' in df.columns:
                for lag in [1, 7]:  # Just 1 and 7 day lags for temp
                    col_name = f'temperature_lag_{lag}d'
                    df[col_name] = df.groupby('region')['temperature'].shift(lag)
                    lag_features.append(col_name)
            
            # Create lag features for irrigation (if exists)
            if 'irrigationhours' in df.columns:
                df['irrigation_lag_1d'] = df.groupby('region')['irrigationhours'].shift(1)
                lag_features.append('irrigation_lag_1d')
            
            self.features_created.extend(lag_features)
            
            logger.info(f"Created {len(lag_features)} lag features")
            logger.info(f"  - Lag periods: {lag_days} days")
            logger.info(f"  - Features: {lag_features}")
            
            return df
            
        except Exception as e:
            logger.error(f"Lag feature creation failed: {e}")
            raise
    
    def create_regional_aggregations(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Create regional aggregation features.
        
        WHY: Regional patterns reveal area-wide trends that individual
        stations might miss. Essential for regional planning.
        
        BUSINESS VALUE:
        - Identify regional drought/flood conditions
        - Plan region-wide interventions
        - Compare station performance to regional average
        
        Features created:
        - regional_rainfall_total: Total rainfall in region
        - regional_temperature_avg: Average regional temperature
        - regional_station_count: Number of stations in region
        - station_vs_regional_rainfall: Deviation from regional average
        
        Args:
            df: DataFrame with regional data
            
        Returns:
            DataFrame with regional aggregation features
        """
        logger.info("-" * 80)
        logger.info("CREATING REGIONAL AGGREGATIONS")
        logger.info("-" * 80)
        
        df = df.copy()
        
        try:
            # Calculate regional statistics
            regional_stats = df.groupby('region').agg({
                'rainfall': ['sum', 'mean', 'std'],
                'temperature': ['mean', 'std'],
                'stationid': 'nunique'
            }).reset_index()
            
            regional_stats.columns = [
                'region',
                'regional_rainfall_total',
                'regional_rainfall_mean',
                'regional_rainfall_std',
                'regional_temperature_mean',
                'regional_temperature_std',
                'regional_station_count'
            ]
            
            # Merge back to main dataframe
            df = df.merge(regional_stats, on='region', how='left')
            
            # Create deviation features
            df['station_vs_regional_rainfall'] = (
                df['rainfall'] - df['regional_rainfall_mean']
            ) / (df['regional_rainfall_std'] + 1e-6)
            
            df['station_vs_regional_temp'] = (
                df['temperature'] - df['regional_temperature_mean']
            ) / (df['regional_temperature_std'] + 1e-6)
            
            regional_features = [
                'regional_rainfall_total',
                'regional_rainfall_mean',
                'regional_temperature_mean',
                'regional_station_count',
                'station_vs_regional_rainfall',
                'station_vs_regional_temp'
            ]
            self.features_created.extend(regional_features)
            
            logger.info(f"Created {len(regional_features)} regional aggregation features")
            logger.info(f"  - Regions analyzed: {df['region'].nunique()}")
            logger.info(f"  - Features: {regional_features}")
            
            return df
            
        except Exception as e:
            logger.error(f"Regional aggregation failed: {e}")
            raise
    
    def create_anomaly_interactions(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Create features from anomaly flags.
        
        WHY: Multiple simultaneous anomalies indicate compound risks
        requiring immediate attention.
        
        BUSINESS VALUE:
        - Identify high-risk situations (multiple anomalies)
        - Prioritize maintenance and interventions
        - Risk scoring for decision support
        
        Features created:
        - has_anomaly: Binary anomaly flag
        - anomaly_severity: Risk score (0-5 scale)
        - anomaly_count: Number of anomalies in timewindow
        - compound_risk: Multiple anomalies indicator
        
        Args:
            df: DataFrame with anomaly columns
            
        Returns:
            DataFrame with anomaly interaction features
        """
        logger.info("-" * 80)
        logger.info("CREATING ANOMALY INTERACTION FEATURES")
        logger.info("-" * 80)
        
        df = df.copy()
        
        try:
            anomaly_features = []
            
            # Binary anomaly indicator
            if 'is_anomaly' in df.columns:
                df['has_anomaly'] = df['is_anomaly'].astype(int)
                anomaly_features.append('has_anomaly')
            
            # Anomaly severity based on score
            if 'anomaly_score' in df.columns:
                df['anomaly_severity'] = pd.cut(
                    df['anomaly_score'],
                    bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
                    labels=['Very Low', 'Low', 'Medium', 'High', 'Critical']
                )
                anomaly_features.append('anomaly_severity')
            
            # Rolling anomaly count (7-day window)
            if 'has_anomaly' in df.columns and 'stationid' in df.columns:
                df = df.sort_values(['stationid', 'observationdate'])
                df['anomaly_count_7d'] = df.groupby('stationid')['has_anomaly'].transform(
                    lambda x: x.rolling(window=7, min_periods=1).sum()
                )
                anomaly_features.append('anomaly_count_7d')
                
                # Compound risk indicator (multiple anomalies in window)
                df['compound_risk'] = (df['anomaly_count_7d'] >= 3).astype(int)
                anomaly_features.append('compound_risk')
            
            self.features_created.extend(anomaly_features)
            
            logger.info(f"Created {len(anomaly_features)} anomaly interaction features")
            logger.info(f"  - Stations with compound risk: {df['compound_risk'].sum() if 'compound_risk' in df.columns else 0}")
            logger.info(f"  - Features: {anomaly_features}")
            
            return df
            
        except Exception as e:
            logger.error(f"Anomaly interaction feature creation failed: {e}")
            raise
    
    def get_feature_summary(self) -> Dict[str, Any]:
        """
        Get summary of created features.
        
        Returns:
            Dictionary with feature metadata
        """
        return {
            'version': 'v2',
            'features_count': len(self.features_created),
            'features': self.features_created,
            'categories': {
                'cross_dataset': [
                    'rainfall_irrigation_ratio',
                    'temp_irrigation_product',
                    'activity_intensity',
                    'weather_stress_index'
                ],
                'lag_features': [f for f in self.features_created if 'lag' in f],
                'regional_aggregations': [f for f in self.features_created if 'regional' in f or 'station_vs' in f],
                'anomaly_interactions': [f for f in self.features_created if 'anomaly' in f or 'compound' in f]
            }
        }


def engineer_features_v2(
    features_v1_df: pd.DataFrame,
    activity_anomaly_path: Path,
    output_path: Path
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Main function to create v2 advanced features.
    
    Args:
        features_v1_df: DataFrame with v1 features
        activity_anomaly_path: Path to activity anomaly data
        output_path: Path to save output
        
    Returns:
        Tuple of (DataFrame with features, metadata)
    """
    logger.info("=" * 80)
    logger.info("FEATURE ENGINEERING V2 - ADVANCED")
    logger.info("=" * 80)
    
    try:
        # Load activity data
        logger.info("Loading activity anomaly data...")
        activity_df = pd.read_csv(activity_anomaly_path)
        logger.info(f"  - Activity logs: {len(activity_df)} rows")
        
        # Initialize engineer
        engineer = FeatureEngineerV2()
        
        # Start with v1 features
        df = features_v1_df.copy()
        
        # Step 1: Create lag features
        df = engineer.create_lag_features(df, lag_days=[1, 3, 7])
        
        # Step 2: Create regional aggregations
        df = engineer.create_regional_aggregations(df)
        
        # Step 3: Create anomaly interactions
        if 'is_anomaly' in df.columns:
            df = engineer.create_anomaly_interactions(df)
        
        # Step 4: Create cross-dataset features (separate output)
        cross_df = engineer.create_cross_dataset_features(df, activity_df)
        
        # Save main output
        df.to_csv(output_path, index=False)
        logger.info(f"\n[OK] Features saved to: {output_path}")
        logger.info(f"[OK] Total rows: {len(df)}")
        logger.info(f"[OK] Total columns: {len(df.columns)}")
        
        # Save cross-dataset features separately
        cross_output_path = output_path.parent / f"{output_path.stem}_cross_dataset.csv"
        cross_df.to_csv(cross_output_path, index=False)
        logger.info(f"[OK] Cross-dataset features saved to: {cross_output_path}")
        
        # Get summary
        summary = engineer.get_feature_summary()
        summary['output_rows'] = len(df)
        summary['output_columns'] = len(df.columns)
        summary['cross_dataset_rows'] = len(cross_df)
        
        return df, summary
        
    except Exception as e:
        logger.error(f"Feature engineering v2 failed: {e}", exc_info=True)
        raise
