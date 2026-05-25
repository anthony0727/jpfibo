from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run", "python", str(REPO / "scripts" / "validate.py"), *args],
        cwd=REPO, capture_output=True, text=True,
    )


@pytest.mark.parametrize("fixture", [
    "examples/policy-shareholding-valid.ttl",
    "examples/main-bank-candidate-valid.ttl",
    "examples/major-shareholder-valid.ttl",
])
def test_valid_examples_conform(fixture: str) -> None:
    r = _run(fixture)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("fixture", [
    "examples/policy-shareholding-invalid.ttl",
    "examples/main-bank-candidate-invalid.ttl",
    "examples/major-shareholder-invalid.ttl",
])
def test_invalid_examples_fail(fixture: str) -> None:
    r = _run(fixture, "--expect-fail")
    assert r.returncode == 0, r.stdout + r.stderr
