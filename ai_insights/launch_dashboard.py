from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def launch_dashboard(project_root: Optional[Path] = None) -> subprocess.Popen:
    """Launch Streamlit dashboard as a background process.

    Returns the Popen handle.
    """
    root = (project_root or Path(__file__).resolve().parents[1]).resolve()
    app_path = root / "ai_insights" / "dashboard_app.py"

    port = os.getenv("AI_DASHBOARD_PORT", "8501").strip() or "8501"

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        port,
        "--server.address",
        "localhost",
    ]

    # Use project root as cwd so relative paths behave.
    return subprocess.Popen(cmd, cwd=str(root))
