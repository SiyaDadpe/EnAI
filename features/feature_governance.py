"""
Feature Governance and Lineage Tracking

Tracks feature engineering lineage, versions, and metadata.

WHY: Governance ensures reproducibility, auditability, and compliance.
Critical for production ML systems and regulatory requirements.

GOVERNANCE PRINCIPLES:
- Every feature has provenance (source + transformations)
- Versions are immutable and tracked
- Changes are logged and auditable
- Failures are recorded for debugging
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class FeatureGovernance:
    """
    Governance and lineage tracking for feature engineering.
    """
    
    def __init__(self, metadata_path: Path = None):
        """
        Initialize feature governance tracker.
        
        Args:
            metadata_path: Path to save metadata
        """
        self.metadata_path = metadata_path or Path("data/features_output/feature_metadata.json")
        self.lineage = defaultdict(dict)
        self.versions = {}
        self.audit_log = []
        
    def start_pipeline(self, version: str, input_sources: List[str]):
        """
        Record pipeline start.
        
        Args:
            version: Feature version (e.g., 'v1', 'v2')
            input_sources: List of input data sources
        """
        entry = {
            'event': 'pipeline_start',
            'version': version,
            'timestamp': datetime.now().isoformat(),
            'input_sources': input_sources
        }
        self.audit_log.append(entry)
        logger.info(f"[GOVERNANCE] Pipeline started: {version}")
        
    def record_transformation(
        self,
        version: str,
        transformation_name: str,
        input_files: List[str],
        output_file: str,
        features_created: List[str],
        metadata: Dict[str, Any] = None
    ):
        """
        Record a feature engineering transformation.
        
        Args:
            version: Feature version
            transformation_name: Name of transformation
            input_files: Input file paths
            output_file: Output file path
            features_created: List of feature names created
            metadata: Additional metadata
        """
        transformation = {
            'transformation': transformation_name,
            'timestamp': datetime.now().isoformat(),
            'inputs': input_files,
            'output': output_file,
            'features_created': features_created,
            'feature_count': len(features_created),
            'metadata': metadata or {}
        }
        
        if version not in self.lineage:
            self.lineage[version] = []
        
        self.lineage[version].append(transformation)
        
        entry = {
            'event': 'transformation',
            'version': version,
            'transformation': transformation_name,
            'timestamp': datetime.now().isoformat(),
            'features_created_count': len(features_created)
        }
        self.audit_log.append(entry)
        
        logger.info(f"[GOVERNANCE] Recorded: {transformation_name} ({len(features_created)} features)")
        
    def record_scenario(
        self,
        scenario_name: str,
        baseline_version: str,
        output_file: str,
        impact_analysis: Dict[str, Any]
    ):
        """
        Record a scenario simulation.
        
        Args:
            scenario_name: Scenario identifier
            baseline_version: Base feature version used
            output_file: Output file path
            impact_analysis: Impact analysis results
        """
        scenario = {
            'scenario': scenario_name,
            'timestamp': datetime.now().isoformat(),
            'baseline_version': baseline_version,
            'output': output_file,
            'impact_analysis': impact_analysis
        }
        
        if 'scenarios' not in self.lineage:
            self.lineage['scenarios'] = []
        
        self.lineage['scenarios'].append(scenario)
        
        entry = {
            'event': 'scenario_simulation',
            'scenario': scenario_name,
            'timestamp': datetime.now().isoformat()
        }
        self.audit_log.append(entry)
        
        logger.info(f"[GOVERNANCE] Recorded scenario: {scenario_name}")
        
    def record_failure(
        self,
        version: str,
        stage: str,
        error_message: str,
        error_type: str = None
    ):
        """
        Record a pipeline failure for debugging.
        
        Args:
            version: Feature version
            stage: Stage where failure occurred
            error_message: Error description
            error_type: Type of error
        """
        failure = {
            'event': 'failure',
            'version': version,
            'stage': stage,
            'error_type': error_type or 'Unknown',
            'error_message': error_message,
            'timestamp': datetime.now().isoformat()
        }
        
        self.audit_log.append(failure)
        
        logger.error(f"[GOVERNANCE] Failure recorded: {stage} - {error_message}")
        
    def complete_pipeline(
        self,
        version: str,
        output_files: List[str],
        total_features: int,
        duration_seconds: float
    ):
        """
        Record pipeline completion.
        
        Args:
            version: Feature version
            output_files: List of output file paths
            total_features: Total number of features created
            duration_seconds: Pipeline execution time
        """
        self.versions[version] = {
            'completed_at': datetime.now().isoformat(),
            'output_files': output_files,
            'total_features': total_features,
            'duration_seconds': duration_seconds,
            'status': 'SUCCESS'
        }
        
        entry = {
            'event': 'pipeline_complete',
            'version': version,
            'timestamp': datetime.now().isoformat(),
            'total_features': total_features,
            'duration_seconds': duration_seconds
        }
        self.audit_log.append(entry)
        
        logger.info(f"[GOVERNANCE] Pipeline completed: {version} ({total_features} features, {duration_seconds:.1f}s)")
        
    def save_metadata(self):
        """Save governance metadata to JSON file."""
        try:
            self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
            
            metadata = {
                'generated_at': datetime.now().isoformat(),
                'versions': self.versions,
                'lineage': dict(self.lineage),
                'audit_log': self.audit_log,
                'summary': {
                    'total_versions': len(self.versions),
                    'total_transformations': sum(len(v) for v in self.lineage.values() if isinstance(v, list)),
                    'total_audit_events': len(self.audit_log)
                }
            }
            
            with open(self.metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"[GOVERNANCE] Metadata saved: {self.metadata_path}")
            
        except Exception as e:
            logger.error(f"[GOVERNANCE] Failed to save metadata: {e}")
            raise
    
    def get_feature_provenance(self, feature_name: str) -> Dict[str, Any]:
        """
        Get provenance (lineage) for a specific feature.
        
        Args:
            feature_name: Name of feature
            
        Returns:
            Provenance information
        """
        provenance = {
            'feature_name': feature_name,
            'found_in_versions': [],
            'transformations': []
        }
        
        for version, transformations in self.lineage.items():
            if isinstance(transformations, list):
                for transform in transformations:
                    if feature_name in transform.get('features_created', []):
                        provenance['found_in_versions'].append(version)
                        provenance['transformations'].append({
                            'version': version,
                            'transformation': transform['transformation'],
                            'timestamp': transform['timestamp'],
                            'inputs': transform['inputs']
                        })
        
        return provenance
    
    def generate_data_lineage_diagram(self) -> str:
        """
        Generate text-based data lineage diagram.
        
        Returns:
            String representation of lineage
        """
        diagram = []
        diagram.append("\n" + "=" * 80)
        diagram.append("FEATURE ENGINEERING DATA LINEAGE")
        diagram.append("=" * 80 + "\n")
        
        for version in ['v1', 'v2']:
            if version in self.lineage:
                diagram.append(f"\n{version.upper()} FEATURES:")
                diagram.append("-" * 40)
                
                transformations = self.lineage[version]
                for i, transform in enumerate(transformations, 1):
                    diagram.append(f"\n{i}. {transform['transformation']}")
                    diagram.append(f"   Inputs: {', '.join([Path(f).name for f in transform['inputs']])}")
                    diagram.append(f"   Output: {Path(transform['output']).name}")
                    diagram.append(f"   Features: {len(transform['features_created'])} created")
        
        if 'scenarios' in self.lineage:
            diagram.append(f"\n\nSCENARIO SIMULATIONS:")
            diagram.append("-" * 40)
            
            for scenario in self.lineage['scenarios']:
                diagram.append(f"\n• {scenario['scenario']}")
                diagram.append(f"  Baseline: {scenario['baseline_version']}")
                diagram.append(f"  Output: {Path(scenario['output']).name}")
        
        return "\n".join(diagram)


_global_governance = None


def get_feature_governance(metadata_path: Path = None) -> FeatureGovernance:
    """
    Get global feature governance instance.
    
    Args:
        metadata_path: Path to save metadata
        
    Returns:
        FeatureGovernance instance
    """
    global _global_governance
    if _global_governance is None:
        _global_governance = FeatureGovernance(metadata_path)
    return _global_governance
