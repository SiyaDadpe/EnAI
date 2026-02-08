# Team Tasks - What's Left to Implement

## ✅ Data Engineering (COMPLETE)

**Owner**: Siya  
**Status**: Done and ready to use

**What's delivered**:
- Clean validated datasets in `data/output/`
- Full pipeline: ingestion → validation → filtering
- Lineage tracking and audit logs
- Schema configuration system

---

## ✅ ML Team - Anomaly Detection (COMPLETE)

**Owner**: Ronit  
**Status**: Done and ready for AI/Features teams

**What's delivered**:
- 3 trained anomaly detection models in `models/`
- Anomaly-flagged datasets in `data/ml_output/`
- Performance report with metrics
- ML pipeline runner (`ml_pipeline.py`)

**Models Implemented**:
1. ✅ **Isolation Forest for Weather** (50K rows analyzed)
   - Detected 2,500 anomalies (5.0%)
   - Features: temperature, rainfall, ratios, temporal patterns
   - Model: `models/weather_isolation_forest.pkl`

2. ✅ **Local Outlier Factor for Activity Logs** (30K rows analyzed)
   - Detected 1,374 anomalies (4.58%)
   - Features: irrigation hours, fertilizer, crop type, region
   - Model: `models/activity_lof.pkl`

3. ✅ **Statistical Z-Score for Station Regions** (800 stations analyzed)
   - Detected 8 anomalous stations (1.0%)
   - Compares stations to regional averages
   - Model: `models/station_statistical.pkl`

**Output Files** (in `data/ml_output/`):
- `anomaly_flagged_Weather.csv` (with anomaly_score, is_anomaly, anomaly_reason)
- `anomaly_flagged_Activity Logs.csv` (with anomaly_score, is_anomaly, anomaly_reason)
- `anomaly_flagged_Station Region.csv` (with anomaly_score, is_anomaly, anomaly_reason)
- `ml_performance_report.json` (complete metrics and statistics)

**Total Anomalies Detected**: 3,882 across all datasets

**To re-run**: `python ml_pipeline.py` (completes in ~15 seconds)

---

## 🤖 AI Team - Explanations & Insights

**Owner**: Me, Myself and I
**Status**: Done and fully integrated

**What's delivered**:
- Automated AI explanations report (PDF/JSON) in `data/ai_output/`
- Interactive Streamlit dashboard (auto-launches after pipeline)
- Alert system for critical anomalies
- All explanations, summaries, and recommendations generated from pipeline artifacts and ML outputs

**How it works**:
- Run `main.py` to execute the full pipeline, generate explanations, and launch the dashboard
- Outputs:
  - `data/ai_output/ai_explanations_report.pdf` (PDF)
  - `data/ai_output/ai_explanations_report.json` (JSON)
  - Streamlit dashboard at `http://localhost:8501` (shows quality, anomalies, decisions)
  - Alerts in `data/ai_output/alerts.json` (optional)

**API Setup**: Gemini/OpenAI API keys can be set in `.env` for LLM-powered explanations (optional)

**To re-run**: `python main.py` (completes pipeline, explanations, dashboard)

**Example workflow**:
1. Run `python main.py` (with `.env` toggles for AI features)
2. Review PDF/JSON report in `data/ai_output/`
3. Explore interactive dashboard (auto-launches)
4. Alerts and recommendations available for downstream teams

---

## 📊 Features Team - Feature Engineering

