"""
Main pipeline runner for the enterprise data engineering project.

Orchestrates the complete data pipeline:
1. Setup and initialization
2. Ingestion of raw CSVs
3. Validation and quality checks
4. Quarantine management
5. Governance and reporting

This pipeline is:
- Idempotent: Safe to re-run with updated data
- Modular: Each stage is independent
- Auditable: Full lineage and logging

Usage:
    python main.py
    
WHY: Single entry point makes the pipeline easy to run, test, and schedule.
"""

import sys
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import configuration
from config.pipeline_config import (
    RAW_DATA_DIR,
    VALIDATED_DATA_DIR,
    OUTPUT_DIR,
    EXPECTED_FILES,
    ensure_directories,
)

# Import utilities
from utils.logger import setup_logging, get_logger, log_dataframe_info

# Import ingestion modules
from ingestion.schema_inference import ingest_csv_with_schema

# Import validation modules
from validation.schema_validator import validate_schema
from validation.quality_checker import run_quality_checks

# Import governance modules
from governance.lineage_tracker import get_tracker, reset_tracker
from governance.audit_logger import get_audit_logger

# Setup logging
logger = get_logger(__name__)


class DataPipeline:
    """
    Main data pipeline orchestrator.
    
    Manages the end-to-end data processing workflow.
    """
    
    def __init__(self):
        """Initialize pipeline."""
        self.lineage = get_tracker()
        self.audit = get_audit_logger()
        self.results = {
            "ingestion": {},
            "validation": {},
            "filtered": {},
        }
    
    def setup(self):
        """
        Initialize pipeline environment.
        
        - Create necessary directories
        - Initialize logging
        - Reset trackers
        """
        logger.info("=" * 80)
        logger.info("ENTERPRISE DATA PIPELINE - STARTING")
        logger.info("=" * 80)
        
        # Ensure all directories exist
        ensure_directories()
        
        # Log pipeline configuration
        self.audit.log_pipeline_start({
            "raw_data_dir": str(RAW_DATA_DIR),
            "validated_data_dir": str(VALIDATED_DATA_DIR),
            "output_dir": str(OUTPUT_DIR),
            "expected_files": EXPECTED_FILES,
        })
        
        logger.info("Pipeline setup complete")
    
    def ingest_file(self, filename: str) -> tuple[Any, Dict[str, Any]]:
        """
        Ingest a single CSV file.
        
        Args:
            filename: Name of CSV file in raw data directory
        
        Returns:
            Tuple of (DataFrame, metadata)
        """
        logger.info("-" * 80)
        logger.info(f"INGESTING: {filename}")
        logger.info("-" * 80)
        
        file_path = RAW_DATA_DIR / filename
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None, {"error": "File not found"}
        
        try:
            # Ingest CSV with schema
            df, metadata = ingest_csv_with_schema(file_path, schema_name=filename)
            
            log_dataframe_info(df, name=filename, logger=logger)
            
            # Record in lineage
            self.lineage.record_ingestion(
                source_file=str(file_path),
                output_file=f"ingested_{filename}",
                stats=metadata["final_stats"]
            )
            
            # Audit log
            self.audit.log_file_processed(
                filename=filename,
                stage="ingestion",
                rows_in=metadata["initial_stats"]["row_count"],
                rows_out=metadata["final_stats"]["row_count"],
                metadata=metadata
            )
            
            self.results["ingestion"][filename] = metadata
            
            return df, metadata
        
        except Exception as e:
            logger.error(f"Failed to ingest {filename}: {e}", exc_info=True)
            self.audit.log_error(e, {"stage": "ingestion", "filename": filename})
            return None, {"error": str(e)}
    
    def validate_file(self, df, filename: str, schema) -> tuple[Any, Dict[str, Any], Dict[str, Any]]:
        """
        Validate a DataFrame.
        
        Args:
            df: DataFrame to validate
            filename: Original filename for tracking
            schema: Schema definition
        
        Returns:
            Tuple of (DataFrame, validation_report, quality_report)
        """
        logger.info("-" * 80)
        logger.info(f"VALIDATING: {filename}")
        logger.info("-" * 80)
        
        try:
            # Run schema validation
            validation_report = validate_schema(df, schema)
            
            # Run quality checks
            quality_report = run_quality_checks(df, schema)
            
            # Log results
            logger.info(f"Validation: {validation_report['valid_count']}/{validation_report['total_rows']} rows passed")
            logger.info(f"Quality: {quality_report['passed_all_checks']}/{quality_report['total_rows']} rows passed")
            
            # Audit log - convert Pandas Series to JSON-serializable format
            validation_metrics_for_audit = {
                k: v for k, v in validation_report.items() if k != 'valid_rows'
            }
            validation_metrics_for_audit['valid_count'] = int(validation_report['valid_count'])
            validation_metrics_for_audit['invalid_count'] = int(validation_report['invalid_count'])
            
            quality_metrics_for_audit = quality_report["quality_metrics"].copy()
            # Convert any Series in quality_metrics to lists
            for key, value in quality_metrics_for_audit.items():
                if hasattr(value, 'tolist'):
                    quality_metrics_for_audit[key] = value.tolist()
            
            self.audit.log_quality_metrics({
                "filename": filename,
                "validation_metrics": validation_metrics_for_audit,
                "quality_metrics": quality_metrics_for_audit,
            })
            
            self.results["validation"][filename] = {
                "validation_report": validation_report,
                "quality_report": quality_report,
            }
            
            return df, validation_report, quality_report
        
        except Exception as e:
            logger.error(f"Failed to validate {filename}: {e}", exc_info=True)
            self.audit.log_error(e, {"stage": "validation", "filename": filename})
            return df, {}, {}
    
    def filter_valid_rows(
        self,
        df,
        filename: str,
        validation_report: Dict[str, Any],
        quality_report: Dict[str, Any]
    ) -> Any:
        """
        Filter to keep only valid rows.
        
        Args:
            df: DataFrame to process
            filename: Original filename
            validation_report: Validation results
            quality_report: Quality check results
        
        Returns:
            Valid DataFrame
        """
        logger.info("-" * 80)
        logger.info(f"FILTERING VALID DATA: {filename}")
        logger.info("-" * 80)
        
        try:
            # Combine validation and quality masks
            valid_mask = validation_report["valid_rows"] & quality_report["valid_rows"]
            valid_df = df[valid_mask].copy()
            invalid_count = len(df) - len(valid_df)
            
            logger.info(f"Kept {len(valid_df)}/{len(df)} valid rows (removed {invalid_count} invalid)")
            log_dataframe_info(valid_df, name=f"{filename} (valid)", logger=logger)
            
            # Record in lineage
            valid_output = str(VALIDATED_DATA_DIR / filename)
            self.lineage.record_validation(
                input_file=f"ingested_{filename}",
                valid_output=valid_output,
                validation_report={
                    "valid_rows": len(valid_df),
                    "invalid_rows": invalid_count,
                }
            )
            
            self.results["filtered"][filename] = {
                "total_rows": len(df),
                "valid_rows": len(valid_df),
                "invalid_rows": invalid_count
            }
            
            return valid_df
        
        except Exception as e:
            logger.error(f"Failed to filter {filename}: {e}", exc_info=True)
            self.audit.log_error(e, {"stage": "filtering", "filename": filename})
            return df
    
    def save_validated_data(self, df, filename: str):
        """
        Save validated data to output directory.
        
        Args:
            df: Validated DataFrame
            filename: Original filename
        """
        output_path = VALIDATED_DATA_DIR / filename
        df.to_csv(output_path, index=False)
        logger.info(f"Saved validated data: {output_path}")
        
        # Also save to final output directory
        final_output_path = OUTPUT_DIR / f"validated_{filename}"
        df.to_csv(final_output_path, index=False)
        logger.info(f"Saved to output: {final_output_path}")
    
    def process_file(self, filename: str):
        """
        Process a single file through the complete pipeline.
        
        Args:
            filename: Name of CSV file to process
        """
        from config.schema_config import get_schema
        
        # Step 1: Ingest
        df, ingest_metadata = self.ingest_file(filename)
        if df is None:
            logger.error(f"Skipping {filename} due to ingestion failure")
            return
        
        # Step 2: Validate
        schema = get_schema(filename)
        df, validation_report, quality_report = self.validate_file(df, filename, schema)
        
        # Step 3: Filter to valid rows only
        valid_df = self.filter_valid_rows(df, filename, validation_report, quality_report)
        
        # Step 4: Save validated data
        self.save_validated_data(valid_df, filename)
        
        logger.info(f"Completed processing: {filename}")
    
    def run(self):
        """
        Run the complete pipeline for all expected files.
        """
        start_time = datetime.now()
        
        try:
            # Setup
            self.setup()
            
            # Process each expected file
            for filename in EXPECTED_FILES:
                try:
                    self.process_file(filename)
                except Exception as e:
                    logger.error(f"Error processing {filename}: {e}", exc_info=True)
                    self.audit.log_error(e, {"filename": filename})
            
            # Save lineage
            self.lineage.save()
            
            # Generate summary
            self.generate_summary()
            
            # Mark pipeline as successful
            elapsed = (datetime.now() - start_time).total_seconds()
            self.audit.log_pipeline_end("success", {
                "elapsed_seconds": elapsed,
                "files_processed": len(self.results["ingestion"]),
                "total_removed": sum(
                    r.get("invalid_rows", 0) 
                    for r in self.results["filtered"].values()
                ),
            })
            
            logger.info("=" * 80)
            logger.info("PIPELINE COMPLETED SUCCESSFULLY")
            logger.info(f"Total time: {elapsed:.2f} seconds")
            logger.info("=" * 80)
        
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.audit.log_pipeline_end("failure", {"error": str(e)})
            raise
    
    def generate_summary(self):
        """
        Generate and log pipeline execution summary.
        """
        logger.info("-" * 80)
        logger.info("PIPELINE SUMMARY")
        logger.info("-" * 80)
        
        # Ingestion summary
        logger.info("\nINGESTION:")
        for filename, metadata in self.results["ingestion"].items():
            if "error" in metadata:
                logger.info(f"  {filename}: ERROR - {metadata['error']}")
            else:
                stats = metadata.get("final_stats", {})
                logger.info(f"  {filename}: {stats.get('row_count', 0)} rows ingested")
        
        # Validation summary
        logger.info("\nVALIDATION:")
        for filename, reports in self.results["validation"].items():
            val_report = reports.get("validation_report", {})
            qual_report = reports.get("quality_report", {})
            logger.info(
                f"  {filename}: {val_report.get('valid_count', 0)}/{val_report.get('total_rows', 0)} "
                f"schema valid, {qual_report.get('passed_all_checks', 0)} quality passed"
            )
        
        # Filtering summary
        logger.info("\nFILTERING:")
        total_removed = 0
        for filename, report in self.results["filtered"].items():
            invalid = report.get("invalid_rows", 0)
            total_removed += invalid
            if invalid > 0:
                logger.info(f"  {filename}: {invalid} invalid rows removed")
        
        if total_removed == 0:
            logger.info("  No invalid rows - all data is valid!")
        
        logger.info(f"\nTOTAL REMOVED: {total_removed} rows")


