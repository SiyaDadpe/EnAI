from __future__ import annotations

import argparse
from pathlib import Path

from ai_insights.config import get_paths, load_env
from ai_insights.parsers import parse_all
from ai_insights.report import build_report, save_json
from ai_insights.pdf_writer import write_pdf


def generate(out_dir: Path | None = None) -> tuple[Path, Path]:
    """Generate the AI explanations report.

    Returns:
        (json_path, pdf_path)
    """
    paths = get_paths()
    load_env(paths.project_root)

    resolved_out_dir = out_dir or paths.ai_output_dir
    resolved_out_dir.mkdir(parents=True, exist_ok=True)

    parsed = parse_all(
        metadata_path=paths.metadata_json,
        audit_log_path=paths.audit_log,
        pipeline_log_path=paths.pipeline_log,
        ml_performance_path=paths.ml_performance_report,
        ml_output_dir=paths.ml_output_dir,
    )

    report = build_report(parsed)

    json_path = resolved_out_dir / "ai_explanations_report.json"
    pdf_path = resolved_out_dir / "ai_explanations_report.pdf"

    save_json(report, json_path)
    write_pdf(report, pdf_path)

    return json_path, pdf_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI explanations report (JSON + PDF) from pipeline artifacts.")
    parser.add_argument("--out-dir", default=None, help="Output directory (default: data/ai_output)")
    parser.add_argument("--pdf", default="ai_explanations_report.pdf", help="PDF filename")
    parser.add_argument("--json", default="ai_explanations_report.json", help="JSON filename")
    args = parser.parse_args()

    paths = get_paths()
    load_env(paths.project_root)

    out_dir = Path(args.out_dir) if args.out_dir else paths.ai_output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    parsed = parse_all(
        metadata_path=paths.metadata_json,
        audit_log_path=paths.audit_log,
        pipeline_log_path=paths.pipeline_log,
        ml_performance_path=paths.ml_performance_report,
        ml_output_dir=paths.ml_output_dir,
    )

    report = build_report(parsed)

    json_path = out_dir / args.json
    pdf_path = out_dir / args.pdf

    save_json(report, json_path)
    write_pdf(report, pdf_path)

    print(f"[OK] JSON report: {json_path}")
    print(f"[OK] PDF report:  {pdf_path}")

    llm_mode = ((report.get('data_quality', {}) or {}).get('narrative', {}) or {}).get('mode')
    if llm_mode and llm_mode != 'deterministic':
        print(f"[OK] LLM mode: {llm_mode}")
    else:
        print("[INFO] LLM not configured; generated deterministic report.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
