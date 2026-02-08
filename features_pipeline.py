"""
Feature Engineering Pipeline Runner

WHY THIS MATTERS:
Features are the language that machine learning speaks. Good features mean:
- Better predictions
- Faster model training
- More interpretable results
- Lower computational costs

This pipeline creates versioned features with full governance and error recovery.

BUSINESS VALUE:
1. V1 Features: Foundational temporal and statistical patterns
2. V2 Features: Advanced cross-dataset insights and anomaly interactions
3. Scenarios: What-if analysis for business planning

VERSIONING STRATEGY:
- v1: Baseline features (stable, production-ready)
- v2: Advanced features (builds on v1, experimental improvements)
- Scenarios: Business simulations (non-feature engineering, analysis only)

ERROR HANDLING:
- Continue on non-fatal errors (log and proceed)
- Graceful degradation (v2 can fail, v1 still usable)
- Full audit trail of failures
"""

import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd

from features.feature_engineering_v1 import FeatureEngineerV1
from features.feature_engineering_v2 import FeatureEngineerV2
from features.scenario_simulation import ScenarioSimulator
from features.feature_governance import get_feature_governance
from utils.logger import setup_logging


class FeaturePipeline:
    """
    Main feature engineering pipeline with versioning and governance.
    """
    
    def __init__(
        self,
        validated_dir: Path = None,
        ml_output_dir: Path = None,
        output_dir: Path = None,
        reference_units_path: Path = None
    ):
        """
        Initialize feature pipeline.
        
        Args:
            validated_dir: Directory with validated data
            ml_output_dir: Directory with ML anomaly outputs
            output_dir: Output directory for features
            reference_units_path: Path to reference units file
        """
        self.logger = logging.getLogger(__name__)
        
        # Set up paths
        base_dir = Path(__file__).parent
        self.validated_dir = validated_dir or base_dir / "data" / "output"
        self.ml_output_dir = ml_output_dir or base_dir / "data" / "ml_output"
        self.output_dir = output_dir or base_dir / "data" / "features_output"
        self.reference_units_path = reference_units_path or self.validated_dir / "validated_Reference Units.csv"
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize governance
        self.governance = get_feature_governance(self.output_dir / "feature_metadata.json")
        
        # Track results
        self.results = {
            'v1': {'status': 'NOT_STARTED', 'features': 0, 'errors': []},
            'v2': {'status': 'NOT_STARTED', 'features': 0, 'errors': []},
            'scenarios': {'status': 'NOT_STARTED', 'count': 0, 'errors': []}
        }
        
    def run_v1_features(self) -> Tuple[bool, pd.DataFrame, List[str]]:
        """
        Run v1 (baseline) feature engineering.
        
        Returns:
            Tuple of (success, dataframe, feature_list)
        """
        self.logger.info("\n" + "=" * 80)
        self.logger.info("STARTING V1 BASELINE FEATURES")
        self.logger.info("=" * 80)
        
        try:
            self.governance.start_pipeline(
                version='v1',
                input_sources=[
                    str(self.validated_dir / "validated_Weather.csv"),
                    str(self.validated_dir / "validated_Station Region.csv"),
                    str(self.reference_units_path)
                ]
            )
            
            # Initialize v1 engineer
            engineer = FeatureEngineerV1()
            
            # Load datasets
            self.logger.info("\n[V1] Loading datasets...")
            weather_df = pd.read_csv(self.validated_dir / "validated_Weather.csv")
            station_df = pd.read_csv(self.validated_dir / "validated_Station Region.csv")
            
            # Merge datasets
            self.logger.info("[V1] Merging datasets...")
            initial_cols = set(weather_df.columns)
            df = engineer.merge_datasets(weather_df, station_df)
            self.logger.info(f"[V1] Merged into {len(df):,} records")
            
            # Run transformations
            transformations = [
                ('temporal_features', engineer.create_temporal_features, {}),
                ('rolling_statistics', engineer.create_rolling_statistics, {'window_days': 7}),
            ]
            
            for transform_name, transform_func, kwargs in transformations:
                self.logger.info(f"\n[V1] Creating {transform_name}...")
                initial_cols = set(df.columns)
                
                try:
                    df = transform_func(df, **kwargs)
                    new_features = list(set(df.columns) - initial_cols)
                    
                    self.governance.record_transformation(
                        version='v1',
                        transformation_name=transform_name,
                        input_files=[str(self.validated_dir / "validated_Weather.csv")],
                        output_file=str(self.output_dir / "features_v1.csv"),
                        features_created=new_features,
                        metadata={'row_count': len(df)}
                    )
                    
                    self.logger.info(f"[V1] Created {len(new_features)} new features")
                    
                except Exception as e:
                    error_msg = f"Failed in {transform_name}: {e}"
                    self.logger.error(f"[V1] {error_msg}")
                    self.results['v1']['errors'].append(error_msg)
                    self.governance.record_failure('v1', transform_name, str(e), type(e).__name__)
                    # Continue with other transformations
            
            # Save v1 features
            output_path = self.output_dir / "features_v1.csv"
            df.to_csv(output_path, index=False)
            self.logger.info(f"\n[V1] Saved to: {output_path}")
            
            # Get feature list
            original_cols = {'observationdate', 'stationid', 'temperature', 'rainfall', 'region', 'region_type', 'stationcode'}
            v1_features = [col for col in df.columns if col not in original_cols]
            
            self.results['v1']['status'] = 'SUCCESS'
            self.results['v1']['features'] = len(v1_features)
            
            self.logger.info(f"[V1] SUCCESS: {len(v1_features)} features created")
            return True, df, v1_features
            
        except Exception as e:
            self.logger.error(f"\n[V1] CRITICAL FAILURE: {e}", exc_info=True)
            self.results['v1']['status'] = 'FAILED'
            self.results['v1']['errors'].append(f"Critical: {e}")
            self.governance.record_failure('v1', 'pipeline', str(e), type(e).__name__)
            return False, None, []
    
    def run_v2_features(self, v1_df: pd.DataFrame) -> Tuple[bool, pd.DataFrame, List[str]]:
        """
        Run v2 (advanced) feature engineering.
        
        Args:
            v1_df: DataFrame with v1 features
            
        Returns:
            Tuple of (success, dataframe, feature_list)
        """
        self.logger.info("\n" + "=" * 80)
        self.logger.info("STARTING V2 ADVANCED FEATURES")
        self.logger.info("=" * 80)
        
        if v1_df is None:
            self.logger.error("[V2] Cannot proceed without v1 features")
            self.results['v2']['status'] = 'SKIPPED'
            return False, None, []
        
        try:
            self.governance.start_pipeline(
                version='v2',
                input_sources=[
                    str(self.output_dir / "features_v1.csv"),
                    str(self.validated_dir / "validated_Activity Logs.csv"),
                    str(self.ml_output_dir / "anomaly_flagged_weather.csv")
                ]
            )
            
            # Initialize v2 engineer
            engineer = FeatureEngineerV2()
            
            # Load activity logs
            self.logger.info("\n[V2] Loading additional datasets...")
            activity_df = pd.read_csv(self.validated_dir / "validated_Activity Logs.csv")
            self.logger.info(f"[V2] Loaded activity logs: {len(activity_df):,} records")
            
            # Create cross-dataset features
            self.logger.info("\n[V2] Creating cross-dataset features...")
            initial_cols = set(v1_df.columns)
            
            try:
                df = engineer.create_cross_dataset_features(v1_df, activity_df)
                new_features = list(set(df.columns) - initial_cols)
                
                self.governance.record_transformation(
                    version='v2',
                    transformation_name='cross_dataset_features',
                    input_files=[str(self.output_dir / "features_v1.csv")],
                    output_file=str(self.output_dir / "features_v2.csv"),
                    features_created=new_features,
                    metadata={'row_count': len(df)}
                )
                
                self.logger.info(f"[V2] Created {len(new_features)} new features")
                
            except Exception as e:
                error_msg = f"Failed in cross_dataset_features: {e}"
                self.logger.error(f"[V2] {error_msg}")
                self.results['v2']['errors'].append(error_msg)
                self.governance.record_failure('v2', 'cross_dataset_features', str(e), type(e).__name__)
                # Use v1 df if cross-dataset fails
                df = v1_df
            
            # Create lag features
            self.logger.info("\n[V2] Creating lag features...")
            initial_cols = set(df.columns)
            
            try:
                dflagged = engineer.create_lag_features(df, lag_days=[1, 3, 7])
                new_features = list(set(df.columns) - initial_cols)
                
                self.governance.record_transformation(
                    version='v2',
                    transformation_name='lag_features',
                    input_files=[str(self.output_dir / "features_v1.csv")],
                    output_file=str(self.output_dir / "features_v2.csv"),
                    features_created=new_features,
                    metadata={'row_count': len(df)}
                )
                
                self.logger.info(f"[V2] Created {len(new_features)} new features")
                
            except Exception as e:
                error_msg = f"Failed in lag_features: {e}"
                self.logger.error(f"[V2] {error_msg}")
                self.results['v2']['errors'].append(error_msg)
                self.governance.record_failure('v2', 'lag_features', str(e), type(e).__name__)
            
            # Save v2 features
            output_path = self.output_dir / "features_v2.csv"
            df.to_csv(output_path, index=False)
            self.logger.info(f"\n[V2] Saved to: {output_path}")
            
            # Get feature list
            v1_features_path = self.output_dir / "features_v1.csv"
            v1_cols = set(pd.read_csv(v1_features_path, nrows=0).columns)
            v2_features = [col for col in df.columns if col not in v1_cols]
            
            self.results['v2']['status'] = 'SUCCESS' if len(v2_features) > 0 else 'PARTIAL'
            self.results['v2']['features'] = len(v2_features)
            
            self.logger.info(f"[V2] {self.results['v2']['status']}: {len(v2_features)} features created")
            return True, df, v2_features
            
        except Exception as e:
            self.logger.error(f"\n[V2] CRITICAL FAILURE: {e}", exc_info=True)
            self.results['v2']['status'] = 'FAILED'
            self.results['v2']['errors'].append(f"Critical: {e}")
            self.governance.record_failure('v2', 'pipeline', str(e), type(e).__name__)
            return False, v1_df, []
    
    def run_scenarios(self, v2_df: pd.DataFrame) -> bool:
        """
        Run scenario simulations.
        
        Args:
            v2_df: DataFrame with v2 features
            
        Returns:
            Success flag
        """
        self.logger.info("\n" + "=" * 80)
        self.logger.info("STARTING SCENARIO SIMULATIONS")
        self.logger.info("=" * 80)
        
        # Skip scenarios for now - they require complex setup
        self.logger.info("[SCENARIOS] Skipping scenario simulations (can be run separately)")
        self.results['scenarios']['status'] = 'SKIPPED'
        return True
    
    def run(self) -> Dict[str, Any]:
        """
        Run complete feature pipeline.
        
        Returns:
            Pipeline execution summary
        """
        self.logger.info("\n" + "=" * 80)
        self.logger.info("FEATURE ENGINEERING PIPELINE")
        self.logger.info("=" * 80)
        
        start_time = time.time()
        
        # Run v1 features
        v1_success, v1_df, v1_features = self.run_v1_features()
        
        if v1_success:
            self.governance.complete_pipeline(
                version='v1',
                output_files=[str(self.output_dir / "features_v1.csv")],
                total_features=len(v1_features),
                duration_seconds=time.time() - start_time
            )
        
        # Run v2 features (can fail independently)
        v2_start = time.time()
        v2_success, v2_df, v2_features = self.run_v2_features(v1_df)
        
        if v2_success:
            self.governance.complete_pipeline(
                version='v2',
                output_files=[str(self.output_dir / "features_v2.csv")],
                total_features=len(v2_features),
                duration_seconds=time.time() - v2_start
            )
        
        # Run scenarios (can fail independently)
        self.run_scenarios(v2_df)
        
        # Save governance metadata
        try:
            self.governance.save_metadata()
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")
        
        # Generate summary
        duration = time.time() - start_time
        summary = {
            'pipeline_duration_seconds': duration,
            'v1_features': self.results['v1'],
            'v2_features': self.results['v2'],
            'scenarios': self.results['scenarios'],
            'overall_status': 'SUCCESS' if v1_success else 'FAILED',
            'output_directory': str(self.output_dir),
            'metadata_file': str(self.governance.metadata_path)
        }
        
        # Print summary
        self.logger.info("\n" + "=" * 80)
        self.logger.info("PIPELINE EXECUTION SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"\nV1 Features: {self.results['v1']['status']} ({self.results['v1']['features']} features)")
        self.logger.info(f"V2 Features: {self.results['v2']['status']} ({self.results['v2']['features']} features)")
        self.logger.info(f"Scenarios: {self.results['scenarios']['status']} ({self.results['scenarios']['count']} completed)")
        self.logger.info(f"\nTotal Duration: {duration:.2f} seconds")
        self.logger.info(f"Output Directory: {self.output_dir}")
        
        # Print lineage diagram
        self.logger.info(self.governance.generate_data_lineage_diagram())
        
        return summary


def main():
    """Main entry point for feature pipeline."""
    setup_logging(log_file='features_pipeline.log')
    logger = logging.getLogger(__name__)
    
    try:
        pipeline = FeaturePipeline()
        summary = pipeline.run()
        
        if summary['overall_status'] == 'SUCCESS':
            logger.info("\n[OK] Feature pipeline completed successfully!")
            sys.exit(0)
        else:
            logger.error("\n[FAILED] Feature pipeline encountered errors")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"\n[CRITICAL] Pipeline crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
