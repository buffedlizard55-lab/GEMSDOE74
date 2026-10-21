"""Submission GeoTIFF validator and writer for the DOE GEMS Prize.

Requirements (competition problem page, "Submission format"):
  * projected CRS EPSG:32611 (UTM 11N)
  * 100 m resolution, same bounds as the training data
  * single band, float32
  * values in [0, 1]; data outside the bounds is null or NaN

Grid constants below were read from GEMSDOE32's own audit receipts
(docs/downloads/*-audit.json in buffedlizard55-lab/GEMSDOE32, shape 3730x3292,
transform 100,0,243350,0,-100,4508550). They are NOT yet confirmed against the
official training_features.tif header, which this environment cannot download.
Confirm them with `scripts/validate_submission.py --template <official tif>`
before any submission.

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
NOTE_MAX_CHARS = 200  # the GEMSDOE32 site reports this limit; not stated on the organiser form (see irregularities)
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


def validate_submission(path, footprint=None) -> dict:
    """Validate a candidate submission GeoTIFF.

    footprint: optional 2-D bool array (True = inside the GeoDAWN footprint, same grid).
               When given, cells inside must be finite and cells outside must be NaN or 0.
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
        checks["shape_3730x3292"] = (ds.height, ds.width) == EXPECTED_SHAPE
        checks["transform_100m_origin"] = _transform_matches(ds.transform)
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
        checks["inside_footprint_all_finite"] = bool(np.isfinite(inside).all())
        checks["outside_footprint_nan_or_zero"] = bool(np.all(np.isnan(outside) | (outside == 0.0)))
        report["n_outside_nonzero_finite"] = int(np.sum(np.isfinite(outside) & (outside != 0.0)))

    report["checks"] = checks
    report["passed"] = all(checks.values())
    return report


def write_submission(prob, out_path, name: str, note: str, footprint=None, nodata: str = "none") -> dict:
    """Write a validated single-band float32 GeoTIFF and return its receipt.

    prob:      2-D float array on the competition grid, values must lie in [0, 1].
    footprint: optional bool array; outside cells are written as 0.0 (nodata="none")
               or NaN (nodata="nan"). If None, every cell is written as given.
    name:      unique submission name, [A-Za-z0-9._-], 3-80 chars.
    note:      comment for the organiser form; at most NOTE_MAX_CHARS characters.
    """
    import rasterio
    from rasterio.transform import Affine

    if not NAME_RE.match(name):
        raise ValueError(f"invalid submission name {name!r}")
    if len(note) > NOTE_MAX_CHARS:
        raise ValueError(f"note is {len(note)} chars; limit is {NOTE_MAX_CHARS}")
    if nodata not in ("none", "nan"):
        raise ValueError("nodata must be 'none' or 'nan'")

    arr = np.asarray(prob, dtype=np.float32)
    if arr.shape != EXPECTED_SHAPE:
        raise ValueError(f"expected shape {EXPECTED_SHAPE}, got {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("prob must be finite inside the grid")
    if arr.min() < 0.0 or arr.max() > 1.0:
        raise ValueError(f"prob must lie in [0, 1]; got [{arr.min()}, {arr.max()}]")
    if footprint is not None:
        fp = np.asarray(footprint).astype(bool)
        if fp.shape != arr.shape:
            raise ValueError("footprint shape mismatch")
        fill = np.float32(np.nan) if nodata == "nan" else np.float32(0.0)
        arr = np.where(fp, arr, fill).astype(np.float32)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "height": EXPECTED_SHAPE[0],
        "width": EXPECTED_SHAPE[1],
        "crs": EXPECTED_CRS,
        "transform": Affine(*EXPECTED_TRANSFORM),
        "nodata": float("nan") if nodata == "nan" else None,
        "compress": "deflate",
        "tiled": False,
    }
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(arr, 1)
        dst.update_tags(submission_name=name, submission_note=note)

    report = validate_submission(out_path, footprint=footprint)
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
