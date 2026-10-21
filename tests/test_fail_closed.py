from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(script: str, cwd: Path):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def test_submission_generator_refuses_missing_official_inputs(tmp_path):
    result = run("generate_submission.py", tmp_path)
    assert result.returncode == 2
    assert "No new TIFF was generated" in result.stderr
    assert not list(tmp_path.rglob("*.tif"))


def test_holdout_evaluator_refuses_proxy_score(tmp_path):
    result = run("evaluate_holdout.py", tmp_path)
    assert result.returncode == 2
    assert "no holdout score was computed" in result.stderr
    assert not list(tmp_path.rglob("*.json"))


def test_prepare_data_does_not_claim_success_when_inputs_absent(tmp_path):
    result = run("prepare_data.py", tmp_path)
    assert result.returncode == 2
    assert "Missing required real inputs" in result.stderr
    assert not (tmp_path / "data" / "prepared_manifest.json").exists()
