"""
Data lineage tracking.

Maintains relationships between:
- Raw input files
- Intermediate processing steps
- Validated datasets
- Final outputs

WHY: Lineage enables:
- Root cause analysis when issues appear
- Impact analysis when source data changes
- Compliance and auditability
- Debugging and troubleshooting
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict

from config.pipeline_config import METADATA_OUTPUT_PATH

logger = logging.getLogger(__name__)


class LineageTracker:
    """
    Tracks data lineage throughout the pipeline.
    
    Records transformations, dependencies, and metadata.
    """
    
    def __init__(self):
        """Initialize lineage tracker."""
        self.lineage_graph = defaultdict(dict)
        self.metadata = {
            "pipeline_start": datetime.now().isoformat(),
            "pipeline_end": None,
        }
    
    def record_ingestion(
        self,
        source_file: str,
        output_file: str,
        stats: Dict[str, Any]
    ):
        """
        Record ingestion of a raw file.
        
        Args:
            source_file: Path to raw CSV
            output_file: Path to ingested data
            stats: Ingestion statistics
        """
        self.lineage_graph[output_file] = {
            "stage": "ingestion",
            "source": source_file,
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
        }
        logger.debug(f"Recorded ingestion: {source_file} -> {output_file}")
    
    def record_validation(
        self,
        input_file: str,
        valid_output: str,
        validation_report: Dict[str, Any]
    ):
        """
        Record validation stage.
        
        Args:
            input_file: Input data file
            valid_output: Output file for valid data
            validation_report: Validation results
        """
        self.lineage_graph[valid_output] = {
            "stage": "validation",
            "source": input_file,
            "timestamp": datetime.now().isoformat(),
            "validation_report": validation_report,
        }
        
        logger.debug(f"Recorded validation: {input_file} -> {valid_output}")
    
    def record_transformation(
        self,
        stage: str,
        inputs: List[str],
        output: str,
        metadata: Dict[str, Any]
    ):
        """
        Record a transformation stage.
        
        Args:
            stage: Name of the stage (e.g., "merge", "feature_engineering")
            inputs: List of input files
            output: Output file
            metadata: Additional metadata
        """
        self.lineage_graph[output] = {
            "stage": stage,
            "sources": inputs,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata,
        }
        logger.debug(f"Recorded {stage}: {inputs} -> {output}")
    
    def get_lineage(self, file_path: str) -> Dict[str, Any]:
        """
        Get lineage for a specific file.
        
        Args:
            file_path: File to trace
        
        Returns:
            Lineage dictionary
        """
        return self.lineage_graph.get(file_path, {})
    
    def trace_back(self, file_path: str) -> List[str]:
        """
        Trace back to original source files.
        
        Args:
            file_path: File to trace
        
        Returns:
            List of ancestor files
        """
        ancestors = []
        current = self.lineage_graph.get(file_path, {})
        
        if "source" in current:
            source = current["source"]
            ancestors.append(source)
            ancestors.extend(self.trace_back(source))
        
        elif "sources" in current:
            for source in current["sources"]:
                ancestors.append(source)
                ancestors.extend(self.trace_back(source))
        
        return ancestors
    
    def save(self, output_path: Path = None):
        """
        Save lineage to JSON file.
        
        Args:
            output_path: Path to save lineage (default: from config)
        """
        if output_path is None:
            output_path = METADATA_OUTPUT_PATH
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.metadata["pipeline_end"] = datetime.now().isoformat()
        
        lineage_data = {
            "metadata": self.metadata,
            "lineage_graph": dict(self.lineage_graph),
        }
        
        with open(output_path, 'w') as f:
            json.dump(lineage_data, f, indent=2)
        
        logger.info(f"Saved lineage to {output_path}")
    
    @classmethod
    def load(cls, path: Path) -> 'LineageTracker':
        """
        Load lineage from JSON file.
        
        Args:
            path: Path to lineage file
        
        Returns:
            Loaded LineageTracker instance
        """
        tracker = cls()
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        tracker.metadata = data.get("metadata", {})
        tracker.lineage_graph = defaultdict(dict, data.get("lineage_graph", {}))
        
        logger.info(f"Loaded lineage from {path}")
        
        return tracker


# Global tracker instance
_global_tracker = None


def get_tracker() -> LineageTracker:
    """Get or create global lineage tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = LineageTracker()
    return _global_tracker


def reset_tracker():
    """Reset global tracker (useful for testing)."""
    global _global_tracker
    _global_tracker = LineageTracker()
