from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def _clean_markdown_text(text: str) -> str:
    """Convert lightweight markdown-ish text to PDF-friendly HTML.

    - Converts leading '* ' / '- ' bullets to a bullet glyph.
    - Strips common markdown emphasis markers.
    - Escapes XML special characters for ReportLab Paragraph.
    """
    if not text:
        return ""

    lines: List[str] = []
    for raw in text.splitlines():
        s = raw.strip("\r")
        stripped = s.lstrip()

        # Bullet normalization
        if stripped.startswith("* ") or stripped.startswith("- "):
            s = "• " + stripped[2:]

        # Strip some markdown artifacts
        s = s.replace("**", "").replace("`", "")
        # Gemini/LLMs sometimes leave stray '*' (markdown). Remove them.
        s = s.replace("*", "")

        # Escape for ReportLab's mini-HTML
        s = escape(s)

        lines.append(s)

    return "<br/>".join(lines)


def _try_format_json_to_bullets(text: str) -> str:
    """If text is JSON-like, convert it to bullet-style plaintext."""
    if not text:
        return ""
    t = text.strip()
    if not ((t.startswith("{") and t.endswith("}")) or (t.startswith("[") and t.endswith("]"))):
        return text

    try:
        obj = json.loads(t)
    except Exception:
        return text

    def as_lines(o: Any, prefix: str = "") -> List[str]:
        if o is None:
            return []
        if isinstance(o, str):
            # keep multi-line strings
            return [prefix + line for line in o.splitlines() if line.strip()]
        if isinstance(o, list):
            lines: List[str] = []
            for item in o:
                if isinstance(item, (dict, list)):
                    lines.extend(as_lines(item, prefix=prefix))
                else:
                    lines.append(prefix + str(item))
            return lines
        if isinstance(o, dict):
            lines: List[str] = []
            for k, v in o.items():
                lines.append(f"{k}:")
                inner = as_lines(v, prefix="- ")
                if inner:
                    lines.extend(inner)
            return lines
        return [prefix + str(o)]

    return "\n".join(as_lines(obj))


def _render_anomaly_bullets(key: str, top: List[Dict[str, Any]]) -> str:
    """Create a compact bullet list for anomalies to avoid wide tables."""
    lines: List[str] = []
    for r in top[:10]:
        score = _safe_str(r.get("anomaly_score", ""))
        reason = _safe_str(r.get("anomaly_reason", "")).strip()
        if len(reason) > 180:
            reason = reason[:177] + "..."

        if key == "weather":
            ident = _safe_str(r.get("stationid", ""))
            dt = _safe_str(r.get("observationdate", ""))
            temp = _safe_str(r.get("temperature", ""))
            rain = _safe_str(r.get("rainfall", ""))
            lines.append(f"- Station {ident}, date {dt}, temp {temp}, rain {rain}, score {score}: {reason}")
        elif key == "activity":
            region = _safe_str(r.get("region", ""))
            dt = _safe_str(r.get("activitydate", ""))
            crop = _safe_str(r.get("croptype", ""))
            irr = _safe_str(r.get("irrigationhours", ""))
            fert = _safe_str(r.get("fertilizer_amount", ""))
            lines.append(f"- Region {region}, date {dt}, crop {crop}, irrigation {irr}, fertilizer {fert}, score {score}: {reason}")
        else:
            # fallback
            lines.append(f"- score {score}: {reason}")

    return "\n".join(lines)


def _col_widths(available_width: float, cols: List[str], weights: Dict[str, float]) -> List[float]:
    w = [float(weights.get(c, 1.0)) for c in cols]
    total = sum(w) if sum(w) > 0 else 1.0
    return [available_width * (x / total) for x in w]


def _make_wrapped_table(
    table_data: List[List[Any]],
    col_widths: List[float],
    font_size: int = 7,
    header_font_size: int = 8,
) -> Table:
    t = Table(table_data, colWidths=col_widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), header_font_size),
                ("FONTSIZE", (0, 1), (-1, -1), font_size),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t