**Input Files**:
- All validated CSVs from `data/output/`
- `data/ml_output/anomaly_flagged_*.csv` (ML team's anomaly scores)
- AI team's insights (when available)

**Tasks**:
1. **Feature Engineering v1 (Baseline)**:
   - Merge Weather + Station Region on station codes
   - Create time-based features (day_of_week, month, season)
   - Calculate rolling averages (7-day rainfall, temperature trends)
   - Unit conversions using Reference Units table

2. **Feature Engineering v2 (Advanced)**:
   - Cross-dataset features (weather impact on irrigation)
   - Lag features (yesterday's rainfall → today's irrigation)
   - Aggregations by region (regional rainfall totals)
   - Anomaly interaction features

3. **Scenario Simulation**:
   - "What if" rainfall increases 20%?
   - Regional drought simulation
   - Fertilizer optimization scenarios

4. **Deliverables**:
   - Feature catalog (documentation of all features)
   - Versioned feature datasets (`features_v1.csv`, `features_v2.csv`)
   - Feature importance analysis
   - Scenario simulation results

---

## 📁 Where to Find Everything

### Validated Data (Your starting point)
```
data/output/
├── validated_Weather.csv
├── validated_Station Region.csv
├── validated_Activity Logs.csv
├── validated_Reference Units.csv
└── metadata.json  <- Lineage, stats, validation reports
```

### ML Outputs (Ready for AI & Features teams)
```
data/ml_output/
├── anomaly_flagged_Weather.csv
├── anomaly_flagged_Activity Logs.csv
├── anomaly_flagged_Station Region.csv
└── ml_performance_report.json

models/
├── weather_isolation_forest.pkl
├── activity_lof.pkl
└── station_statistical.pkl
```

### Logs (For AI team)
```
pipeline.log  <- Execution details
audit.log     <- Governance events
```

### Metadata Example
```json
{
  "lineage_graph": {
    "ingested_Weather.csv": {
      "stats": {
        "row_count": 50000,
        "missing_values": {"observationdate": 24920, "temperature": 2488}
      }
    }
  }
}
```

---

## 🚀 Getting Started

### ML Team ✅ (COMPLETE)
```bash
# Re-run ML pipeline anytime
python ml_pipeline.py

# Or load existing models
import joblib
weather_model = joblib.load('models/weather_isolation_forest.pkl')
```

### AI Team (Ready to start!)
```bash
import pandas as pd

# Load validated data
weather = pd.read_csv('data/output/validated_Weather.csv')
activities = pd.read_csv('data/output/validated_Activity Logs.csv')

# Start building anomaly detection
from sklearn.ensemble import IsolationForest
model = IsolationForest(contamination=0.1)
weather['anomaly_score'] = model.fit_predict(weather[['temperature', 'rainfall']])
```

### AI Team (Ready to start!)
```bash
import pandas as pd
import json

# Load ML team's anomaly outputs
weather_anomalies = pd.read_csv('data/ml_output/anomaly_flagged_Weather.csv')
activity_anomalies = pd.read_csv('data/ml_output/anomaly_flagged_Activity Logs.csv')

# Load metadata
with open('data/output/metadata.json') as f:
    metadata = json.load(f)

# Get validation stats
for file, info in metadata['lineage_graph'].items():
    if info['stage'] == 'validation':
        print(f"{file}: {info['validation_report']}")

# Generate summary with LLM
# (Use OpenAI API to explain quality issues)
```

### Features Team (Ready to start!)
```bash
import pandas as pd

# Load all datasets
weather = pd.read_csv('data/output/validated_Weather.csv')
stations = pd.read_csv('data/output/validated_Station Region.csv')
activities = pd.read_csv('data/output/validated_Activity Logs.csv')

# Load ML anomaly scores
weather_with_anomalies = pd.read_csv('data/ml_output/anomaly_flagged_Weather.csv')

# Merge datasets
merged = weather.merge(stations, left_on='stationid', right_on='stationcode')

# Create features
merged['day_of_week'] = pd.to_datetime(merged['observationdate']).dt.dayofweek
merged['month'] = pd.to_datetime(merged['observationdate']).dt.month
```

---

## ⏱️ Timeline Suggestion

**Day 1-2**: ✅ ML team builds anomaly detection (COMPLETE)  
**Day 2-3**: AI team generates explanations (can start now - ML output ready)  
**Day 3-4**: Features team creates v1 features (can start now - validated data ready)  
**Day 4-5**: Features team creates v2 + scenarios (needs ML anomaly scores - ready now)  
**Day 5**: Integration & final dashboard

---

## 🆘 Need Help?

**Data issues**: Check `pipeline.log` and `metadata.json`  
**Schema questions**: See `config/schema_config.py`  
**Re-run pipeline**: `python main.py` (safe to re-run anytime)

**Questions about data quality?**
- ✅ 50K rows in Weather.csv (50% have missing dates - validated and cleaned)
- ✅ 30K rows in Activity Logs.csv (validated and cleaned)
- ✅ 800 stations in Station Region.csv (validated and cleaned)
- ✅ 3,882 anomalies detected across all datasets (ready for analysis)
- Everything is validated, clean, and anomaly-flagged!
