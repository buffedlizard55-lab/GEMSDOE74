"""Safety checks: legacy entry points must not make synthetic competition results."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_submission_generator_fails_closed_without_creating_artifacts(tmp_path):
    out = tmp_path / "must-not-be-created"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/generate_submission.py"), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "no competition prediction was generated" in result.stderr
    assert not out.exists()


def test_legacy_holdout_entrypoints_fail_closed():
    for script in ("evaluate_holdout.py", "evaluate_holdout_segments.py"):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 2
        assert "BLOCKED" in result.stderr
