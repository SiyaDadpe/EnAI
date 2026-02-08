"""
Features module for feature engineering and scenario simulations.

Implements versioned feature engineering pipeline with:
- v1: Baseline features
- v2: Advanced features
- Scenario simulations
- Feature governance and lineage tracking
"""

__version__ = "1.0.0"
__all__ = [
    "FeatureEngineerV1",
    "FeatureEngineerV2",
    "ScenarioSimulator",
    "FeatureGovernance",
    "FeatureCatalog"
]

from features.feature_engineering_v1 import FeatureEngineerV1
from features.feature_engineering_v2 import FeatureEngineerV2
from features.scenario_simulation import ScenarioSimulator
from features.feature_governance import FeatureGovernance
from features.feature_catalog import FeatureCatalog

