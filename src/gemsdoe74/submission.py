"""GeoTIFF writer and byte-level validator.

A real sample-submission GeoTIFF is mandatory. No synthetic footprint or pinned-grid
fallback is allowed in this submission path. A local pass checks format only; it does
not establish scientific validity or organizer acceptance.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
from datetime import datetime, timezone

import numpy as np
import rasterio

SENTINEL = np.float32(-3.4028234663852886e38)


def sha256_of(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_tif(path: pathlib.Path, template_path: pathlib.Path):
    """Validate output against the official sample-submission footprint.

    Following the organizer's submission-format guidance, require finite probabilities
    in [0,1] inside the valid footprint and NaN outside. No synthetic footprint or
    whole-array finite assumption is used.
    """
    path = pathlib.Path(path)
    template_path = pathlib.Path(template_path) if template_path is not None else None
    if template_path is None or not template_path.is_file():
        raise FileNotFoundError("official sample_submission.tif is required; no synthetic footprint fallback")

    checks = []
    with rasterio.open(template_path) as template, rasterio.open(path) as ds:
        template_arr = template.read(1)
        arr = ds.read(1)
        footprint = np.isfinite(template_arr)
        geom_match = (
            ds.width == template.width and ds.height == template.height and
            ds.crs == template.crs and ds.transform == template.transform
        )
        checks.extend([
            {"name": "template_geometry_match", "passed": bool(geom_match), "detail": "CRS, shape, and affine transform"},
            {"name": "single_band", "passed": ds.count == 1, "detail": f"count={ds.count}"},
            {"name": "float32", "passed": ds.dtypes[0] == "float32", "detail": ds.dtypes[0]},
            {"name": "no_sentinel", "passed": not bool(np.any(arr == SENTINEL)), "detail": "negative float32 nodata sentinel absent"},
        ])
        finite = np.isfinite(arr)
        in_range = finite & (arr >= 0.0) & (arr <= 1.0)
        inside_ok = bool(finite[footprint].all() and in_range[footprint].all())
        outside_values = arr[~footprint]
        outside_ok = bool(np.isnan(outside_values).all())
        no_infinity = not bool(np.isinf(arr).any())
        nodata_ok = ds.nodata is None or (isinstance(ds.nodata, float) and np.isnan(ds.nodata))
        checks.extend([
            {"name": "inside_footprint_finite_in_range", "passed": inside_ok, "detail": f"valid footprint cells={int(footprint.sum())}"},
            {"name": "outside_footprint_nan", "passed": outside_ok, "detail": "all cells outside template bounds must be NaN"},
            {"name": "no_infinity", "passed": no_infinity, "detail": "no infinite values anywhere"},
            {"name": "nodata_none_or_nan", "passed": nodata_ok, "detail": f"nodata={ds.nodata}"},
        ])

    return {"passed": all(c["passed"] for c in checks), "checks": checks}


def write_submission_geotiff(
    predictions: np.ndarray,
    template_path: pathlib.Path,
    out_path: pathlib.Path,
    outside_mode: str = "nan",
    note: str | None = None,
):
    """Write a prediction grid using the official template's exact geometry.

    The official template is required; cells outside its valid footprint are written
    as NaN per the organizer's documented submission format.
    """
    if outside_mode != "nan":
        raise ValueError("outside_mode must be 'nan'; zero-filled outside bounds are not the documented submission format")
    template_path = pathlib.Path(template_path) if template_path is not None else None
    if template_path is None or not template_path.is_file():
        raise FileNotFoundError("official sample_submission.tif is required")

    with rasterio.open(template_path) as template:
        template_arr = template.read(1)
        footprint = np.isfinite(template_arr)
        if template.count != 1:
            raise ValueError("sample_submission.tif must be single-band")
        if template.crs is None:
            raise ValueError("sample_submission.tif has no CRS")
        if np.asarray(predictions).shape != template_arr.shape:
            raise ValueError(f"prediction shape {np.asarray(predictions).shape} != template shape {template_arr.shape}")
        profile = dict(template.profile)
        profile.update(dtype="float32", count=1, compress="deflate")
        template_crs = template.crs.to_string()
        template_transform = list(template.transform)[:6]

    preds = np.asarray(predictions, dtype=np.float32)
    if not np.isfinite(preds).all():
        raise ValueError("predictions must be finite before applying the outside mask")
    if (preds < 0).any() or (preds > 1).any():
        raise ValueError(f"predictions outside [0,1]: [{float(preds.min())}, {float(preds.max())}]")

    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    output = np.where(footprint, preds, np.nan).astype(np.float32)
    profile["nodata"] = float("nan")

    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(output, 1)
    audit = validate_tif(out_path, template_path)
    if not audit["passed"]:
        raise ValueError(f"Validation failed after reopening written bytes: {audit}")
    audit["checks"] = [{**check, "passed": bool(check["passed"])} for check in audit["checks"]]
    audit["passed"] = bool(audit["passed"])

    note = note or "GEMSDOE74 experimental candidate; review before submission"
    if len(note) > 140:
        raise ValueError(f"submission note exceeds 140 characters ({len(note)})")
    manifest = {
        "file_name": out_path.name,
        "sha256": sha256_of(out_path),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "outside_mode": outside_mode,
        "crs": template_crs,
        "shape": list(output.shape),
        "transform": template_transform,
        "dtype": "float32",
        "nodata": "nan",
        "positive_pixels_inside_template_footprint": int(np.count_nonzero(output[footprint] > 0)),
        "template_footprint_cells": int(footprint.sum()),
        "checks": audit["checks"],
        "local_format_validation_passed": audit["passed"],
        "scientific_validation": "not implied by file-format validation",
        "note": note,
    }
    out_path.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
