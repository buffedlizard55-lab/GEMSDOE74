"""Writer tests using a tiny test template; not competition data."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from gemsdoe74.submission import validate_tif, write_submission_geotiff


def make_template(path):
    arr = np.array([[0, 0, np.nan, np.nan], [0, 0, np.nan, np.nan], [np.nan, np.nan, np.nan, np.nan]], dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=4,
        height=3,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=from_origin(500000, 4500000, 100, 100),
        nodata=np.nan,
    ) as ds:
        ds.write(arr, 1)
    return arr


def test_writer_requires_a_real_template(tmp_path):
    with pytest.raises(FileNotFoundError, match="official sample_submission"):
        write_submission_geotiff(np.zeros((3, 4), np.float32), None, tmp_path / "no-template.tif")


def test_writer_rejects_zero_filled_outside_mode(tmp_path):
    template = tmp_path / "sample.tif"
    footprint = make_template(template)
    with pytest.raises(ValueError, match="zero-filled outside bounds"):
        write_submission_geotiff(np.zeros_like(footprint), template, tmp_path / "candidate.tif", outside_mode="zeros")


def test_validator_rejects_zero_values_outside_official_bounds(tmp_path):
    template = tmp_path / "sample.tif"
    footprint = make_template(template)
    with rasterio.open(template) as src:
        profile = src.profile.copy()
    with rasterio.open(tmp_path / "bad-zero-outside.tif", "w", **profile) as dst:
        dst.write(np.zeros_like(footprint, dtype=np.float32), 1)
    report = validate_tif(tmp_path / "bad-zero-outside.tif", template)
    assert report["passed"] is False
    assert next(c for c in report["checks"] if c["name"] == "outside_footprint_nan")["passed"] is False


def test_writer_nan_mode_keeps_nan_only_outside(tmp_path):
    template = tmp_path / "sample.tif"
    footprint = make_template(template)
    out = tmp_path / "candidate-nan.tif"

    receipt = write_submission_geotiff(np.zeros_like(footprint), template, out, outside_mode="nan", note="format test only")

    assert receipt["local_format_validation_passed"] is True
    report = validate_tif(out, template)
    assert report["passed"] is True
    with rasterio.open(out) as ds:
        actual = ds.read(1)
        inside = np.isfinite(footprint)
        assert np.isfinite(actual[inside]).all()
        assert np.isnan(actual[~inside]).all()
        assert ds.nodata is not None and np.isnan(ds.nodata)
