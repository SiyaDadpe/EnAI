"""
Weather Anomaly Detection using Isolation Forest.

Detects outliers in temperature and rainfall measurements.
Isolation Forest is effective for high-dimensional data and doesn't assume
normal distribution.

WHY: Weather sensors can malfunction, producing extreme or impossible values.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
from typing import Tuple, Dict, Any, List

logger = logging.getLogger(__name__)


class WeatherAnomalyDetector:
    """
    Isolation Forest-based anomaly detector for weather data.
    """
    
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        """
        Initialize Weather Anomaly Detector.
        
        Args:
            contamination: Expected proportion of outliers (0.01 to 0.5)
            random_state: Random seed for reproducibility
        """
        self.contamination = contamination
        self.random_state = random_state
        self.model = None
        self.scaler = StandardScaler()
        self.base_feature_columns = ['temperature', 'rainfall']
        self.feature_columns = None
        self.trained = False
        
    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Prepare features for anomaly detection.
        
        Args:
            df: Raw weather DataFrame
            
        Returns:
            Tuple of (DataFrame with prepared features, list of feature column names)
        """
        # Create a copy to avoid modifying original
        df_features = df.copy()
        
        # Start with base features
        feature_cols = self.base_feature_columns.copy()
        
        # Fill missing values with median (robust to outliers)
        for col in self.base_feature_columns:
            if col in df_features.columns:
                median_val = df_features[col].median()
                df_features[col] = df_features[col].fillna(median_val)
                logger.info(f"Filled {df_features[col].isna().sum()} missing values in {col} with median: {median_val:.2f}")
        
        # Add derived features
        if 'temperature' in df_features.columns and 'rainfall' in df_features.columns:
            # Temperature-rainfall interaction (unusual combinations)
            df_features['temp_rain_ratio'] = df_features['temperature'] / (df_features['rainfall'] + 1)
            feature_cols.append('temp_rain_ratio')
        
        # Add temporal features if date is available
        if 'observationdate' in df_features.columns:
            df_features['observationdate'] = pd.to_datetime(df_features['observationdate'], errors='coerce')
            df_features['month'] = df_features['observationdate'].dt.month
            df_features['day_of_year'] = df_features['observationdate'].dt.dayofyear
            feature_cols.extend(['month', 'day_of_year'])
        
        return df_features, feature_cols
    
    def train(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Train Isolation Forest model on weather data.
        
        Args:
            df: Weather DataFrame with temperature and rainfall columns
            
        Returns:
            Training statistics and metrics
        """
        logger.info("=" * 80)
        logger.info("TRAINING: Weather Anomaly Detection (Isolation Forest)")
        logger.info("=" * 80)
        
        # Prepare features
        df_features, feature_cols = self.prepare_features(df)
        
        # Store feature columns for later use
        self.feature_columns = feature_cols
        
        # Select feature columns that exist
        available_features = [col for col in self.feature_columns if col in df_features.columns]
        X = df_features[available_features].values
        
        logger.info(f"Training on {len(X)} samples with {len(available_features)} features: {available_features}")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Isolation Forest
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100,
            max_samples='auto',
            n_jobs=-1,
            verbose=0
        )
        
        self.model.fit(X_scaled)
        self.trained = True
        
        # Get predictions on training data
        predictions = self.model.predict(X_scaled)
        scores = self.model.score_samples(X_scaled)
        
        # Statistics
        n_anomalies = (predictions == -1).sum()
        anomaly_rate = n_anomalies / len(predictions)
        
        stats = {
            'model_type': 'Isolation Forest',
            'n_samples': len(X),
            'n_features': len(available_features),
            'features': available_features,
            'contamination': self.contamination,
            'n_anomalies_detected': int(n_anomalies),
            'anomaly_rate': float(anomaly_rate),
            'score_mean': float(scores.mean()),
            'score_std': float(scores.std()),
            'score_min': float(scores.min()),
            'score_max': float(scores.max()),
        }
        
        logger.info(f"Training complete: {n_anomalies} anomalies detected ({anomaly_rate:.2%})")
        logger.info(f"Anomaly score range: [{scores.min():.3f}, {scores.max():.3f}]")
        
        return stats
    
    def predict(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Detect anomalies in weather data.
        
        Args:
            df: Weather DataFrame to analyze
            
        Returns:
            Tuple of (DataFrame with anomaly columns, prediction statistics)
        """
        if not self.trained:
            raise ValueError("Model must be trained before prediction. Call train() first.")
        
        logger.info("-" * 80)
        logger.info("PREDICTING: Weather Anomalies")
        logger.info("-" * 80)
        
        # Prepare features (use same feature columns as training)
        df_features, _ = self.prepare_features(df)
        
        # Select available features (same as training)
        available_features = [col for col in self.feature_columns if col in df_features.columns]
        X = df_features[available_features].values
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Predict
        predictions = self.model.predict(X_scaled)
        scores = self.model.score_samples(X_scaled)
        
        # Convert to anomaly format
        # Isolation Forest: -1 = anomaly, 1 = normal
        # We convert scores to 0-1 range (higher = more anomalous)
        
        # Normalize scores to 0-1 range
        score_min = scores.min()
        score_max = scores.max()
        anomaly_scores = 1 - (scores - score_min) / (score_max - score_min)
        
        # Create output DataFrame
        df_output = df.copy()
        df_output['anomaly_score'] = anomaly_scores
        df_output['is_anomaly'] = predictions == -1
        
        # Generate anomaly reasons
        df_output['anomaly_reason'] = self._generate_reasons(df_output, df_features)
        
        # Statistics
        n_anomalies = df_output['is_anomaly'].sum()
        anomaly_rate = n_anomalies / len(df_output)
        
        stats = {
            'n_samples': len(df_output),
            'n_anomalies': int(n_anomalies),
            'anomaly_rate': float(anomaly_rate),
            'mean_anomaly_score': float(anomaly_scores.mean()),
            'max_anomaly_score': float(anomaly_scores.max()),
        }
        
        logger.info(f"Prediction complete: {n_anomalies} anomalies detected ({anomaly_rate:.2%})")
        
        return df_output, stats
    
    def _generate_reasons(self, df: pd.DataFrame, df_features: pd.DataFrame) -> pd.Series:
        """
        Generate human-readable explanations for anomalies.
        
        Args:
            df: Original DataFrame with anomaly flags
            df_features: Feature DataFrame
            
        Returns:
            Series of reason strings
        """
        reasons = []
        
        for idx, row in df.iterrows():
            if not row['is_anomaly']:
                reasons.append("Normal observation")
                continue
            
            reason_parts = []
            
            # Check temperature
            if pd.notna(row.get('temperature')):
                temp = row['temperature']
                if temp < -50:
                    reason_parts.append(f"Extreme low temperature ({temp:.1f}°C)")
                elif temp > 60:
                    reason_parts.append(f"Extreme high temperature ({temp:.1f}°C)")
                elif temp > 50:
                    reason_parts.append(f"Unusually high temperature ({temp:.1f}°C)")
            
            # Check rainfall
            if pd.notna(row.get('rainfall')):
                rain = row['rainfall']
                if rain > 500:
                    reason_parts.append(f"Extreme rainfall ({rain:.1f}mm)")
                elif rain > 200:
                    reason_parts.append(f"Very high rainfall ({rain:.1f}mm)")
            
            # Check for unusual combinations
            if pd.notna(row.get('temperature')) and pd.notna(row.get('rainfall')):
                temp = row['temperature']
                rain = row['rainfall']
                if temp > 40 and rain > 100:
                    reason_parts.append("Unusual high temp + high rainfall combination")
                elif temp < 0 and rain > 50:
                    reason_parts.append("Unusual freezing temp + high rainfall combination")
            
            if reason_parts:
                reasons.append("; ".join(reason_parts))
            else:
                reasons.append(f"Statistical outlier (score: {row['anomaly_score']:.3f})")
        
        return pd.Series(reasons, index=df.index)
    
    def save(self, model_path: Path):
        """
        Save trained model to disk.
        
        Args:
            model_path: Path to save the model
        """
        if not self.trained:
            raise ValueError("Cannot save untrained model")
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_columns': self.feature_columns,
            'contamination': self.contamination,
            'random_state': self.random_state,
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
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_columns = model_data['feature_columns']
        self.contamination = model_data['contamination']
        self.random_state = model_data['random_state']
        self.trained = True
        
        logger.info(f"Model loaded from {model_path}")


def detect_weather_anomalies(
    input_path: Path,
    output_path: Path,
    model_path: Path,
    contamination: float = 0.05
) -> Dict[str, Any]:
    """
    Main function to detect weather anomalies.
    
    Args:
        input_path: Path to validated weather CSV
        output_path: Path to save anomaly-flagged CSV
        model_path: Path to save trained model
        contamination: Expected proportion of outliers
        
    Returns:
        Dictionary with training and prediction statistics
    """
    # Load data
    logger.info(f"Loading weather data from {input_path}")
    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} weather observations")
    
    # Initialize detector
    detector = WeatherAnomalyDetector(contamination=contamination)
    
    # Train
    train_stats = detector.train(df)
    
    # Predict
    df_output, pred_stats = detector.predict(df)
    
    # Save model
    detector.save(model_path)
    
    # Save output
    df_output.to_csv(output_path, index=False)
    logger.info(f"Anomaly-flagged data saved to {output_path}")
    
    return {
        'training': train_stats,
        'prediction': pred_stats,
    }
