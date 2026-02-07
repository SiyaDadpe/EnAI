from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from ai_insights.llm import llm_generate_text
from ai_insights.parsers import ParsedInputs, parse_pipeline_quality_signals


def _pct(n: float, d: float) -> float:
    return 0.0 if d == 0 else (n / d) * 100.0


def build_data_quality_section(metadata: Dict[str, Any], pipeline_log_text: str) -> Dict[str, Any]:
    lineage = metadata.get("lineage_graph", {}) or {}

    datasets: List[Dict[str, Any]] = []
    for name, info in lineage.items():
        stage = info.get("stage")
        if stage != "ingestion":
            continue

        stats = info.get("stats", {}) or {}
        row_count = float(stats.get("row_count", 0) or 0)
        missing_values = stats.get("missing_values", {}) or {}

        missing_pct = {
            col: round(_pct(float(miss or 0), row_count), 2)
            for col, miss in missing_values.items()
        }

        worst = sorted(missing_pct.items(), key=lambda kv: kv[1], reverse=True)[:5]

        datasets.append(
            {
                "dataset": name,
                "row_count": int(row_count),
                "column_count": int(stats.get("column_count", 0) or 0),
                "missing_values": missing_values,
                "missing_pct": missing_pct,
                "top_missing_columns": [{"column": c, "missing_pct": p} for c, p in worst],
                "dtypes": stats.get("dtypes", {}),
            }
        )

    signals = parse_pipeline_quality_signals(pipeline_log_text)

    # LLM narrative summary
    prompt = {
        "task": "Summarize data quality issues per dataset for an executive report.",
        "inputs": {
            "datasets": datasets,
            "pipeline_log_signals": {
                "required_column_completeness": signals.get("required_column_completeness", [])[:10],
                "duplicate_key_warnings": signals.get("duplicate_key_warnings", [])[:10],
                "errors": signals.get("errors", [])[:5],
            },
        },
        "requirements": [
            "Write 3-6 bullet points total.",
            "Use only numbers present in inputs.",
            "Call out missing date columns explicitly.",
        ],
    }

    llm = llm_generate_text("Return bullet points only.\n\n" + json.dumps(prompt, indent=2))

    return {
        "datasets": datasets,
        "pipeline_signals": signals,
        "narrative": llm,
    }


