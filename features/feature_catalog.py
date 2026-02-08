"""
Feature Catalog Generator

WHY: Documentation is critical for:
- Understanding what features exist
- Explaining business value to stakeholders
- Onboarding new team members
- Model interpretability and debugging
- Regulatory compliance and auditability

This module generates comprehensive feature documentation with:
- Business justifications
- Technical specifications
- Data types and statistics
- Governance lineage
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
from collections import defaultdict

logger = logging.getLogger(__name__)


class FeatureCatalog:
    """
    Generate comprehensive feature catalog documentation.
    """
    
    # Feature definitions with business justifications
    FEATURE_DEFINITIONS = {
        # V1 TEMPORAL FEATURES
        'day_of_week': {
            'category': 'Temporal',
            'version': 'v1',
            'description': 'Day of week (0=Monday, 6=Sunday)',
            'business_value': 'Captures weekly patterns in weather and agricultural activities. Weekend vs weekday irrigation patterns differ significantly.',
            'data_type': 'integer',
            'range': '0-6'
        },
        'month': {
            'category': 'Temporal',
            'version': 'v1',
            'description': 'Month of year (1-12)',
            'business_value': 'Seasonal patterns are critical for agriculture. Different crops have different growing seasons.',
            'data_type': 'integer',
            'range': '1-12'
        },
        'season': {
            'category': 'Temporal',
            'version': 'v1',
            'description': 'Season category (Spring, Summer, Autumn, Winter)',
            'business_value': 'High-level seasonal patterns for strategic planning. Different seasons require different resource allocation.',
            'data_type': 'categorical',
            'values': ['Spring', 'Summer', 'Autumn', 'Winter']
        },
        'day_of_year': {
            'category': 'Temporal',
            'version': 'v1',
            'description': 'Day of year (1-365/366)',
            'business_value': 'Captures annual cycles and specific date-based patterns (e.g., planting/harvest dates).',
            'data_type': 'integer',
            'range': '1-366'
        },
        'week_of_year': {
            'category': 'Temporal',
            'version': 'v1',
            'description': 'Week of year (1-52/53)',
            'business_value': 'Weekly planning horizon for operations. Aligns with typical agricultural activity schedules.',
            'data_type': 'integer',
            'range': '1-53'
        },
        'is_weekend': {
            'category': 'Temporal',
            'version': 'v1',
            'description': 'Binary flag for weekend (Saturday/Sunday)',
            'business_value': 'Labor costs and availability differ on weekends. Staff scheduling and operational planning.',
            'data_type': 'binary',
            'values': [0, 1]
        },
        
        # V1 ROLLING STATISTICS
        'rainfall_7day_mean': {
            'category': 'Rolling Statistics',
            'version': 'v1',
            'description': '7-day moving average of rainfall',
            'business_value': 'Smooths daily volatility to identify sustained wet periods. Critical for irrigation planning.',
            'data_type': 'float',
            'unit': 'mm'
        },
        'rainfall_7day_std': {
            'category': 'Rolling Statistics',
            'version': 'v1',
            'description': '7-day rolling standard deviation of rainfall',
            'business_value': 'Measures rainfall consistency vs volatility. High std indicates unpredictable weather.',
            'data_type': 'float',
            'unit': 'mm'
        },
        'temperature_7day_mean': {
            'category': 'Rolling Statistics',
            'version': 'v1',
            'description': '7-day moving average of temperature',
            'business_value': 'Captures temperature trends for crop stress prediction. Cold/heat waves affect yield.',
            'data_type': 'float',
            'unit': 'Celsius'
        },
        'temperature_7day_std': {
            'category': 'Rolling Statistics',
            'version': 'v1',
            'description': '7-day rolling standard deviation of temperature',
            'business_value': 'Temperature variability affects crop health. Stable temps are better than fluctuations.',
            'data_type': 'float',
            'unit': 'Celsius'
        },
        
        # V1 UNIT STANDARDIZATION
        'temperature_standardized': {
            'category': 'Standardized Units',
            'version': 'v1',
            'description': 'Temperature converted to standard unit (Celsius)',
            'business_value': 'Ensures consistency across stations with different measurement systems.',
            'data_type': 'float',
            'unit': 'Celsius'
        },
        'rainfall_standardized': {
            'category': 'Standardized Units',
            'version': 'v1',
            'description': 'Rainfall converted to standard unit (mm)',
            'business_value': 'Ensures consistency across stations with different measurement systems.',
            'data_type': 'float',
            'unit': 'mm'
        },
        
        # V2 CROSS-DATASET FEATURES
        'rainfall_irrigation_ratio': {
            'category': 'Cross-Dataset',
            'version': 'v2',
            'description': 'Ratio of rainfall to irrigation hours',
            'business_value': 'Identifies irrigation efficiency. High ratio means over-irrigation given rainfall. Cost savings opportunity.',
            'data_type': 'float',
            'range': '0-inf'
        },
        'temp_irrigation_product': {
            'category': 'Cross-Dataset',
            'version': 'v2',
            'description': 'Temperature multiplied by irrigation hours',
            'business_value': 'Captures water evaporation rate. High temps + high irrigation = water waste.',
            'data_type': 'float',
            'unit': 'Celsius * hours'
        },
        'activity_intensity': {
            'category': 'Cross-Dataset',
            'version': 'v2',
            'description': 'Fertilizer amount divided by irrigation hours',
            'business_value': 'Fertilizer concentration metric. Too high = nutrient burn, too low = waste.',
            'data_type': 'float',
            'unit': 'kg/hour'
        },
        'weather_stress_index': {
            'category': 'Cross-Dataset',
            'version': 'v2',
            'description': 'Combined temperature and rainfall stress indicator',
            'business_value': 'Unified weather stress metric. High values trigger alerts for crop protection measures.',
            'data_type': 'float',
            'range': '0-inf'
        },
        
        # V2 LAG FEATURES
        'rainfall_lag1': {
            'category': 'Lag Features',
            'version': 'v2',
            'description': '1-day lagged rainfall',
            'business_value': 'Yesterday\'s rainfall affects today\'s soil moisture. Irrigation decisions depend on recent rain.',
            'data_type': 'float',
            'unit': 'mm'
        },
        'rainfall_lag3': {
            'category': 'Lag Features',
            'version': 'v2',
            'description': '3-day lagged rainfall',
            'business_value': 'Multi-day rainfall memory in soil. Extended periods without rain trigger irrigation needs.',
            'data_type': 'float',
            'unit': 'mm'
        },
        'rainfall_lag7': {
            'category': 'Lag Features',
            'version': 'v2',
            'description': '7-day lagged rainfall',
            'business_value': 'Weekly rainfall patterns for medium-term planning. Drought detection.',
            'data_type': 'float',
            'unit': 'mm'
        },
        'temperature_lag1': {
            'category': 'Lag Features',
            'version': 'v2',
            'description': '1-day lagged temperature',
            'business_value': 'Temperature trends for frost/heat warnings. Consecutive hot days increase stress.',
            'data_type': 'float',
            'unit': 'Celsius'
        },
        'irrigation_lag1': {
            'category': 'Lag Features',
            'version': 'v2',
            'description': '1-day lagged irrigation hours',
            'business_value': 'Recent irrigation affects today\'s water needs. Prevents over-watering.',
            'data_type': 'float',
            'unit': 'hours'
        },
        
        # V2 REGIONAL AGGREGATIONS
        'regional_rainfall_total': {
            'category': 'Regional Aggregations',
            'version': 'v2',
            'description': 'Total rainfall across all stations in region',
            'business_value': 'Regional water availability. Helps water resource allocation across region.',
            'data_type': 'float',
            'unit': 'mm'
        },
        'regional_temp_mean': {
            'category': 'Regional Aggregations',
            'version': 'v2',
            'description': 'Average temperature across region',
            'business_value': 'Regional climate patterns. Identifies micro-climates within region.',
            'data_type': 'float',
            'unit': 'Celsius'
        },
        'station_vs_regional_rainfall': {
            'category': 'Regional Aggregations',
            'version': 'v2',
            'description': 'Difference between station and regional average rainfall',
            'business_value': 'Identifies stations with unusual rainfall. Sensor calibration or local weather events.',
            'data_type': 'float',
            'unit': 'mm'
        },
        'station_vs_regional_temp': {
            'category': 'Regional Aggregations',
            'version': 'v2',
            'description': 'Difference between station and regional average temperature',
            'business_value': 'Detects micro-climate differences or sensor issues. Quality control metric.',
            'data_type': 'float',
            'unit': 'Celsius'
        },
        
        # V2 ANOMALY INTERACTIONS
        'weather_anomaly_score': {
            'category': 'Anomaly Interactions',
            'version': 'v2',
            'description': 'Anomaly score from ML weather model',
            'business_value': 'Quantifies weather abnormality. Triggers alerts for unusual conditions.',
            'data_type': 'float',
            'range': '0-1'
        },
        'activity_anomaly_score': {
            'category': 'Anomaly Interactions',
            'version': 'v2',
            'description': 'Anomaly score from ML activity model',
            'business_value': 'Identifies unusual farming practices. Quality control for operations.',
            'data_type': 'float',
            'range': '0-1'
        },
        'station_anomaly_flag': {
            'category': 'Anomaly Interactions',
            'version': 'v2',
            'description': 'Binary flag for station-level anomalies',
            'business_value': 'Station-wide issues require immediate investigation (sensor failures, regional events).',
            'data_type': 'binary',
            'values': [0, 1]
        },
        'compound_anomaly_risk': {
            'category': 'Anomaly Interactions',
            'version': 'v2',
            'description': 'Combined risk score from multiple anomaly sources',
            'business_value': 'High-priority alerts when multiple systems show problems simultaneously.',
            'data_type': 'float',
            'range': '0-1'
        }
    }
    
    def __init__(self, features_dir: Path, metadata_path: Path = None):
        """
        Initialize feature catalog.
        
        Args:
            features_dir: Directory with feature files
            metadata_path: Path to governance metadata
        """
        self.features_dir = features_dir
        self.metadata_path = metadata_path or features_dir / "feature_metadata.json"
        self.catalog = {}
        
    def generate_catalog(self) -> Dict[str, Any]:
        """
        Generate complete feature catalog.
        
        Returns:
            Feature catalog dictionary
        """
        logger.info("Generating feature catalog...")
        
        catalog = {
            'generated_at': datetime.now().isoformat(),
            'catalog_version': '1.0',
            'features_by_version': defaultdict(list),
            'features_by_category': defaultdict(list),
            'feature_details': {},
            'statistics': {}
        }
        
        # Load feature data
        v1_path = self.features_dir / "features_v1.csv"
        v2_path = self.features_dir / "features_v2.csv"
        
        # Analyze v1 features
        if v1_path.exists():
            logger.info("Analyzing v1 features...")
            v1_df = pd.read_csv(v1_path)
            v1_features = self._analyze_features(v1_df, 'v1')
            catalog['features_by_version']['v1'] = v1_features
            
            for feature in v1_features:
                if feature in self.FEATURE_DEFINITIONS:
                    catalog['feature_details'][feature] = self.FEATURE_DEFINITIONS[feature]
                    category = self.FEATURE_DEFINITIONS[feature]['category']
                    catalog['features_by_category'][category].append(feature)
        
        # Analyze v2 features
        if v2_path.exists():
            logger.info("Analyzing v2 features...")
            v2_df = pd.read_csv(v2_path)
            v1_cols = set(v1_df.columns) if v1_path.exists() else set()
            v2_only_features = [col for col in v2_df.columns if col not in v1_cols]
            
            catalog['features_by_version']['v2'] = v2_only_features
            
            for feature in v2_only_features:
                if feature in self.FEATURE_DEFINITIONS:
                    catalog['feature_details'][feature] = self.FEATURE_DEFINITIONS[feature]
                    category = self.FEATURE_DEFINITIONS[feature]['category']
                    catalog['features_by_category'][category].append(feature)
        
        # Load governance metadata
        if self.metadata_path.exists():
            with open(self.metadata_path, 'r') as f:
                governance = json.load(f)
                catalog['governance'] = governance
        
        # Generate statistics
        catalog['statistics'] = {
            'total_v1_features': len(catalog['features_by_version']['v1']),
            'total_v2_features': len(catalog['features_by_version']['v2']),
            'total_features': len(catalog['features_by_version']['v1']) + len(catalog['features_by_version']['v2']),
            'categories': list(catalog['features_by_category'].keys()),
            'category_counts': {cat: len(feats) for cat, feats in catalog['features_by_category'].items()}
        }
        
        self.catalog = catalog
        return catalog
    
    def _analyze_features(self, df: pd.DataFrame, version: str) -> List[str]:
        """
        Analyze features in a dataframe.
        
        Args:
            df: Features dataframe
            version: Feature version
            
        Returns:
            List of feature names
        """
        # Exclude original data columns
        exclude_cols = {
            'Date', 'Station ID', 'Temperature', 'Rainfall', 'Region',
            'Activity Type', 'Irrigation Hours', 'Fertilizer Amount'
        }
        
        features = [col for col in df.columns if col not in exclude_cols]
        return features
    
    def save_catalog(self, output_path: Path = None):
        """
        Save catalog to JSON file.
        
        Args:
            output_path: Output file path
        """
        if not self.catalog:
            self.generate_catalog()
        
        output_path = output_path or self.features_dir / "feature_catalog.json"
        
        with open(output_path, 'w') as f:
            json.dump(self.catalog, f, indent=2)
        
        logger.info(f"Feature catalog saved: {output_path}")
    
    def generate_markdown_report(self, output_path: Path = None) -> str:
        """
        Generate human-readable markdown report.
        
        Args:
            output_path: Output file path
            
        Returns:
            Markdown content
        """
        if not self.catalog:
            self.generate_catalog()
        
        lines = []
        lines.append("# Feature Engineering Catalog\n")
        lines.append(f"**Generated:** {self.catalog['generated_at']}\n")
        lines.append(f"**Catalog Version:** {self.catalog['catalog_version']}\n")
        
        # Summary statistics
        lines.append("\n## Summary Statistics\n")
        stats = self.catalog['statistics']
        lines.append(f"- **Total Features:** {stats['total_features']}")
        lines.append(f"- **V1 Features:** {stats['total_v1_features']}")
        lines.append(f"- **V2 Features:** {stats['total_v2_features']}")
        lines.append(f"- **Categories:** {len(stats['categories'])}\n")
        
        # Features by category
        lines.append("\n## Features by Category\n")
        for category, features in self.catalog['features_by_category'].items():
            lines.append(f"\n### {category} ({len(features)} features)\n")
            
            for feature in features:
                if feature in self.catalog['feature_details']:
                    details = self.catalog['feature_details'][feature]
                    lines.append(f"\n#### `{feature}`\n")
                    lines.append(f"- **Version:** {details['version']}")
                    lines.append(f"- **Description:** {details['description']}")
                    lines.append(f"- **Business Value:** {details['business_value']}")
                    lines.append(f"- **Data Type:** {details['data_type']}")
                    
                    if 'unit' in details:
                        lines.append(f"- **Unit:** {details['unit']}")
                    if 'range' in details:
                        lines.append(f"- **Range:** {details['range']}")
                    if 'values' in details:
                        lines.append(f"- **Values:** {details['values']}")
        
        # Governance summary
        if 'governance' in self.catalog:
            lines.append("\n## Governance Summary\n")
            gov = self.catalog['governance']['summary']
            lines.append(f"- **Total Versions:** {gov['total_versions']}")
            lines.append(f"- **Total Transformations:** {gov['total_transformations']}")
            lines.append(f"- **Audit Events:** {gov['total_audit_events']}")
        
        markdown = "\n".join(lines)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(markdown)
            logger.info(f"Markdown report saved: {output_path}")
        
        return markdown


def main():
    """Generate feature catalog."""
    from pathlib import Path
    
    features_dir = Path("data/features_output")
    
    cataloger = FeatureCatalog(features_dir)
    catalog = cataloger.generate_catalog()
    cataloger.save_catalog()
    cataloger.generate_markdown_report(features_dir / "FEATURE_CATALOG.md")
    
    print(f"\n[OK] Feature catalog generated!")
    print(f"  - JSON: {features_dir / 'feature_catalog.json'}")
    print(f"  - Markdown: {features_dir / 'FEATURE_CATALOG.md'}")


if __name__ == "__main__":
    main()
