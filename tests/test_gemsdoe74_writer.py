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


def test_writer_zeros_mode_uses_template_and_reopens(tmp_path):
    template = tmp_path / "sample.tif"
    footprint = make_template(template)
    prediction = np.zeros_like(footprint)
    prediction[0, 1] = 1
    out = tmp_path / "candidate.tif"

    receipt = write_submission_geotiff(prediction, template, out, outside_mode="zeros", note="format test only")

    assert receipt["local_format_validation_passed"] is True
    assert receipt["positive_pixels_inside_template_footprint"] == 1
    report = validate_tif(out, template)
    assert report["passed"] is True
    with rasterio.open(out) as ds:
        actual = ds.read(1)
        assert ds.crs.to_epsg() == 32611
        assert ds.transform == from_origin(500000, 4500000, 100, 100)
        assert np.isfinite(actual).all()
        assert (actual >= 0).all() and (actual <= 1).all()


def test_writer_nan_mode_keeps_nan_only_outside(tmp_path):
    template = tmp_path / "sample.tif"
    footprint = make_template(template)
    out = tmp_path / "candidate-nan.tif"

    receipt = write_submission_geotiff(np.zeros_like(footprint), template, out, outside_mode="nan", note="format test only")

    assert receipt["local_format_validation_passed"] is True
    report = validate_tif(out, template, strict_portal_safe=False)
    assert report["passed"] is True
