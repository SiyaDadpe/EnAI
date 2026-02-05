# Enterprise Data Engineering Pipeline

**Applied AI Challenge - Data Ingestion & Validation**

Clean data pipeline that ingests messy CSV files and produces validated datasets ready for ML/AI teams.

---

## 🎯 What This Does

Transforms raw, messy CSV files into clean, validated datasets:

- **Robust CSV ingestion** with encoding detection
- **Schema validation** (required columns, data types, value ranges)
- **Data quality checks** (missing values, duplicates, outliers)
- **Full lineage tracking** and audit logging
- **Idempotent** (safe to re-run with updated data)

---

## 📁 Project Structure

```
EnAI/
├── data/
│   ├── raw/                # Input: Raw CSV files from hackathon
│   ├── validated/          # Output: Clean validated data
│   └── output/             # Output: Final datasets + metadata
│
├── config/
│   ├── schema_config.py    # Schema definitions for each CSV
│   └── pipeline_config.py  # Pipeline settings
│
├── ingestion/              # CSV reading with encoding detection
│   ├── csv_reader.py
│   └── schema_inference.py
│
├── validation/             # Schema & quality validation
│   ├── schema_validator.py
│   └── quality_checker.py
│
├── governance/             # Lineage tracking & audit logs
│   ├── lineage_tracker.py
│   └── audit_logger.py
│
├── utils/
│   └── logger.py
│
├── main.py                 # Pipeline runner
└── requirements.txt
```

---

## 📊 Datasets

Four real-world CSVs already in [`data/raw/`](data/raw):

1. **Weather.csv** (~50K rows, 3MB)
   - Columns: StationID, observationDate, rainfall, rain_unit, temperature, temperature_unit
   - Issues: Mixed date formats, missing values, inconsistent units

2. **Station Region.csv** (~800 rows)
   - Columns: stationCode, Region, region_type
   - Issues: Duplicates, inconsistent casing

3. **Activity Logs.csv** (~30K rows, 1.6MB)
   - Columns: region, activityDate, cropType, irrigationHours, fertilizer_amount
   - Issues: Mixed date formats, NA values

4. **Reference Units.csv** (~4 rows)
   - Columns: unit, standard_unit, conversion_factor
   - Issues: Missing conversion factors

---

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Create conda environment
conda create -n enai python=3.10 -y
conda activate enai

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Pipeline

```bash
python main.py
```

### 3. Check Results

```bash
# Validated datasets (ready for ML/AI teams)
ls data/output/

# Logs
tail pipeline.log
tail audit.log

# Lineage metadata
cat data/output/metadata.json | python -m json.tool
```

---

## 📈 Data Flow

```
RAW CSVs (data/raw/)
    ↓
[Ingestion] → Encoding detection, type conversion, schema inference
    ↓
[Validation] → Schema checks, quality checks, duplicate detection
    ↓
[Filtering] → Remove invalid rows (logged)
    ↓
VALIDATED DATA (data/output/validated_*.csv)
    ↓
ML/AI Teams use this for training & analysis
```

---

## ⚙️ Configuration

### Update Schemas

Edit [`config/schema_config.py`](config/schema_config.py):

```python
WEATHER_SCHEMA = {
    "name": "Weather",
    "columns": {
        "stationid": {"type": "string", "required": True},
        "observationdate": {"type": "datetime", "required": True},
        "temperature": {"type": "float", "required": True, "range": [-50, 60]},
        # ...
    },
    "unique_keys": ["stationid", "observationdate"],
}
```

### Adjust Pipeline Behavior

Edit [`config/pipeline_config.py`](config/pipeline_config.py):

```python
CHUNK_SIZE = 10000                    # Rows per chunk for large files
MAX_MISSING_RATIO = 0.5               # Max missing values per row
DUPLICATE_ACTION = "flag"             # "flag", "keep_first", "keep_last"
MIN_COMPLETENESS_THRESHOLD = 0.8      # 80% required fields must be present
```

---

## 📊 Outputs

### 1. Validated Datasets

Located in [`data/output/`](data/output/):

```
validated_Weather.csv
validated_Station Region.csv
validated_Activity Logs.csv
validated_Reference Units.csv
```

### 2. Metadata & Lineage

[`data/output/metadata.json`](data/output/metadata.json):

```json
{
  "metadata": {
    "pipeline_start": "2026-02-06T00:23:37",
    "pipeline_end": "2026-02-06T00:23:38"
  },
  "lineage_graph": {
    "ingested_Weather.csv": {
      "stage": "ingestion",
      "stats": { "row_count": 50000, "column_count": 6 }
    },
    "validated_Weather.csv": {
      "stage": "validation",
      "validation_report": { "valid_rows": 19903, "invalid_rows": 30097 }
    }
  }
}
```

### 3. Logs

- **pipeline.log**: Full pipeline execution log
- **audit.log**: Governance & compliance events

---

## 🔍 Debugging

```bash
# Check pipeline logs
tail -50 pipeline.log

# Check specific file ingestion
python -c "
from ingestion.schema_inference import ingest_csv_with_schema
from pathlib import Path
df, meta = ingest_csv_with_schema(Path('data/raw/Weather.csv'))
print(f'Ingested: {len(df)} rows, {len(df.columns)} columns')
print(df.head())
"

# Test validation
python -c "
from validation.schema_validator import validate_schema
from config.schema_config import WEATHER_SCHEMA
import pandas as pd

df = pd.read_csv('data/raw/Weather.csv')
report = validate_schema(df, WEATHER_SCHEMA)
print(f\"Valid: {report['valid_count']}/{report['total_rows']}\")
"
```

---

## 👥 For Your Teammates

### ML Team

**Use these files for training:**
- `data/output/validated_Weather.csv`
- `data/output/validated_Station Region.csv`  
- `data/output/validated_Activity Logs.csv`
- `data/output/validated_Reference Units.csv`

**Metadata available in:**
- `data/output/metadata.json` (lineage, stats, validation reports)

### AI Team

**Inputs for explanations:**
- Pipeline logs: `pipeline.log`, `audit.log`
- Validation reports in `metadata.json`
- Invalid row counts and reasons

### Features Team

**Feature engineering inputs:**
- All validated CSVs in `data/output/`
- Column stats and data types in `metadata.json`

---

## 📝 Notes

- **Idempotent**: Safe to re-run weekly as new data arrives
- **Schema-driven**: Update schemas in `config/schema_config.py` as data evolves
- **Validated data only**: Invalid rows are filtered out and logged
- **Full lineage**: Track data from raw → validated in metadata.json

---

## 🔧 Requirements

```
pandas>=2.0.0
numpy>=1.24.0
chardet>=5.0.0
```

See [`requirements.txt`](requirements.txt) for full list.
