"""Tests for the template-driven submission writer; all rasters are synthetic fixtures."""
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gems74 import submission as sub

SHAPE = (4, 5)
TRANSFORM = Affine(100, 0, 243350, 0, -100, 4508550)


def _zeros():
    return np.zeros(SHAPE, np.float32)


def _template(path, footprint=None, crs=sub.EXPECTED_CRS):
    if footprint is None:
        footprint = np.ones(SHAPE, dtype=bool)
    values = np.where(footprint, 0.0, np.nan).astype(np.float32)
    with rasterio.open(
        path, "w", driver="GTiff", dtype="float32", count=1,
        height=SHAPE[0], width=SHAPE[1], crs=crs, transform=TRANSFORM,
        nodata=np.nan, compress="deflate",
    ) as dst:
        dst.write(values, 1)
    return np.asarray(footprint, dtype=bool)


def test_writer_requires_official_template(tmp_path):
    with pytest.raises(FileNotFoundError, match="official sample_submission"):
        sub.write_submission(_zeros(), tmp_path / "missing.tif", name="gems74-toy", note="test only")
    assert not (tmp_path / "missing.tif").exists()


def test_writer_round_trip_passes_validator(tmp_path):
    template = tmp_path / "sample.tif"
    _template(template)
    p = _zeros()
    p[1:4, 2] = 0.9
    out = tmp_path / "toy-check.tif"
    r = sub.write_submission(
        p, out, name="gems74-toy-check", note="format test only, not a prediction",
        template_path=template,
    )
    assert r["validator"]["passed"]
    assert r["n_positive"] == 3
    assert r["sha256"] == sub.sha256_file(out)


def test_writer_rejects_values_outside_unit_interval(tmp_path):
    template = tmp_path / "sample.tif"
    _template(template)
    p = _zeros()
    p[0, 0] = 1.5
    with pytest.raises(ValueError):
        sub.write_submission(p, tmp_path / "bad.tif", name="gems74-bad", note="x", template_path=template)


def test_writer_rejects_long_note_and_bad_name(tmp_path):
    template = tmp_path / "sample.tif"
    _template(template)
    with pytest.raises(ValueError):
        sub.write_submission(_zeros(), tmp_path / "a.tif", name="gems74-a", note="x" * 201, template_path=template)
    with pytest.raises(ValueError):
        sub.write_submission(_zeros(), tmp_path / "b.tif", name="bad name!", note="x", template_path=template)


def test_validator_flags_negative_sentinel_inside_footprint(tmp_path):
    template = tmp_path / "sample.tif"
    _template(template)
    arr = _zeros()
    arr[1, 1] = -3.4028234663852886e38
    path = tmp_path / "sentinel.tif"
    with rasterio.open(
        path, "w", driver="GTiff", dtype="float32", count=1, height=SHAPE[0], width=SHAPE[1],
        crs=sub.EXPECTED_CRS, transform=TRANSFORM, nodata=np.nan,
    ) as dst:
        dst.write(arr, 1)
    rep = sub.validate_submission(path, template_path=template)
    assert not rep["passed"]
    assert rep["checks"]["finite_values_in_0_1"] is False
    assert rep["checks"]["no_sentinel_-3.4e38"] is False


def test_validator_flags_wrong_crs(tmp_path):
    template = tmp_path / "sample.tif"
    _template(template)
    path = tmp_path / "wrongcrs.tif"
    with rasterio.open(
        path, "w", driver="GTiff", dtype="float32", count=1, height=SHAPE[0], width=SHAPE[1],
        crs="EPSG:4326", transform=TRANSFORM, nodata=np.nan,
    ) as dst:
        dst.write(_zeros(), 1)
    rep = sub.validate_submission(path, template_path=template)
    assert rep["checks"]["crs_epsg_32611"] is False
    assert rep["checks"]["official_template_geometry_match"] is False
    assert not rep["passed"]


def test_footprint_policy_writes_only_nan_outside(tmp_path):
    fp = np.zeros(SHAPE, bool)
    fp[1:3, 1:4] = True
    template = tmp_path / "sample.tif"
    _template(template, fp)
    p = _zeros()
    p[2, 2] = 0.4
    out = tmp_path / "fp.tif"
    r = sub.write_submission(
        p, out, name="gems74-fp-check", note="footprint test",
        template_path=template, footprint=fp,
    )
    assert r["validator"]["passed"]
    assert r["validator"]["checks"]["outside_footprint_nan"] is True
    with rasterio.open(out) as ds:
        actual = ds.read(1)
    assert np.isfinite(actual[fp]).all()
    assert np.isnan(actual[~fp]).all()


def test_validator_rejects_zero_filled_outside(tmp_path):
    fp = np.zeros(SHAPE, bool)
    fp[1:3, 1:4] = True
    template = tmp_path / "sample.tif"
    _template(template, fp)
    path = tmp_path / "zero-outside.tif"
    with rasterio.open(
        path, "w", driver="GTiff", dtype="float32", count=1, height=SHAPE[0], width=SHAPE[1],
        crs=sub.EXPECTED_CRS, transform=TRANSFORM, nodata=None,
    ) as dst:
        dst.write(np.zeros(SHAPE, dtype=np.float32), 1)
    report = sub.validate_submission(path, template_path=template)
    assert report["checks"]["outside_footprint_nan"] is False
    assert not report["passed"]
