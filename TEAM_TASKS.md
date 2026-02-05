# Team Tasks - What's Left to Implement

## ✅ Data Engineering (COMPLETE)

**Owner**: You  
**Status**: Done and ready to use

**What's delivered**:
- Clean validated datasets in `data/output/`
- Full pipeline: ingestion → validation → filtering
- Lineage tracking and audit logs
- Schema configuration system

---

## 🔨 ML Team - Anomaly Detection

**Input Files**:
- `data/output/validated_Weather.csv` (2.6MB, 50K rows)
- `data/output/validated_Station Region.csv` (14KB, 800 rows)
- `data/output/validated_Activity Logs.csv` (1.4MB, 30K rows)
- `data/output/validated_Reference Units.csv` (conversion table)

**Tasks**:
1. **Build anomaly detection models**:
   - Isolation Forest for Weather data (temperature, rainfall outliers)
   - Local Outlier Factor (LOF) for Activity Logs patterns
   - Time-series anomaly detection for station observations

2. **Create output format**:
   - Add `anomaly_score` column (0-1 scale)
   - Add `is_anomaly` flag (True/False)
   - Add `anomaly_reason` text explanation

3. **Deliverables**:
   - Trained models saved to `models/`
   - Anomaly-flagged datasets in `data/ml_output/`
   - Model performance report (precision, recall)

**Where to start**: Use validated CSVs, they're already clean!

---

## 🤖 AI Team - Explanations & Insights

**Input Files**:
- `pipeline.log` (execution logs)
- `audit.log` (governance events)
- `data/output/metadata.json` (lineage & stats)
- ML team's anomaly outputs

**Tasks**:
1. **Data Quality Summaries**:
   - Read validation reports from metadata.json
   - Generate natural language summaries of data quality
   - Example: "Weather dataset has 50% missing observation dates, mainly in Oct-Dec period"

2. **Anomaly Explanations**:
   - Take ML team's flagged anomalies
   - Use LLM to explain WHY they're anomalous
   - Example: "Temperature of 85°C is anomalous because it exceeds normal range for this region"

3. **Decision Support**:
   - Recommend actions for data quality issues
   - Suggest which stations need maintenance
   - Identify suspicious activity patterns

4. **Deliverables**:
   - AI explanations report (PDF/JSON)
   - Interactive dashboard showing insights
   - Alert system for critical anomalies

**API Setup**: You'll need OpenAI/Anthropic API keys

---

## 📊 Features Team - Feature Engineering

**Input Files**:
- All validated CSVs from `data/output/`
- ML team's anomaly scores
- AI team's insights

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

### ML Team
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

### AI Team
```bash
import json

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

### Features Team
```bash
import pandas as pd

# Load all datasets
weather = pd.read_csv('data/output/validated_Weather.csv')
stations = pd.read_csv('data/output/validated_Station Region.csv')
activities = pd.read_csv('data/output/validated_Activity Logs.csv')

# Merge datasets
merged = weather.merge(stations, left_on='stationid', right_on='stationcode')

# Create features
merged['day_of_week'] = pd.to_datetime(merged['observationdate']).dt.dayofweek
merged['month'] = pd.to_datetime(merged['observationdate']).dt.month
```

---

## ⏱️ Timeline Suggestion

**Day 1-2**: ML team builds anomaly detection  
**Day 2-3**: AI team generates explanations (needs ML output)  
**Day 3-4**: Features team creates v1 features  
**Day 4-5**: Features team creates v2 + scenarios (needs ML anomaly scores)  
**Day 5**: Integration & final dashboard

---

## 🆘 Need Help?

**Data issues**: Check `pipeline.log` and `metadata.json`  
**Schema questions**: See `config/schema_config.py`  
**Re-run pipeline**: `python main.py` (safe to re-run anytime)

**Questions about data quality?**
- 50K rows in Weather.csv (50% have missing dates - that's real messy data!)
- 30K rows in Activity Logs.csv
- 800 stations in Station Region.csv
- Everything is already validated and clean
