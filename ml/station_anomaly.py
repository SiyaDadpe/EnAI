"""
Station Region Anomaly Detection using Statistical Methods.

Detects unusual regional patterns and station-level anomalies.
Uses statistical thresholds and regional comparisons.

WHY: Some stations may report consistently unusual data compared to
their regional peers, indicating calibration issues or environmental factors.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from scipy import stats
import joblib
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class StationAnomalyDetector:
    """
    Statistical anomaly detector for station-region data.
    
    Detects stations with unusual characteristics compared to their region.
    """
    
    def __init__(self, z_threshold: float = 3.0):
        """
        Initialize Station Anomaly Detector.
        
        Args:
            z_threshold: Z-score threshold for anomaly detection (typically 2-3)
        """
        self.z_threshold = z_threshold
        self.regional_stats = {}
        self.trained = False
        
    def train(self, station_df: pd.DataFrame, weather_df: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Train statistical model on station-region data.
        
        Args:
            station_df: Station Region DataFrame
            weather_df: Optional Weather DataFrame to get station-level stats
            
        Returns:
            Training statistics and metrics
        """
        logger.info("=" * 80)
        logger.info("TRAINING: Station Region Anomaly Detection (Statistical)")
        logger.info("=" * 80)
        
        df = station_df.copy()
        
        # Calculate regional statistics if weather data provided
        if weather_df is not None:
            logger.info("Calculating station-level statistics from weather data")
            
            # Merge station and weather data
            weather_with_region = weather_df.merge(
                df[['stationcode', 'region', 'region_type']],
                left_on='stationid',
                right_on='stationcode',
                how='left'
            )
            
            # Calculate per-station statistics
            station_stats = weather_with_region.groupby('stationid').agg({
                'temperature': ['mean', 'std', 'count'],
                'rainfall': ['mean', 'std', 'sum'],
            }).reset_index()
            
            station_stats.columns = ['stationid', 'temp_mean', 'temp_std', 'temp_count',
                                      'rain_mean', 'rain_std', 'rain_sum']
            
            # Merge back to station data
            df = df.merge(station_stats, left_on='stationcode', right_on='stationid', how='left')
            
            # Calculate regional statistics
            for region in df['region'].unique():
                if pd.notna(region):
                    region_data = df[df['region'] == region]
                    
                    self.regional_stats[region] = {
                        'n_stations': len(region_data),
                        'temp_mean': region_data['temp_mean'].mean(),
                        'temp_std': region_data['temp_mean'].std(),
                        'rain_mean': region_data['rain_mean'].mean(),
                        'rain_std': region_data['rain_mean'].std(),
                        'observation_count_mean': region_data['temp_count'].mean(),
                        'observation_count_std': region_data['temp_count'].std(),
                    }
            
            logger.info(f"Calculated statistics for {len(self.regional_stats)} regions")
        else:
            # Without weather data, just count stations per region
            for region in df['region'].unique():
                if pd.notna(region):
                    region_data = df[df['region'] == region]
                    self.regional_stats[region] = {
                        'n_stations': len(region_data),
                    }
        
        self.trained = True
        
        stats = {
            'model_type': 'Statistical (Z-score)',
            'n_stations': len(df),
            'n_regions': len(self.regional_stats),
            'z_threshold': self.z_threshold,
            'regions': list(self.regional_stats.keys()),
        }
        
        logger.info(f"Training complete: Analyzed {len(df)} stations across {len(self.regional_stats)} regions")
        
        return stats
    
    def predict(
        self,
        station_df: pd.DataFrame,
        weather_df: pd.DataFrame = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Detect anomalies in station data.
        
        Args:
            station_df: Station Region DataFrame
            weather_df: Optional Weather DataFrame for station-level stats
            
        Returns:
            Tuple of (DataFrame with anomaly columns, prediction statistics)
        """
        if not self.trained:
            raise ValueError("Model must be trained before prediction. Call train() first.")
        
        logger.info("-" * 80)
        logger.info("PREDICTING: Station Region Anomalies")
        logger.info("-" * 80)
        
        df = station_df.copy()
        
        # Initialize anomaly columns
        df['anomaly_score'] = 0.0
        df['is_anomaly'] = False
        df['anomaly_reason'] = "Normal station"
        
        # If weather data provided, calculate station-level stats
        if weather_df is not None:
            weather_with_region = weather_df.merge(
                df[['stationcode', 'region', 'region_type']],
                left_on='stationid',
                right_on='stationcode',
                how='left'
            )
            
            station_stats = weather_with_region.groupby('stationid').agg({
                'temperature': ['mean', 'std', 'count'],
                'rainfall': ['mean', 'std', 'sum'],
            }).reset_index()
            
            station_stats.columns = ['stationid', 'temp_mean', 'temp_std', 'temp_count',
                                      'rain_mean', 'rain_std', 'rain_sum']
            
            df = df.merge(station_stats, left_on='stationcode', right_on='stationid', how='left')
            
            # Calculate anomaly scores based on regional comparison
            for idx, row in df.iterrows():
                region = row['region']
                
                if pd.isna(region) or region not in self.regional_stats:
                    df.at[idx, 'anomaly_score'] = 0.5
                    df.at[idx, 'is_anomaly'] = True
                    df.at[idx, 'anomaly_reason'] = "Unknown or invalid region"
                    continue
                
                regional_stats = self.regional_stats[region]
                z_scores = []
                reason_parts = []
                
                # Check temperature mean
                if pd.notna(row.get('temp_mean')) and regional_stats.get('temp_std', 0) > 0:
                    z_temp = abs(row['temp_mean'] - regional_stats['temp_mean']) / regional_stats['temp_std']
                    z_scores.append(z_temp)
                    
                    if z_temp > self.z_threshold:
                        diff = row['temp_mean'] - regional_stats['temp_mean']
                        reason_parts.append(
                            f"Temperature {diff:+.1f}°C from regional average "
                            f"(z={z_temp:.1f})"
                        )
                
                # Check rainfall mean
                if pd.notna(row.get('rain_mean')) and regional_stats.get('rain_std', 0) > 0:
                    z_rain = abs(row['rain_mean'] - regional_stats['rain_mean']) / regional_stats['rain_std']
                    z_scores.append(z_rain)
                    
                    if z_rain > self.z_threshold:
                        diff = row['rain_mean'] - regional_stats['rain_mean']
                        reason_parts.append(
                            f"Rainfall {diff:+.1f}mm from regional average "
                            f"(z={z_rain:.1f})"
                        )
                
                # Check observation count
                if pd.notna(row.get('temp_count')) and regional_stats.get('observation_count_std', 0) > 0:
                    z_count = abs(row['temp_count'] - regional_stats['observation_count_mean']) / regional_stats['observation_count_std']
                    z_scores.append(z_count)
                    
                    if z_count > self.z_threshold:
                        reason_parts.append(
                            f"Unusual observation count ({int(row['temp_count'])} vs "
                            f"regional avg {int(regional_stats['observation_count_mean'])})"
                        )
                
                # Aggregate anomaly score
                if z_scores:
                    max_z = max(z_scores)
                    # Normalize to 0-1 range (z-scores above 5 are extremely rare)
                    anomaly_score = min(max_z / 5.0, 1.0)
                    df.at[idx, 'anomaly_score'] = anomaly_score
                    df.at[idx, 'is_anomaly'] = max_z > self.z_threshold
                    
                    if reason_parts:
                        df.at[idx, 'anomaly_reason'] = "; ".join(reason_parts)
                    elif df.at[idx, 'is_anomaly']:
                        df.at[idx, 'anomaly_reason'] = f"Statistical outlier (max z-score: {max_z:.2f})"
        else:
            # Without weather data, only flag unknown regions
            for idx, row in df.iterrows():
                region = row['region']
                
                if pd.isna(region) or region not in self.regional_stats:
                    df.at[idx, 'anomaly_score'] = 0.7
                    df.at[idx, 'is_anomaly'] = True
                    df.at[idx, 'anomaly_reason'] = "Unknown or invalid region"
        
        # Statistics
        n_anomalies = df['is_anomaly'].sum()
        anomaly_rate = n_anomalies / len(df)
        
        stats = {
            'n_samples': len(df),
            'n_anomalies': int(n_anomalies),
            'anomaly_rate': float(anomaly_rate),
            'mean_anomaly_score': float(df['anomaly_score'].mean()),
            'max_anomaly_score': float(df['anomaly_score'].max()),
        }
        
        logger.info(f"Prediction complete: {n_anomalies} anomalous stations detected ({anomaly_rate:.2%})")
        
        return df, stats
    
    def save(self, model_path: Path):
        """
        Save trained model to disk.
        
        Args:
            model_path: Path to save the model
        """
        if not self.trained:
            raise ValueError("Cannot save untrained model")
        
        model_data = {
            'regional_stats': self.regional_stats,
            'z_threshold': self.z_threshold,
        }
        
        joblib.dump(model_data, model_path)
        logger.info(f"Model saved to {model_path}")
    
    def load(self, model_path: Path):
        """
        Load trained model from disk.
        
        Args:
            model_path: Path to load the model from
        """
        model_data = joblib.load(model_path)
        
        self.regional_stats = model_data['regional_stats']
        self.z_threshold = model_data['z_threshold']
        self.trained = True
        
        logger.info(f"Model loaded from {model_path}")


def detect_station_anomalies(
    station_input_path: Path,
    weather_input_path: Path,
    output_path: Path,
    model_path: Path,
    z_threshold: float = 3.0
) -> Dict[str, Any]:
    """
    Main function to detect station anomalies.
    
    Args:
        station_input_path: Path to validated station region CSV
        weather_input_path: Path to validated weather CSV
        output_path: Path to save anomaly-flagged station CSV
        model_path: Path to save trained model
        z_threshold: Z-score threshold for anomaly detection
        
    Returns:
        Dictionary with training and prediction statistics
    """
    # Load data
    logger.info(f"Loading station data from {station_input_path}")
    station_df = pd.read_csv(station_input_path)
    logger.info(f"Loaded {len(station_df)} stations")
    
    logger.info(f"Loading weather data from {weather_input_path}")
    weather_df = pd.read_csv(weather_input_path)
    logger.info(f"Loaded {len(weather_df)} weather observations")
    
    # Initialize detector
    detector = StationAnomalyDetector(z_threshold=z_threshold)
    
    # Train
    train_stats = detector.train(station_df, weather_df)
    
    # Predict
    df_output, pred_stats = detector.predict(station_df, weather_df)
    
    # Save model
    detector.save(model_path)
    
    # Save output
    df_output.to_csv(output_path, index=False)
    logger.info(f"Anomaly-flagged station data saved to {output_path}")
    
    return {
        'training': train_stats,
        'prediction': pred_stats,
    }
