from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import streamlit as st


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_report_path() -> Path:
    return _project_root() / "data" / "ai_output" / "ai_explanations_report.json"


def _load_report(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _render_quality(report: Dict[str, Any]) -> None:
    dq = report.get("data_quality", {}) or {}
    st.subheader("Data Quality")

    narrative = (dq.get("narrative", {}) or {}).get("text")
    if narrative:
        st.markdown(narrative)

    datasets = dq.get("datasets", []) or []
    if not datasets:
        st.info("No dataset stats found in metadata.json.")
        return

    ds_names = [d.get("dataset", "") for d in datasets]
    selected = st.selectbox("Dataset", ds_names)
    ds = next((d for d in datasets if d.get("dataset") == selected), None) or {}

    c1, c2 = st.columns(2)
    c1.metric("Rows", ds.get("row_count", 0))
    c2.metric("Columns", ds.get("column_count", 0))

    top_missing = ds.get("top_missing_columns", []) or []
    if top_missing:
        st.caption("Top missing columns")
        st.dataframe(pd.DataFrame(top_missing), use_container_width=True)

    with st.expander("All missing percentages"):
        mp = ds.get("missing_pct", {}) or {}
        if mp:
            df = pd.DataFrame([{"column": k, "missing_pct": v} for k, v in mp.items()])
            st.dataframe(df.sort_values("missing_pct", ascending=False), use_container_width=True)

    with st.expander("Pipeline log signals (errors/warnings)"):
        sig = dq.get("pipeline_signals", {}) or {}
        st.write({
            "errors_count": len(sig.get("errors", []) or []),
            "warnings_count": len(sig.get("warnings", []) or []),
        })
        st.text("\n".join((sig.get("errors", []) or [])[:20]))


def _render_anomalies(report: Dict[str, Any]) -> None:
    an = report.get("anomalies", {}) or {}
    st.subheader("Anomalies")

    narrative = (an.get("narrative", {}) or {}).get("text")
    if narrative:
        st.markdown(narrative)

    datasets = an.get("datasets", {}) or {}
    if not datasets:
        st.info("No anomaly datasets found. Re-run `python ml_pipeline.py` if needed.")
        return

    key = st.selectbox("Anomaly dataset", list(datasets.keys()))
    obj = datasets.get(key, {}) or {}

    c1, c2 = st.columns(2)
    c1.metric("Total rows", obj.get("total_rows", 0))
    c2.metric("Anomalies", obj.get("anomalies", 0))

    top = obj.get("top_anomalies", []) or []
    if top:
        st.caption("Top anomalies (representative)")
        st.dataframe(pd.DataFrame(top), use_container_width=True)


def _render_decisions(report: Dict[str, Any]) -> None:
    ds = report.get("decision_support", {}) or {}
    st.subheader("Decision Support")

    text = (ds.get("narrative", {}) or {}).get("text") or ""
    if not text.strip():
        st.info("No decision-support narrative found.")
        return

    st.markdown(text)


def main() -> None:
    st.set_page_config(page_title="EnAI Insights", layout="wide")
    st.title("EnAI – AI Explanations & Insights")

    report_path = _default_report_path()

    st.caption(f"Report source: {report_path}")

    if not report_path.exists():
        st.error("AI report JSON not found.")
        st.code("$env:AI_REPORT_ON_RUN='1'; python main.py\n# or\npython -m ai_insights.generate_pdf_report")
        return

    report = _load_report(report_path)

    tabs = st.tabs(["Quality", "Anomalies", "Decision Support"])
    with tabs[0]:
        _render_quality(report)
    with tabs[1]:
        _render_anomalies(report)
    with tabs[2]:
        _render_decisions(report)


if __name__ == "__main__":
    main()
