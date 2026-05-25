from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_trajectory_renders() -> None:
    out = REPO / "docs" / "building-trajectory.md"
    r = subprocess.run(
        ["uv", "run", "python", str(REPO / "scripts" / "build_trajectory.py")],
        cwd=REPO, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    text = out.read_text()
    assert "J-FIBO Building Trajectory" in text
    assert "terms contributed" in text
    assert "Mermaid timeline" in text