def main():
    """
    Main entry point for the pipeline.
    """
    # Setup logging
    setup_logging()

    # Load .env once (optional) so AI toggles can be set there.
    try:
        from ai_insights.config import load_env

        load_env(PROJECT_ROOT)
    except Exception:
        pass
    
    # Create and run pipeline
    pipeline = DataPipeline()
    pipeline.run()

    # Optional: generate AI explanations PDF/JSON after pipeline run.
    # Controlled via env var so existing behavior stays the same unless enabled.
    if os.getenv("AI_REPORT_ON_RUN", "").strip().lower() in {"1", "true", "yes"}:
        try:
            from ai_insights.generate_pdf_report import generate

            json_path, pdf_path = generate()
            logger.info(f"AI report generated: {pdf_path}")
            logger.info(f"AI report JSON: {json_path}")
        except Exception as e:
            logger.error(f"AI report generation failed: {e}", exc_info=True)

    # Optional: auto-launch interactive dashboard
    if os.getenv("AI_DASHBOARD_ON_RUN", "").strip().lower() in {"1", "true", "yes"}:
        try:
            from ai_insights.launch_dashboard import launch_dashboard

            proc = launch_dashboard(PROJECT_ROOT)
            port = os.getenv("AI_DASHBOARD_PORT", "8501")
            logger.info(f"Streamlit dashboard started (PID={proc.pid}) at http://localhost:{port}")
        except Exception as e:
            logger.error(f"Dashboard launch failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
