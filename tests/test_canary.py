"""Leakage canary integration test is blocked until the real holdout exists.

The previous test sampled random catalogue pixels and treated that as a canary. That
is not the segment-buffered hidden set required by the project contract.
"""
from pathlib import Path
import pytest


def test_feature_alone_leakage_canary():
    required = [
        Path("data/sample_submission.tif"),
        Path("data/training_features.tif"),
        Path("data/labels.tif"),
        Path("data/prepared_manifest.json"),
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        pytest.skip("official inputs unavailable; leakage canary NOT RUN: " + ", ".join(missing))
    pytest.skip("official data exist, but the segment-buffered holdout and C1 feature canary are not implemented yet")
