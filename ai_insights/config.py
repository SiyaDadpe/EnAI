from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class AIInsightsPaths:
    project_root: Path

    pipeline_log: Path
    audit_log: Path
    metadata_json: Path

    ml_output_dir: Path
    ml_performance_report: Path

    ai_output_dir: Path


def get_paths(project_root: Optional[Path] = None) -> AIInsightsPaths:
    root = (project_root or Path(__file__).resolve().parents[1]).resolve()

    data_dir = root / "data"
    output_dir = data_dir / "output"
    ml_output_dir = data_dir / "ml_output"

    return AIInsightsPaths(
        project_root=root,
        pipeline_log=root / "pipeline.log",
        audit_log=root / "audit.log",
        metadata_json=output_dir / "metadata.json",
        ml_output_dir=ml_output_dir,
        ml_performance_report=ml_output_dir / "ml_performance_report.json",
        ai_output_dir=data_dir / "ai_output",
    )


def load_env(project_root: Optional[Path] = None) -> None:
    """Loads .env from project root if present."""
    root = (project_root or Path(__file__).resolve().parents[1]).resolve()
    env_path = root / ".env"
    load_dotenv(dotenv_path=env_path, override=False)
