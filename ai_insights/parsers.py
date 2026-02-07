from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd


@dataclass(frozen=True)
class ParsedInputs:
    metadata: Dict[str, Any]
    audit_events: List[Dict[str, Any]]
    pipeline_log_text: str
    ml_performance: Dict[str, Any]
    anomalies: Dict[str, pd.DataFrame]


def read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_audit_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    events: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def load_anomaly_csvs(ml_output_dir: Path) -> Dict[str, pd.DataFrame]:
    """Loads known anomaly outputs from ML pipeline.

    Returns mapping keys: weather, activity, station.
    """
    mapping = {
        "weather": ml_output_dir / "anomaly_flagged_Weather.csv",
        "activity": ml_output_dir / "anomaly_flagged_Activity Logs.csv",
        "station": ml_output_dir / "anomaly_flagged_Station Region.csv",
    }
    out: Dict[str, pd.DataFrame] = {}
    for key, p in mapping.items():
        if p.exists():
            out[key] = pd.read_csv(p)
        else:
            out[key] = pd.DataFrame()
    return out


def parse_pipeline_quality_signals(pipeline_log_text: str) -> Dict[str, Any]:
    """Extracts a few useful signals from pipeline.log.

    This is intentionally lightweight and best-effort.
    """
    signals: Dict[str, Any] = {
        "errors": [],
        "warnings": [],
        "required_column_completeness": [],
        "duplicate_key_warnings": [],
        "validation_summary": [],
        "quality_summary": [],
    }

    for line in pipeline_log_text.splitlines():
        if " - ERROR - " in line:
            signals["errors"].append(line)
        if " - WARNING - " in line:
            signals["warnings"].append(line)

        # Required column completeness warnings
        m = re.search(r"Required column '([^']+)' is only ([0-9.]+)% complete", line)
        if m:
            signals["required_column_completeness"].append(
                {"column": m.group(1), "completeness_pct": float(m.group(2)), "raw": line}
            )

        # Duplicate key warnings (schema validator)
        m = re.search(r"Found (\d+) rows with duplicate keys on \[(.+?)\]", line)
        if m:
            signals["duplicate_key_warnings"].append(
                {"duplicate_rows": int(m.group(1)), "keys": m.group(2), "raw": line}
            )

        # Validation / Quality summary lines
        m = re.search(r"Validation: (\d+)/(\d+) rows passed", line)
        if m:
            signals["validation_summary"].append(
                {"passed": int(m.group(1)), "total": int(m.group(2)), "raw": line}
            )
        m = re.search(r"Quality: (\d+)/(\d+) rows passed", line)
        if m:
            signals["quality_summary"].append(
                {"passed": int(m.group(1)), "total": int(m.group(2)), "raw": line}
            )

    return signals


def parse_all(
    metadata_path: Path,
    audit_log_path: Path,
    pipeline_log_path: Path,
    ml_performance_path: Path,
    ml_output_dir: Path,
) -> ParsedInputs:
    metadata = read_json(metadata_path) if metadata_path.exists() else {}
    audit_events = read_audit_jsonl(audit_log_path)
    pipeline_log_text = read_text(pipeline_log_path)
    ml_performance = read_json(ml_performance_path) if ml_performance_path.exists() else {}
    anomalies = load_anomaly_csvs(ml_output_dir)

    return ParsedInputs(
        metadata=metadata,
        audit_events=audit_events,
        pipeline_log_text=pipeline_log_text,
        ml_performance=ml_performance,
        anomalies=anomalies,
    )