def write_pdf(report: Dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=9, leading=11)
    tiny = ParagraphStyle("Tiny", parent=styles["BodyText"], fontSize=7, leading=9)
    story: List[Any] = []

    title = "AI Explanations & Insights Report"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"Generated at: {_safe_str(report.get('generated_at'))}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Data quality section
    story.append(Paragraph("Data Quality Summaries", styles["Heading1"]))
    dq = report.get("data_quality", {})
    narrative = (dq.get("narrative", {}) or {}).get("text")
    if narrative:
        story.append(Paragraph(_clean_markdown_text(narrative), small))
        story.append(Spacer(1, 8))

    datasets = dq.get("datasets", []) or []
    for ds in datasets:
        story.append(Paragraph(_safe_str(ds.get("dataset")), styles["Heading2"]))
        story.append(Paragraph(f"Rows: {ds.get('row_count')}, Cols: {ds.get('column_count')}", styles["Normal"]))

        top_missing = ds.get("top_missing_columns", []) or []
        if top_missing:
            table_data = [["Column", "Missing %"]] + [[m.get("column"), m.get("missing_pct")] for m in top_missing]
            page_width = letter[0]
            available_width = page_width - 72 * 2
            col_widths = _col_widths(available_width * 0.6, ["Column", "Missing %"], {"Column": 3, "Missing %": 1})
            t = _make_wrapped_table(table_data, col_widths, font_size=8, header_font_size=9)
            story.append(t)
            story.append(Spacer(1, 10))

    # Anomalies section
    story.append(Paragraph("Anomaly Explanations (Representative)", styles["Heading1"]))
    an = report.get("anomalies", {})
    an_narrative = (an.get("narrative", {}) or {}).get("text")
    if an_narrative:
        story.append(Paragraph(_clean_markdown_text(an_narrative), small))
        story.append(Spacer(1, 10))

    datasets = (an.get("datasets", {}) or {})
    for key, obj in datasets.items():
        story.append(Paragraph(f"Dataset: {key}", styles["Heading2"]))
        story.append(Paragraph(f"Anomalies: {obj.get('anomalies')} / {obj.get('total_rows')}", styles["Normal"]))
        top = obj.get("top_anomalies", []) or []
        if top:
            # Weather + Activity: render as compact bullet list to avoid table overflow.
            if key in {"weather", "activity"}:
                story.append(Paragraph(_clean_markdown_text(_render_anomaly_bullets(key, top)), small))
                story.append(Spacer(1, 12))
            else:
                # Station (and others): small wrapped table is fine.
                if key == "station":
                    cols = ["stationcode", "region", "temp_count", "temp_mean", "rain_mean", "anomaly_score", "anomaly_reason"]
                    weights = {"stationcode": 1.2, "region": 1.2, "temp_count": 1.0, "temp_mean": 1.0, "rain_mean": 1.0, "anomaly_score": 1.0, "anomaly_reason": 3.2}
                else:
                    cols = ["anomaly_score", "anomaly_reason"]
                    weights = {"anomaly_score": 1.0, "anomaly_reason": 4.0}

                page_width = letter[0]
                available_width = page_width - 72 * 2
                col_widths = _col_widths(available_width, cols, weights)

                header = [Paragraph(escape(c), tiny) for c in cols]
                table_data: List[List[Any]] = [header]

                for r in top[:12]:
                    row = [Paragraph(escape(_safe_str(r.get(c, ""))), tiny) for c in cols]
                    table_data.append(row)

                t = _make_wrapped_table(table_data, col_widths, font_size=7, header_font_size=8)
                story.append(t)
                story.append(Spacer(1, 12))

    # Decision support
    story.append(Paragraph("Decision Support", styles["Heading1"]))
    ds = report.get("decision_support", {})
    ds_text = (ds.get("narrative", {}) or {}).get("text")
    if ds_text:
        # If the LLM returned JSON, convert it to bullet points.
        ds_text = _try_format_json_to_bullets(ds_text)
        story.append(Paragraph(_clean_markdown_text(ds_text), small))
        story.append(Spacer(1, 12))

    # Audit errors sample
    story.append(Paragraph("Governance / Audit Notes", styles["Heading1"]))
    audit = report.get("audit", {})
    story.append(Paragraph(f"Audit events: {audit.get('events_total')} | Errors: {audit.get('errors_total')}", styles["Normal"]))

    out_doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    out_doc.build(story)