def build_anomaly_section(anomalies: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    section: Dict[str, Any] = {"datasets": {}}

    for key, df in anomalies.items():
        if df is None or df.empty:
            section["datasets"][key] = {"total_rows": 0, "anomalies": 0, "top_anomalies": []}
            continue

        # normalize is_anomaly
        if "is_anomaly" in df.columns:
            is_anom = df["is_anomaly"].astype(str).str.lower().isin(["true", "1", "yes"])
        else:
            is_anom = pd.Series([False] * len(df))

        anom_df = df[is_anom].copy()

        # Score field differs slightly; expected anomaly_score
        if "anomaly_score" in anom_df.columns:
            anom_df["_score"] = pd.to_numeric(anom_df["anomaly_score"], errors="coerce")
        else:
            anom_df["_score"] = 0.0

        top = anom_df.sort_values("_score", ascending=False).head(15)

        # keep a compact record for PDF
        records = []
        for _, row in top.iterrows():
            rec = {}
            for col in df.columns:
                if col in {"anomaly_reason", "anomaly_score", "is_anomaly"}:
                    rec[col] = row.get(col)
            # include identifiers and key numerics
            for col in ["stationid", "stationcode", "region", "observationdate", "activitydate", "temperature", "rainfall", "irrigationhours", "fertilizer_amount"]:
                if col in df.columns:
                    rec[col] = row.get(col)
            records.append(rec)

        section["datasets"][key] = {
            "total_rows": int(len(df)),
            "anomalies": int(len(anom_df)),
            "top_anomalies": records,
        }

    # LLM explains representative anomalies, not all.
    prompt = {
        "task": "Explain why the representative anomalies are anomalous, with simple domain reasoning.",
        "requirements": [
            "Provide explanations grouped by dataset: weather, activity, station.",
            "For each dataset, explain 3-5 representative anomalies.",
            "Avoid speculation; refer to missing/invalid values and extreme magnitudes.",
        ],
        "top_anomalies": section["datasets"],
    }

    llm = llm_generate_text(json.dumps(prompt, indent=2))

    section["narrative"] = llm
    return section


def build_decision_support(data_quality: Dict[str, Any], anomalies: Dict[str, Any]) -> Dict[str, Any]:
    prompt = {
        "task": "Provide decision support recommendations based on quality issues and anomalies.",
        "requirements": [
            "Return plain text only (no JSON, no braces).",
            "Use exactly three headings: Data Quality Actions, Station Maintenance, Suspicious Activity Patterns.",
            "Under each heading, provide 3-6 bullet points starting with '- '.",
            "Tie each recommendation to evidence from inputs; do not invent numbers.",
        ],
        "inputs": {
            "data_quality_top_missing": {
                d["dataset"]: d.get("top_missing_columns", [])
                for d in data_quality.get("datasets", [])
            },
            "pipeline_errors": (data_quality.get("pipeline_signals", {}).get("errors", []) or [])[:5],
            "anomaly_counts": {
                k: {
                    "anomalies": v.get("anomalies"),
                    "total_rows": v.get("total_rows"),
                }
                for k, v in (anomalies.get("datasets", {}) or {}).items()
            },
            "station_top": (anomalies.get("datasets", {}) or {}).get("station", {}).get("top_anomalies", [])[:5],
        },
    }

    llm = llm_generate_text("Return plain text only.\n\n" + json.dumps(prompt, indent=2))
    return {"narrative": llm}


def build_report(parsed: ParsedInputs) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "report_version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "inputs_present": {
            "metadata": bool(parsed.metadata),
            "audit_events": len(parsed.audit_events),
            "pipeline_log_chars": len(parsed.pipeline_log_text or ""),
            "ml_performance": bool(parsed.ml_performance),
            "anomaly_datasets": list(parsed.anomalies.keys()),
        },
    }

    data_quality = build_data_quality_section(parsed.metadata, parsed.pipeline_log_text)
    anomalies = build_anomaly_section(parsed.anomalies)
    decisions = build_decision_support(data_quality, anomalies)

    report["data_quality"] = data_quality
    report["anomalies"] = anomalies
    report["decision_support"] = decisions

    # Add audit errors for transparency
    audit_errors = [e for e in parsed.audit_events if e.get("event_type") == "error"]
    report["audit"] = {
        "events_total": len(parsed.audit_events),
        "errors_total": len(audit_errors),
        "errors_sample": audit_errors[:10],
    }

    report["ml_performance"] = parsed.ml_performance

    return report


def save_json(report: Dict[str, Any], path: Path) -> None:
    def sanitize(obj: Any) -> Any:
        """Convert non-JSON values (NaN/Inf/pandas NA/numpy scalars) to JSON-safe types.

        This intentionally produces strict JSON (no NaN literals).
        """
        if obj is None or isinstance(obj, (str, bool, int)):
            return obj

        # Handle dict/list containers
        if isinstance(obj, dict):
            return {str(k): sanitize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [sanitize(v) for v in obj]

        # numpy / pandas scalars
        if hasattr(obj, "item") and callable(getattr(obj, "item")):
            try:
                return sanitize(obj.item())
            except Exception:
                pass

        # pandas Timestamp
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()

        # floats: ensure strict JSON (no NaN/Infinity)
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj

        # pandas missing values (NA/NaT)
        try:
            if pd.isna(obj):
                return None
        except Exception:
            pass

        # fallback
        return str(obj)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sanitize(report), f, indent=2, ensure_ascii=False, allow_nan=False)
