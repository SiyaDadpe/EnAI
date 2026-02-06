"""
ML Pipeline Runner - Anomaly Detection System

Orchestrates the complete ML anomaly detection workflow:
1. Load validated datasets from data engineering
2. Train anomaly detection models
3. Generate anomaly predictions
4. Save models and flagged datasets
5. Create performance reports

This is the ML team's main entry point - does NOT modify any data engineering code.

Usage:
    python ml_pipeline.py
"""

import sys
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
from utils.logger import setup_logging, get_logger

# Import ML modules
from ml.weather_anomaly import detect_weather_anomalies
from ml.activity_anomaly import detect_activity_anomalies
from ml.station_anomaly import detect_station_anomalies

# Setup logging
setup_logging()
logger = get_logger(__name__)


class MLPipeline:
    """
    ML Pipeline orchestrator for anomaly detection.
    
    Runs all anomaly detection models and generates reports.
    """
    
    def __init__(self):
        """Initialize ML pipeline."""
        # Input paths (from data engineering output)
        self.data_dir = PROJECT_ROOT / "data" / "output"
        self.weather_input = self.data_dir / "validated_Weather.csv"
        self.activity_input = self.data_dir / "validated_Activity Logs.csv"
        self.station_input = self.data_dir / "validated_Station Region.csv"
        
        # Output paths (ML team's workspace)
        self.output_dir = PROJECT_ROOT / "data" / "ml_output"
        self.models_dir = PROJECT_ROOT / "models"
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Results storage
        self.results = {}
        
    def run(self):
        """
        Run complete ML pipeline.
        """
        logger.info("=" * 80)
        logger.info("ML PIPELINE - ANOMALY DETECTION")
        logger.info("=" * 80)
        logger.info(f"Start time: {datetime.now().isoformat()}")
        
        start_time = datetime.now()
        
        try:
            # 1. Weather anomaly detection
            logger.info("\n" + "=" * 80)
            logger.info("STEP 1: Weather Anomaly Detection (Isolation Forest)")
            logger.info("=" * 80)
            weather_results = self._detect_weather_anomalies()
            self.results['weather'] = weather_results
            
            # 2. Activity log anomaly detection
            logger.info("\n" + "=" * 80)
            logger.info("STEP 2: Activity Log Anomaly Detection (LOF)")
            logger.info("=" * 80)
            activity_results = self._detect_activity_anomalies()
            self.results['activity'] = activity_results
            
            # 3. Station anomaly detection
            logger.info("\n" + "=" * 80)
            logger.info("STEP 3: Station Region Anomaly Detection (Statistical)")
            logger.info("=" * 80)
            station_results = self._detect_station_anomalies()
            self.results['station'] = station_results
            
            # 4. Generate performance report
            logger.info("\n" + "=" * 80)
            logger.info("STEP 4: Generating Performance Report")
            logger.info("=" * 80)
            self._generate_report()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info("\n" + "=" * 80)
            logger.info("ML PIPELINE COMPLETE")
            logger.info("=" * 80)
            logger.info(f"End time: {end_time.isoformat()}")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info(f"\nOutputs saved to: {self.output_dir}")
            logger.info(f"Models saved to: {self.models_dir}")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise
    
    def _detect_weather_anomalies(self) -> Dict[str, Any]:
        """
        Run weather anomaly detection.
        """
        output_path = self.output_dir / "anomaly_flagged_Weather.csv"
        model_path = self.models_dir / "weather_isolation_forest.pkl"
        
        results = detect_weather_anomalies(
            input_path=self.weather_input,
            output_path=output_path,
            model_path=model_path,
            contamination=0.05  # Expect 5% anomalies
        )
        
        logger.info(f"[OK] Weather anomalies detected: {results['prediction']['n_anomalies']}")
        logger.info(f"[OK] Output saved: {output_path}")
        logger.info(f"[OK] Model saved: {model_path}")
        
        return results
    
    def _detect_activity_anomalies(self) -> Dict[str, Any]:
        """
        Run activity log anomaly detection.
        """
        output_path = self.output_dir / "anomaly_flagged_Activity Logs.csv"
        model_path = self.models_dir / "activity_lof.pkl"
        
        results = detect_activity_anomalies(
            input_path=self.activity_input,
            output_path=output_path,
            model_path=model_path,
            contamination=0.05,  # Expect 5% anomalies
            n_neighbors=20
        )
        
        logger.info(f"[OK] Activity anomalies detected: {results['prediction']['n_anomalies']}")
        logger.info(f"[OK] Output saved: {output_path}")
        logger.info(f"[OK] Model saved: {model_path}")
        
        return results
    
    def _detect_station_anomalies(self) -> Dict[str, Any]:
        """
        Run station anomaly detection.
        """
        output_path = self.output_dir / "anomaly_flagged_Station Region.csv"
        model_path = self.models_dir / "station_statistical.pkl"
        
        results = detect_station_anomalies(
            station_input_path=self.station_input,
            weather_input_path=self.weather_input,
            output_path=output_path,
            model_path=model_path,
            z_threshold=3.0  # 3 standard deviations
        )
        
        logger.info(f"[OK] Station anomalies detected: {results['prediction']['n_anomalies']}")
        logger.info(f"[OK] Output saved: {output_path}")
        logger.info(f"[OK] Model saved: {model_path}")
        
        return results
    
    def _generate_report(self):
        """
        Generate comprehensive performance report.
        """
        report = {
            'pipeline_metadata': {
                'generated_at': datetime.now().isoformat(),
                'ml_pipeline_version': '1.0',
                'team': 'ML Team - Anomaly Detection',
            },
            'models': {
                'weather': {
                    'model_type': self.results['weather']['training']['model_type'],
                    'algorithm': 'Isolation Forest',
                    'contamination': self.results['weather']['training']['contamination'],
                    'n_features': self.results['weather']['training']['n_features'],
                    'features': self.results['weather']['training']['features'],
                },
                'activity': {
                    'model_type': self.results['activity']['training']['model_type'],
                    'algorithm': 'Local Outlier Factor',
                    'contamination': self.results['activity']['training']['contamination'],
                    'n_neighbors': self.results['activity']['training']['n_neighbors'],
                    'n_features': self.results['activity']['training']['n_features'],
                    'features': self.results['activity']['training']['features'],
                },
                'station': {
                    'model_type': self.results['station']['training']['model_type'],
                    'algorithm': 'Statistical Z-Score',
                    'z_threshold': self.results['station']['training']['z_threshold'],
                    'n_regions': self.results['station']['training']['n_regions'],
                },
            },
            'performance': {
                'weather': {
                    'total_samples': self.results['weather']['prediction']['n_samples'],
                    'anomalies_detected': self.results['weather']['prediction']['n_anomalies'],
                    'anomaly_rate': self.results['weather']['prediction']['anomaly_rate'],
                    'mean_anomaly_score': self.results['weather']['prediction']['mean_anomaly_score'],
                },
                'activity': {
                    'total_samples': self.results['activity']['prediction']['n_samples'],
                    'anomalies_detected': self.results['activity']['prediction']['n_anomalies'],
                    'anomaly_rate': self.results['activity']['prediction']['anomaly_rate'],
                    'mean_anomaly_score': self.results['activity']['prediction']['mean_anomaly_score'],
                },
                'station': {
                    'total_samples': self.results['station']['prediction']['n_samples'],
                    'anomalies_detected': self.results['station']['prediction']['n_anomalies'],
                    'anomaly_rate': self.results['station']['prediction']['anomaly_rate'],
                    'mean_anomaly_score': self.results['station']['prediction']['mean_anomaly_score'],
                },
            },
            'summary': {
                'total_datasets_processed': 3,
                'total_anomalies_detected': (
                    self.results['weather']['prediction']['n_anomalies'] +
                    self.results['activity']['prediction']['n_anomalies'] +
                    self.results['station']['prediction']['n_anomalies']
                ),
                'output_files': [
                    'anomaly_flagged_Weather.csv',
                    'anomaly_flagged_Activity Logs.csv',
                    'anomaly_flagged_Station Region.csv',
                ],
                'model_files': [
                    'weather_isolation_forest.pkl',
                    'activity_lof.pkl',
                    'station_statistical.pkl',
                ],
            },
        }
        
        # Save JSON report
        report_path = self.output_dir / "ml_performance_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"[OK] Performance report saved: {report_path}")
        
        # Print summary to console
        logger.info("\n" + "=" * 80)
        logger.info("PERFORMANCE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"\nWeather Data:")
        logger.info(f"  - Total samples: {report['performance']['weather']['total_samples']:,}")
        logger.info(f"  - Anomalies: {report['performance']['weather']['anomalies_detected']:,} "
                   f"({report['performance']['weather']['anomaly_rate']:.2%})")
        logger.info(f"  - Mean anomaly score: {report['performance']['weather']['mean_anomaly_score']:.3f}")
        
        logger.info(f"\nActivity Logs:")
        logger.info(f"  - Total samples: {report['performance']['activity']['total_samples']:,}")
        logger.info(f"  - Anomalies: {report['performance']['activity']['anomalies_detected']:,} "
                   f"({report['performance']['activity']['anomaly_rate']:.2%})")
        logger.info(f"  - Mean anomaly score: {report['performance']['activity']['mean_anomaly_score']:.3f}")
        
        logger.info(f"\nStation Regions:")
        logger.info(f"  - Total samples: {report['performance']['station']['total_samples']:,}")
        logger.info(f"  - Anomalies: {report['performance']['station']['anomalies_detected']:,} "
                   f"({report['performance']['station']['anomaly_rate']:.2%})")
        logger.info(f"  - Mean anomaly score: {report['performance']['station']['mean_anomaly_score']:.3f}")
        
        logger.info(f"\nTotal anomalies across all datasets: {report['summary']['total_anomalies_detected']:,}")


def main():
    """
    Main entry point for ML pipeline.
    """
    try:
        pipeline = MLPipeline()
        pipeline.run()
        
        print("\n" + "=" * 80)
        print("SUCCESS! ML Anomaly Detection Complete")
        print("=" * 80)
        print(f"\n📊 Check results in: data/ml_output/")
        print(f"🤖 Check models in: models/")
        print(f"📈 Check report: data/ml_output/ml_performance_report.json")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
