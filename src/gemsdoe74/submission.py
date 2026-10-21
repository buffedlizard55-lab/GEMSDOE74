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


def validate_tif(path: pathlib.Path, template_path: pathlib.Path, strict_portal_safe: bool = True):
    """Validate bytes against the provided sample-submission template.

    Strict mode requires every stored value to be finite and within [0,1], with no
    nodata tag (recommended for avoiding portal range errors). Non-strict mode checks
    finite/range values inside the template footprint and permits only zero/NaN outside.
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
        if strict_portal_safe:
            checks.append({"name": "all_stored_values_finite", "passed": bool(finite.all()), "detail": f"{int(finite.sum())}/{arr.size}"})
            checks.append({"name": "all_stored_values_in_0_1", "passed": bool(in_range.all()), "detail": f"min={float(np.nanmin(arr))}, max={float(np.nanmax(arr))}"})
            checks.append({"name": "nodata_unset", "passed": ds.nodata is None, "detail": f"nodata={ds.nodata}"})
        else:
            inside_ok = bool(finite[footprint].all() and in_range[footprint].all())
            outside_values = arr[~footprint]
            outside_ok = bool(np.isfinite(outside_values).all() and ((outside_values == 0).all())) or bool(np.isnan(outside_values).all())
            checks.append({"name": "inside_footprint_finite_in_range", "passed": inside_ok, "detail": f"footprint cells={int(footprint.sum())}"})
            checks.append({"name": "outside_zero_or_nan", "passed": outside_ok, "detail": "outside cells must all be zero or all NaN"})
            checks.append({"name": "no_infinity", "passed": not bool(np.isinf(arr).any()), "detail": "no infinite values"})
            nodata_ok = ds.nodata is None or (isinstance(ds.nodata, float) and np.isnan(ds.nodata))
            checks.append({"name": "nodata_none_or_nan", "passed": nodata_ok, "detail": f"nodata={ds.nodata}"})

    return {"passed": all(c["passed"] for c in checks), "checks": checks}


def write_submission_geotiff(
    predictions: np.ndarray,
    template_path: pathlib.Path,
    out_path: pathlib.Path,
    outside_mode: str = "zeros",
    note: str | None = None,
):
    """Write a prediction grid using the official template's exact geometry.

    `outside_mode` is `zeros` (strict all-finite output) or `nan` (NaN outside
    template footprint). The official template is required; no synthetic fallback.
    """
    if outside_mode not in {"zeros", "nan"}:
        raise ValueError("outside_mode must be 'zeros' or 'nan'")
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
    if outside_mode == "zeros":
        output = np.where(footprint, preds, 0.0).astype(np.float32)
        profile["nodata"] = None
        strict = True
    else:
        output = np.where(footprint, preds, np.nan).astype(np.float32)
        profile["nodata"] = float("nan")
        strict = False

    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(output, 1)
    audit = validate_tif(out_path, template_path, strict_portal_safe=strict)
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
        "nodata": None if outside_mode == "zeros" else "nan",
        "positive_pixels_inside_template_footprint": int(np.count_nonzero(output[footprint] > 0)),
        "template_footprint_cells": int(footprint.sum()),
        "checks": audit["checks"],
        "local_format_validation_passed": audit["passed"],
        "scientific_validation": "not implied by file-format validation",
        "note": note,
    }
    out_path.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
