"""
Scenario Simulation Module

Enables "what-if" analysis for business planning:
- Rainfall change scenarios (drought/flood simulation)
- Regional drought impact analysis
- Fertilizer optimization scenarios

WHY: Scenario planning helps businesses prepare for different
weather conditions and optimize resource allocation.

BUSINESS JUSTIFICATION:
- Drought scenarios → Water contingency planning
- Rainfall increase → Irrigation reduction opportunities
- Fertilizer optimization → Cost savings + environmental benefits
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class ScenarioSimulator:
    """
    Scenario simulation engine for agricultural whatif analyses.
    """
    
    def __init__(self):
        """Initialize scenario simulator."""
        self.scenarios = {}
        self.baseline = None
        
    def simulate_rainfall_change(
        self,
        df: pd.DataFrame,
        change_percent: float,
        scenario_name: str = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Simulate impact of rainfall increase/decrease.
        
        WHY: Climate change brings uncertain rainfall patterns.
        Businesses need to plan for both drought and flood scenarios.
        
        BUSINESS VALUE:
        - Plan irrigation infrastructure investments
        - Optimize water storage capacity
        - Prepare for climate variability
        
        Example scenarios:
        - +20% rainfall: Reduced irrigation needs, potential flooding
        - -20% rainfall: Increased irrigation, drought risk
        
        Args:
            df: Baseline features DataFrame
            change_percent: Percent change in rainfall (-100 to 100)
            scenario_name: Name for this scenario
            
        Returns:
            Tuple of (modified DataFrame, impact analysis)
        """
        if scenario_name is None:
            scenario_name = f"rainfall_{'increase' if change_percent > 0 else 'decrease'}_{abs(change_percent)}pct"
        
        logger.info("=" * 80)
        logger.info(f"SCENARIO: {scenario_name}")
        logger.info(f"Rainfall change: {change_percent:+.1f}%")
        logger.info("=" * 80)
        
        df_scenario = df.copy()
        
        try:
            # Store baseline if first scenario
            if self.baseline is None:
                self.baseline = df.copy()
            
            # Modify rainfall
            if 'rainfall' in df_scenario.columns:
                original_rainfall = df_scenario['rainfall'].copy()
                df_scenario['rainfall'] = df_scenario['rainfall'] * (1 + change_percent / 100)
                
                # Recalculate rolling averages
                if 'rainfall_7d_avg' in df_scenario.columns:
                    df_scenario['rainfall_7d_avg'] = df_scenario['rainfall_7d_avg'] * (1 + change_percent / 100)
                
                # Update regional aggregations
                if 'regional_rainfall_total' in df_scenario.columns:
                    df_scenario['regional_rainfall_total'] = df_scenario['regional_rainfall_total'] * (1 + change_percent / 100)
                    df_scenario['regional_rainfall_mean'] = df_scenario['regional_rainfall_mean'] * (1 + change_percent / 100)
            
            # Calculate impact analysis
            impact = {
                'scenario_name': scenario_name,
                'rainfall_change_percent': change_percent,
                'baseline_avg_rainfall': self.baseline['rainfall'].mean() if 'rainfall' in self.baseline else None,
                'scenario_avg_rainfall': df_scenario['rainfall'].mean() if 'rainfall' in df_scenario else None,
                'regions_affected': df_scenario['region'].nunique() if 'region' in df_scenario else None,
                'estimated_irrigation_impact': self._estimate_irrigation_impact(change_percent),
                'risk_level': self._assess_risk_level(change_percent)
            }
            
            # Add scenario flag
            df_scenario['scenario'] = scenario_name
            
            self.scenarios[scenario_name] = impact
            
            logger.info(f"[OK] Scenario created:")
            logger.info(f"  - Baseline avg rainfall: {impact['baseline_avg_rainfall']:.2f} mm")
            logger.info(f"  - Scenario avg rainfall: {impact['scenario_avg_rainfall']:.2f} mm")
            logger.info(f"  - Estimated irrigation impact: {impact['estimated_irrigation_impact']}")
            logger.info(f"  - Risk level: {impact['risk_level']}")
            
            return df_scenario, impact
            
        except Exception as e:
            logger.error(f"Rainfall scenario simulation failed: {e}")
            raise
    
    def simulate_regional_drought(
        self,
        df: pd.DataFrame,
        drought_severity: str = 'moderate'
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Simulate regional drought conditions.
        
        WHY: Droughts can devastate agricultural regions. Simulations
        help identify vulnerable areas and plan interventions.
        
        BUSINESS VALUE:
        - Identify high-risk regions
        - Plan emergency water supplies
        - Estimate crop yield impacts
        
        Drought levels:
        - mild: -15% rainfall, +2°C temperature
        - moderate: -30% rainfall, +3°C temperature
        - severe: -50% rainfall, +5°C temperature
        
        Args:
            df: Baseline features DataFrame
            drought_severity: 'mild', 'moderate', or 'severe'
            
        Returns:
            Tuple of (modified DataFrame, impact analysis)
        """
        logger.info("=" * 80)
        logger.info(f"SCENARIO: Regional Drought ({drought_severity.upper()})")
        logger.info("=" * 80)
        
        df_scenario = df.copy()
        
        try:
            # Store baseline if first scenario
            if self.baseline is None:
                self.baseline = df.copy()
            
            # Define drought parameters
            drought_params = {
                'mild': {'rainfall_change': -15, 'temp_increase': 2},
                'moderate': {'rainfall_change': -30, 'temp_increase': 3},
                'severe': {'rainfall_change': -50, 'temp_increase': 5}
            }
            
            params = drought_params.get(drought_severity, drought_params['moderate'])
            
            # Apply drought conditions
            if 'rainfall' in df_scenario.columns:
                df_scenario['rainfall'] = df_scenario['rainfall'] * (1 + params['rainfall_change'] / 100)
                df_scenario['rainfall'] = df_scenario['rainfall'].clip(lower=0)
            
            if 'temperature' in df_scenario.columns:
                df_scenario['temperature'] = df_scenario['temperature'] + params['temp_increase']
            
            # Recalculate stress index
            if 'temperature' in df_scenario.columns and 'rainfall' in df_scenario.columns:
                df_scenario['drought_stress_index'] = (
                    (df_scenario['temperature'] - self.baseline['temperature'].mean()) /
                    (df_scenario['rainfall'] + 1)
                )
            
            # Calculate impact by region
            regional_impact = df_scenario.groupby('region').agg({
                'rainfall': 'mean',
                'temperature': 'mean'
            }).reset_index()
            
            regional_impact['baseline_rainfall'] = self.baseline.groupby('region')['rainfall'].mean().values
            regional_impact['rainfall_reduction_pct'] = (
                (regional_impact['baseline_rainfall'] - regional_impact['rainfall']) /
                regional_impact['baseline_rainfall'] * 100
            )
            
            impact = {
                'scenario_name': f'regional_drought_{drought_severity}',
                'drought_severity': drought_severity,
                'rainfall_change_percent': params['rainfall_change'],
                'temperature_increase_celsius': params['temp_increase'],
                'regions_affected': len(regional_impact),
                'worst_affected_region': regional_impact.loc[
                    regional_impact['rainfall_reduction_pct'].idxmax(), 'region'
                ] if len(regional_impact) > 0 else None,
                'avg_rainfall_reduction': regional_impact['rainfall_reduction_pct'].mean(),
                'regional_impacts': regional_impact.to_dict('records')
            }
            
            # Add scenario flag
            df_scenario['scenario'] = f'regional_drought_{drought_severity}'
            
            self.scenarios[f'regional_drought_{drought_severity}'] = impact
            
            logger.info(f"[OK] Drought scenario created:")
            logger.info(f"  - Rainfall reduction: {params['rainfall_change']}%")
            logger.info(f"  - Temperature increase: +{params['temp_increase']}°C")
            logger.info(f"  - Worst affected region: {impact['worst_affected_region']}")
            logger.info(f"  - Avg rainfall reduction: {impact['avg_rainfall_reduction']:.1f}%")
            
            return df_scenario, impact
            
        except Exception as e:
            logger.error(f"Drought scenario simulation failed: {e}")
            raise
    
    def simulate_fertilizer_optimization(
        self,
        activity_df: pd.DataFrame,
        weather_df: pd.DataFrame,
        reduction_target_pct: float = 15
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Simulate fertilizer optimization scenarios.
        
        WHY: Over-fertilization wastes money and harms environment.
        Optimization based on weather can reduce usage while maintaining yields.
        
        BUSINESS VALUE:
        - Cost savings (fertilizer is expensive)
        - Environmental sustainability
        - Regulatory compliance
        
        Strategy:
        - Reduce fertilizer when rainfall is high (nutrient retention)
        - Maintain fertilizer when rainfall is low (less leaching)
        
        Args:
            activity_df: Activity logs with fertilizer data
            weather_df: Weather data for context
            reduction_target_pct: Target fertilizer reduction percentage
            
        Returns:
            Tuple of (optimized DataFrame, savings analysis)
        """
        logger.info("=" * 80)
        logger.info(f"SCENARIO: Fertilizer Optimization ({reduction_target_pct}% reduction target)")
        logger.info("=" * 80)
       
        
        df_scenario = activity_df.copy()
        
        try:
            # Merge weather context
            df_scenario['activitydate'] = pd.to_datetime(df_scenario['activitydate'])
            weather_df['observationdate'] = pd.to_datetime(weather_df['observationdate'])
            
            # Get rainfall context for each activity
            weather_context = weather_df.groupby(['region', 'observationdate']).agg({
                'rainfall': 'mean',
                'rainfall_7d_avg': 'mean'
            }).reset_index()
            
            df_scenario = df_scenario.merge(
                weather_context,
                left_on=['region', 'activitydate'],
                right_on=['region', 'observationdate'],
                how='left'
            )
            
            # Calculate optimization factor based on rainfall
            # High rainfall (>50mm) → reduce by target %
            # Moderate rainfall (25-50mm) → reduce by half target
            # Low rainfall (<25mm) → no reduction
            
            df_scenario['rainfall_level'] = pd.cut(
                df_scenario['rainfall_7d_avg'].fillna(25),
                bins=[0, 25, 50, 1000],
                labels=['low', 'moderate', 'high']
            )
            
            df_scenario['optimization_factor'] = df_scenario['rainfall_level'].map({
                'low': 1.0,  # No reduction
                'moderate': 1 - (reduction_target_pct / 200),  # Half reduction
                'high': 1 - (reduction_target_pct / 100)  # Full reduction
            })
            
            # Apply optimization
            original_fertilizer = df_scenario['fertilizer_amount'].copy()
            df_scenario['optimized_fertilizer_amount'] = (
                df_scenario['fertilizer_amount'] * df_scenario['optimization_factor']
            )
            
            # Calculate savings
            total_original = original_fertilizer.sum()
            total_optimized = df_scenario['optimized_fertilizer_amount'].sum()
            total_saved = total_original - total_optimized
            percent_saved = (total_saved / total_original) * 100
            
            # Estimate cost savings (assume $2/kg fertilizer)
            cost_per_kg = 2.0
            cost_savings = total_saved * cost_per_kg
            
            impact = {
                'scenario_name': f'fertilizer_optimization_{reduction_target_pct}pct',
                'target_reduction_percent': reduction_target_pct,
                'actual_reduction_percent': percent_saved,
                'total_original_kg': total_original,
                'total_optimized_kg': total_optimized,
                'total_saved_kg': total_saved,
                'estimated_cost_savings_usd': cost_savings,
                'high_rainfall_applications': (df_scenario['rainfall_level'] == 'high').sum(),
                'moderate_rainfall_applications': (df_scenario['rainfall_level'] == 'moderate').sum(),
                'low_rainfall_applications': (df_scenario['rainfall_level'] == 'low').sum(),
            }
            
            # Add scenario flag
            df_scenario['scenario'] = f'fertilizer_optimization_{reduction_target_pct}pct'
            
            self.scenarios[f'fertilizer_optimization_{reduction_target_pct}pct'] = impact
            
            logger.info(f"[OK] Fertilizer optimization scenario created:")
            logger.info(f"  - Original fertilizer: {total_original:,.0f} kg")
            logger.info(f"  - Optimized fertilizer: {total_optimized:,.0f} kg")
            logger.info(f"  - Savings: {total_saved:,.0f} kg ({percent_saved:.1f}%)")
            logger.info(f"  - Estimated cost savings: ${cost_savings:,.2f}")
            
            return df_scenario, impact
            
        except Exception as e:
            logger.error(f"Fertilizer optimization failed: {e}")
            raise
    
    def _estimate_irrigation_impact(self, rainfall_change_pct: float) -> str:
        """Estimate irrigation impact from rainfall change."""
        if rainfall_change_pct > 15:
            return "Significantly reduced irrigation needs (-20-30%)"
        elif rainfall_change_pct > 5:
            return "Moderately reduced irrigation needs (-10-20%)"
        elif rainfall_change_pct > -5:
            return "Minimal impact on irrigation needs"
        elif rainfall_change_pct > -15:
            return "Moderately increased irrigation needs (+10-20%)"
        else:
            return "Significantly increased irrigation needs (+20-40%)"
    
    def _assess_risk_level(self, rainfall_change_pct: float) -> str:
        """Assess risk level from rainfall change."""
        if abs(rainfall_change_pct) < 10:
            return "LOW"
        elif abs(rainfall_change_pct) < 25:
            return "MODERATE"
        elif abs(rainfall_change_pct) < 40:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def get_all_scenarios_summary(self) -> Dict[str, Any]:
        """
        Get summary of all simulated scenarios.
        
        Returns:
            Dictionary with all scenario results
        """
        return {
            'total_scenarios': len(self.scenarios),
            'scenarios': self.scenarios
        }


def run_scenario_simulations(
    features_v2_df: pd.DataFrame,
    activity_anomaly_df: pd.DataFrame,
    output_dir: Path
) -> Dict[str, Any]:
    """
    Run all scenario simulations.
    
    Args:
        features_v2_df: DataFrame with v2 features
        activity_anomaly_df: Activity data with anomalies
        output_dir: Directory to save scenario outputs
        
    Returns:
        Dictionary with all scenario results
    """
    logger.info("=" * 80)
    logger.info("RUNNING SCENARIO SIMULATIONS")
    logger.info("=" * 80)
    
    simulator = ScenarioSimulator()
    
    try:
        # Scenario 1: Rainfall increase 20%
        df_rain_inc, impact_rain_inc = simulator.simulate_rainfall_change(
            features_v2_df, change_percent=20, scenario_name="rainfall_increase_20pct"
        )
        df_rain_inc.to_csv(output_dir / "scenario_rainfall_increase_20pct.csv", index=False)
        
        # Scenario 2: Rainfall decrease 20% (drought)
        df_rain_dec, impact_rain_dec = simulator.simulate_rainfall_change(
            features_v2_df, change_percent=-20, scenario_name="rainfall_decrease_20pct"
        )
        df_rain_dec.to_csv(output_dir / "scenario_rainfall_decrease_20pct.csv", index=False)
        
        # Scenario 3: Regional drought (moderate)
        df_drought, impact_drought = simulator.simulate_regional_drought(
            features_v2_df, drought_severity='moderate'
        )
        df_drought.to_csv(output_dir / "scenario_regional_drought_moderate.csv", index=False)
        
        # Scenario 4: Fertilizer optimization (15% reduction)
        df_fert, impact_fert = simulator.simulate_fertilizer_optimization(
            activity_anomaly_df, features_v2_df, reduction_target_pct=15
        )
        df_fert.to_csv(output_dir / "scenario_fertilizer_optimization_15pct.csv", index=False)
        
        # Get summary
        summary = simulator.get_all_scenarios_summary()
        
        logger.info("\n" + "=" * 80)
        logger.info("SCENARIO SIMULATIONS COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total scenarios created: {summary['total_scenarios']}")
        
        return summary
        
    except Exception as e:
        logger.error(f"Scenario simulations failed: {e}", exc_info=True)
        raise
