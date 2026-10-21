"""Tests for the submission validator and writer (format rules from the competition page)."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems74 import submission as sub  # noqa: E402

SHAPE = sub.EXPECTED_SHAPE


def _zeros():
    return np.zeros(SHAPE, np.float32)


def test_writer_round_trip_passes_validator(tmp_path):
    p = _zeros()
    p[100:103, 200] = 0.9
    out = tmp_path / "toy-check.tif"
    r = sub.write_submission(p, out, name="gems74-toy-check", note="format test only, not a prediction")
    assert r["validator"]["passed"]
    assert r["n_positive"] == 3
    assert r["sha256"] == sub.sha256_file(out)


def test_writer_rejects_values_outside_unit_interval(tmp_path):
    p = _zeros()
    p[0, 0] = 1.5
    with pytest.raises(ValueError):
        sub.write_submission(p, tmp_path / "bad.tif", name="gems74-bad", note="x")


def test_writer_rejects_long_note_and_bad_name(tmp_path):
    with pytest.raises(ValueError):
        sub.write_submission(_zeros(), tmp_path / "a.tif", name="gems74-a", note="x" * 201)
    with pytest.raises(ValueError):
        sub.write_submission(_zeros(), tmp_path / "b.tif", name="bad name!", note="x")


def test_validator_flags_negative_sentinel_inside_footprint(tmp_path):
    # Reproduces the organiser error "Predicted values must be in range [0, 1]":
    # a -3.4028234663852886e+38 sentinel written as data.
    import rasterio
    from rasterio.transform import Affine

    arr = _zeros()
    arr[10, 10] = -3.4028234663852886e38
    path = tmp_path / "sentinel.tif"
    with rasterio.open(
        path, "w", driver="GTiff", dtype="float32", count=1, height=SHAPE[0], width=SHAPE[1],
        crs=sub.EXPECTED_CRS, transform=Affine(*sub.EXPECTED_TRANSFORM),
    ) as dst:
        dst.write(arr, 1)
    rep = sub.validate_submission(path)
    assert not rep["passed"]
    assert rep["checks"]["finite_values_in_0_1"] is False
    assert rep["checks"]["no_sentinel_-3.4e38"] is False


def test_validator_flags_wrong_crs(tmp_path):
    import rasterio
    from rasterio.transform import Affine

    path = tmp_path / "wrongcrs.tif"
    with rasterio.open(
        path, "w", driver="GTiff", dtype="float32", count=1, height=SHAPE[0], width=SHAPE[1],
        crs="EPSG:4326", transform=Affine(*sub.EXPECTED_TRANSFORM),
    ) as dst:
        dst.write(_zeros(), 1)
    rep = sub.validate_submission(path)
    assert rep["checks"]["crs_epsg_32611"] is False
    assert not rep["passed"]


def test_footprint_policy(tmp_path):
    fp = np.zeros(SHAPE, bool)
    fp[50:60, 50:60] = True
    p = _zeros()
    p[55, 55] = 0.4
    out = tmp_path / "fp.tif"
    r = sub.write_submission(p, out, name="gems74-fp-check", note="footprint test", footprint=fp, nodata="nan")
    assert r["validator"]["passed"]
    assert r["validator"]["checks"]["outside_footprint_nan_or_zero"] is True
