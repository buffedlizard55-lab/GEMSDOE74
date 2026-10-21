"""Submission GeoTIFF validator and writer for the DOE GEMS Prize.

Requirements (competition problem page, "Submission format"):
  * projected CRS EPSG:32611 (UTM 11N)
  * 100 m resolution, same bounds as the training data
  * single band, float32
  * values in [0, 1]; data outside the bounds is null or NaN

    Grid constants below were copied from an owner-side audit in a sibling repository
(shape 3730x3292, transform 100,0,243350,0,-100,4508550). They are NOT organizer-
authenticated and have not been confirmed against the official training_features.tif.
The authorized sample-submission template is mandatory for release checks.

Known failure mode (organizer message "Predicted values must be in range [0, 1]"):
a nodata sentinel such as -3.4028234663852886e+38 that lies inside the footprint.
The validator rejects any finite value outside [0, 1] and any nodata tag that is
not NaN/None.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np

EXPECTED_CRS = "EPSG:32611"
EXPECTED_SHAPE = (3730, 3292)  # (rows, cols)
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
NOTE_MAX_CHARS = 140  # project protocol; not a claimed organizer limit
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$")


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _transform_matches(t, expected=EXPECTED_TRANSFORM, tol=1e-6):
    vals = tuple(t)[:6]
    return all(math.isclose(a, b, abs_tol=tol) for a, b in zip(vals, expected))


def validate_submission(path, footprint=None, template_path=None) -> dict:
    """Validate a candidate submission GeoTIFF.

    footprint: optional 2-D bool array (True = inside the template footprint, same grid).
               When given, cells inside must be finite and cells outside must be NaN.
               Returns a dict with per-check booleans, counts and an overall `passed` flag.
    """
    import rasterio  # imported lazily so the metric works without GDAL

    path = Path(path)
    checks: dict[str, bool] = {}
    report: dict = {"file": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size}

    with rasterio.open(path) as ds:
        checks["single_band"] = ds.count == 1
        checks["dtype_float32"] = ds.dtypes[0] == "float32"
        checks["crs_epsg_32611"] = ds.crs is not None and ds.crs.to_string() == EXPECTED_CRS
        if template_path is None:
            checks["pinned_shape"] = (ds.height, ds.width) == EXPECTED_SHAPE
            checks["pinned_transform"] = _transform_matches(ds.transform)
        else:
            template_path = Path(template_path)
            if not template_path.is_file():
                raise FileNotFoundError(f"official sample-submission template not found: {template_path}")
            with rasterio.open(template_path) as template:
                checks["official_template_geometry_match"] = (
                    ds.width == template.width and ds.height == template.height and
                    ds.crs == template.crs and ds.transform == template.transform
                )
                template_footprint = np.isfinite(template.read(1))
                if footprint is not None and not np.array_equal(np.asarray(footprint, dtype=bool), template_footprint):
                    checks["provided_footprint_matches_template"] = False
                else:
                    footprint = template_footprint
                    checks["provided_footprint_matches_template"] = True
        nodata = ds.nodata
        checks["nodata_none_or_nan"] = nodata is None or (isinstance(nodata, float) and math.isnan(nodata))
        report["nodata"] = None if nodata is None else repr(nodata)
        arr = ds.read(1).astype("float64")

    finite = np.isfinite(arr)
    report["n_cells"] = int(arr.size)
    report["n_nan"] = int(np.isnan(arr).sum())
    report["n_inf"] = int(np.isinf(arr).sum())
    report["n_positive"] = int((arr[finite] > 0).sum())
    checks["no_inf"] = report["n_inf"] == 0
    in_range = (arr >= 0.0) & (arr <= 1.0)
    report["n_finite_outside_0_1"] = int((finite & ~in_range).sum())
    checks["finite_values_in_0_1"] = report["n_finite_outside_0_1"] == 0
    if finite.any():
        report["min_finite"] = float(arr[finite].min())
        report["max_finite"] = float(arr[finite].max())
    checks["no_sentinel_-3.4e38"] = not np.any(arr < -1e30)

    if footprint is not None:
        fp = np.asarray(footprint).astype(bool)
        if fp.shape != arr.shape:
            raise ValueError("footprint shape does not match the submission grid")
        inside = arr[fp]
        outside = arr[~fp]
        checks["inside_footprint_finite_in_0_1"] = bool(
            np.isfinite(inside).all() and (inside >= 0.0).all() and (inside <= 1.0).all()
        )
        checks["outside_footprint_nan"] = bool(np.isnan(outside).all())
        report["n_outside_finite_non_nan"] = int(np.sum(np.isfinite(outside)))

    report["checks"] = checks
    report["passed"] = all(checks.values())
    return report

def write_submission(
    prob, out_path, name: str, note: str, *, template_path=None, footprint=None
) -> dict:
    """Write against the supplied official sample-submission template.

    When a finite-footprint mask is supplied or read from the template, cells outside
    that footprint are always NaN, per the organizer's documented submission format.
    This local writer still cannot establish scientific validity or acceptance.
    """
    import rasterio

    if not NAME_RE.match(name):
        raise ValueError(f"invalid submission name {name!r}")
    if len(note) > NOTE_MAX_CHARS:
        raise ValueError(f"note is {len(note)} chars; limit is {NOTE_MAX_CHARS}")
    if template_path is None or not Path(template_path).is_file():
        raise FileNotFoundError("official sample_submission.tif is required; no pinned-grid fallback")

    template_path = Path(template_path)
    with rasterio.open(template_path) as template:
        if template.count != 1 or template.crs is None:
            raise ValueError("official sample_submission.tif must be single-band and have a CRS")
        template_arr = template.read(1)
        template_footprint = np.isfinite(template_arr)
        if footprint is not None and not np.array_equal(np.asarray(footprint, dtype=bool), template_footprint):
            raise ValueError("provided footprint must exactly match the official template's finite cells")
        fp = template_footprint
        arr = np.asarray(prob, dtype=np.float32)
        if arr.shape != template_arr.shape:
            raise ValueError(f"probability shape {arr.shape} does not match official template {template_arr.shape}")
        if not np.isfinite(arr).all():
            raise ValueError("probabilities must be finite before applying the outside mask")
        if (arr < 0).any() or (arr > 1).any():
            raise ValueError("probabilities must lie in [0,1]")
        profile = dict(template.profile)
        profile.update(dtype="float32", count=1, nodata=float("nan"), compress="deflate")

    output = np.where(fp, arr, np.nan).astype(np.float32)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(output, 1)
        dst.update_tags(submission_name=name, submission_note=note)

    report = validate_submission(out_path, footprint=fp, template_path=template_path)
    receipt = {
        "submission_name": name,
        "submission_note": note,
        "note_chars": len(note),
        "file": out_path.name,
        "sha256": report["sha256"],
        "bytes": report["bytes"],
        "n_positive": report["n_positive"],
        "validator": report,
    }
    receipt_path = out_path.with_suffix(".receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    if not report["passed"]:
        raise RuntimeError(f"written file failed validation: {report['checks']}")
    return receipt
