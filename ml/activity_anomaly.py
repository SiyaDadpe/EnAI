"""
Activity Log Anomaly Detection using Local Outlier Factor (LOF).

Detects unusual patterns in irrigation and fertilizer activities.
LOF is effective for detecting local density-based anomalies.

WHY: Unusual activity patterns may indicate equipment malfunction,
operator error, or fraudulent reporting.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class ActivityAnomalyDetector:
    """
    LOF-based anomaly detector for activity log data.
    """
    
    def __init__(self, contamination: float = 0.05, n_neighbors: int = 20):
        """
        Initialize Activity Anomaly Detector.
        
        Args:
            contamination: Expected proportion of outliers (0.01 to 0.5)
            n_neighbors: Number of neighbors for LOF algorithm
        """
        self.contamination = contamination
        self.n_neighbors = n_neighbors
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = ['irrigationhours', 'fertilizer_amount']
        self.trained = False
        
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for anomaly detection.
        
        Args:
            df: Raw activity log DataFrame
            
        Returns:
            DataFrame with prepared features
        """
        # Create a copy to avoid modifying original
        df_features = df.copy()
        
        # Fill missing numeric values with median
        for col in ['irrigationhours', 'fertilizer_amount']:
            if col in df_features.columns:
                median_val = df_features[col].median()
                df_features[col] = df_features[col].fillna(median_val)
                logger.info(f"Filled {df_features[col].isna().sum()} missing values in {col} with median: {median_val:.2f}")
        
        # Encode categorical variables
        if 'croptype' in df_features.columns:
            if 'croptype' not in self.label_encoders:
                self.label_encoders['croptype'] = LabelEncoder()
                df_features['croptype_encoded'] = self.label_encoders['croptype'].fit_transform(
                    df_features['croptype'].fillna('Unknown')
                )
            else:
                # Handle unseen labels during prediction
                known_classes = set(self.label_encoders['croptype'].classes_)
                df_features['croptype_temp'] = df_features['croptype'].fillna('Unknown')
                df_features['croptype_temp'] = df_features['croptype_temp'].apply(
                    lambda x: x if x in known_classes else 'Unknown'
                )
                df_features['croptype_encoded'] = self.label_encoders['croptype'].transform(
                    df_features['croptype_temp']
                )
            self.feature_columns.append('croptype_encoded')
        
        if 'region' in df_features.columns:
            if 'region' not in self.label_encoders:
                self.label_encoders['region'] = LabelEncoder()
                df_features['region_encoded'] = self.label_encoders['region'].fit_transform(
                    df_features['region'].fillna('Unknown')
                )
            else:
                known_classes = set(self.label_encoders['region'].classes_)
                df_features['region_temp'] = df_features['region'].fillna('Unknown')
                df_features['region_temp'] = df_features['region_temp'].apply(
                    lambda x: x if x in known_classes else 'Unknown'
                )
                df_features['region_encoded'] = self.label_encoders['region'].transform(
                    df_features['region_temp']
                )
            self.feature_columns.append('region_encoded')
        
        # Add derived features
        if 'irrigationhours' in df_features.columns and 'fertilizer_amount' in df_features.columns:
            # Fertilizer per irrigation hour ratio
            df_features['fertilizer_per_hour'] = df_features['fertilizer_amount'] / (df_features['irrigationhours'] + 1)
            self.feature_columns.append('fertilizer_per_hour')
        
        # Add temporal features if date is available
        if 'activitydate' in df_features.columns:
            df_features['activitydate'] = pd.to_datetime(df_features['activitydate'], errors='coerce')
            df_features['month'] = df_features['activitydate'].dt.month.fillna(6)  # Default to mid-year
            df_features['day_of_week'] = df_features['activitydate'].dt.dayofweek.fillna(3)  # Default to Wednesday
            df_features['day_of_month'] = df_features['activitydate'].dt.day.fillna(15)  # Default to mid-month
            self.feature_columns.extend(['month', 'day_of_week', 'day_of_month'])
        
        return df_features
    
    def train(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Train LOF model on activity log data.
        
        Args:
            df: Activity log DataFrame
            
        Returns:
            Training statistics and metrics
        """
        logger.info("=" * 80)
        logger.info("TRAINING: Activity Log Anomaly Detection (LOF)")
        logger.info("=" * 80)
        
        # Prepare features
        df_features = self.prepare_features(df)
        
        # Select feature columns that exist
        available_features = [col for col in self.feature_columns if col in df_features.columns]
        available_features = list(dict.fromkeys(available_features))  # Remove duplicates
        X = df_features[available_features].values
        
        logger.info(f"Training on {len(X)} samples with {len(available_features)} features: {available_features}")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train LOF
        self.model = LocalOutlierFactor(
            n_neighbors=self.n_neighbors,
            contamination=self.contamination,
            novelty=True,  # Enable prediction on new data
            n_jobs=-1
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
            'model_type': 'Local Outlier Factor',
            'n_samples': len(X),
            'n_features': len(available_features),
            'features': available_features,
            'contamination': self.contamination,
            'n_neighbors': self.n_neighbors,
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
        Detect anomalies in activity log data.
        
        Args:
            df: Activity log DataFrame to analyze
            
        Returns:
            Tuple of (DataFrame with anomaly columns, prediction statistics)
        """
        if not self.trained:
            raise ValueError("Model must be trained before prediction. Call train() first.")
        
        logger.info("-" * 80)
        logger.info("PREDICTING: Activity Log Anomalies")
        logger.info("-" * 80)
        
        # Prepare features
        df_features = self.prepare_features(df)
        
        # Select available features (same as training)
        available_features = [col for col in self.feature_columns if col in df_features.columns]
        available_features = list(dict.fromkeys(available_features))  # Remove duplicates
        X = df_features[available_features].values
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Predict
        predictions = self.model.predict(X_scaled)
        scores = self.model.score_samples(X_scaled)
        
        # Convert to anomaly format
        # LOF: -1 = anomaly, 1 = normal
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
                reasons.append("Normal activity pattern")
                continue
            
            reason_parts = []
            
            # Check irrigation hours
            if pd.notna(row.get('irrigationhours')):
                irr = row['irrigationhours']
                if irr > 24:
                    reason_parts.append(f"Excessive irrigation hours ({irr:.1f}h > 24h/day)")
                elif irr > 16:
                    reason_parts.append(f"Very high irrigation hours ({irr:.1f}h/day)")
                elif irr < 0.1 and irr > 0:
                    reason_parts.append(f"Unusually low irrigation hours ({irr:.1f}h/day)")
            
            # Check fertilizer amount
            if pd.notna(row.get('fertilizer_amount')):
                fert = row['fertilizer_amount']
                if fert > 1000:
                    reason_parts.append(f"Extreme fertilizer amount ({fert:.1f}kg)")
                elif fert > 500:
                    reason_parts.append(f"Very high fertilizer amount ({fert:.1f}kg)")
                elif fert < 1 and fert > 0:
                    reason_parts.append(f"Unusually low fertilizer amount ({fert:.1f}kg)")
            
            # Check for unusual ratios
            if pd.notna(row.get('irrigationhours')) and pd.notna(row.get('fertilizer_amount')):
                irr = row['irrigationhours']
                fert = row['fertilizer_amount']
                if irr > 0:
                    ratio = fert / irr
                    if ratio > 100:
                        reason_parts.append(f"Unusual high fertilizer-to-irrigation ratio ({ratio:.1f}kg/h)")
                    elif ratio < 1 and fert > 10:
                        reason_parts.append(f"Unusual low fertilizer-to-irrigation ratio ({ratio:.1f}kg/h)")
            
            # Check for missing dates
            if pd.isna(row.get('activitydate')):
                reason_parts.append("Missing activity date")
            
            if reason_parts:
                reasons.append("; ".join(reason_parts))
            else:
                reasons.append(f"Statistical outlier in local neighborhood (score: {row['anomaly_score']:.3f})")
        
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
            'label_encoders': self.label_encoders,
            'feature_columns': self.feature_columns,
            'contamination': self.contamination,
            'n_neighbors': self.n_neighbors,
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
        self.label_encoders = model_data['label_encoders']
        self.feature_columns = model_data['feature_columns']
        self.contamination = model_data['contamination']
        self.n_neighbors = model_data['n_neighbors']
        self.trained = True
        
        logger.info(f"Model loaded from {model_path}")


def detect_activity_anomalies(
    input_path: Path,
    output_path: Path,
    model_path: Path,
    contamination: float = 0.05,
    n_neighbors: int = 20
) -> Dict[str, Any]:
    """
    Main function to detect activity log anomalies.
    
    Args:
        input_path: Path to validated activity log CSV
        output_path: Path to save anomaly-flagged CSV
        model_path: Path to save trained model
        contamination: Expected proportion of outliers
        n_neighbors: Number of neighbors for LOF
        
    Returns:
        Dictionary with training and prediction statistics
    """
    # Load data
    logger.info(f"Loading activity log data from {input_path}")
    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} activity records")
    
    # Initialize detector
    detector = ActivityAnomalyDetector(contamination=contamination, n_neighbors=n_neighbors)
    
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
