#!/usr/bin/env python3
"""Independent, fail-closed GeoTIFF format validator.

Requires an explicit candidate path and the official sample-submission raster.
It validates the written file after reopening it, derives the footprint from the
sample grid, and compares CRS, shape, and affine transform exactly. This is a
format receipt only: a passing file still needs scientific holdout, leakage,
registry, provenance, and organizer-receipt gates before it is eligible for a
competition slot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = ROOT / "data" / "sample_submission.tif"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _footprint_from_sample(sample: np.ndarray, nodata: float | int | None) -> np.ndarray:
    footprint = np.isfinite(sample)
    if nodata is not None:
        try:
            if math.isfinite(float(nodata)):
                footprint &= sample != nodata
        except (TypeError, ValueError):
            pass
    return footprint


def _json_safe_nodata(value: float | int | None) -> float | str | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    return numeric if math.isfinite(numeric) else str(numeric)


def validate_submission(candidate_path: Path, sample_path: Path) -> dict[str, Any]:
    """Return a machine-readable format report; do not modify either raster."""
    candidate_path = Path(candidate_path).resolve()
    sample_path = Path(sample_path).resolve()
    if not candidate_path.is_file():
        raise FileNotFoundError(f"candidate raster is missing: {candidate_path}")
    if not sample_path.is_file():
        raise FileNotFoundError(f"official sample-submission raster is missing: {sample_path}")

    with rasterio.open(sample_path) as sample_ds:
        if sample_ds.count < 1:
            raise ValueError("sample-submission raster has no bands")
        sample = sample_ds.read(1)
        reference = {
            "height": sample_ds.height,
            "width": sample_ds.width,
            "count": sample_ds.count,
            "crs": sample_ds.crs,
            "transform": sample_ds.transform,
            "nodata": sample_ds.nodata,
        }
        footprint = _footprint_from_sample(sample, sample_ds.nodata)
        if not footprint.any():
            raise ValueError("sample-submission raster has no finite, non-nodata footprint pixels")
        if sample_ds.crs is None:
            raise ValueError("sample-submission raster has no CRS; cannot establish the official grid")

    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}
    with rasterio.open(candidate_path) as candidate_ds:
        checks["single_band"] = candidate_ds.count == 1
        checks["dtype_float32"] = candidate_ds.count == 1 and candidate_ds.dtypes[0] == "float32"
        checks["shape_match"] = (candidate_ds.height, candidate_ds.width) == (reference["height"], reference["width"])
        checks["crs_match"] = reference["crs"] is not None and candidate_ds.crs == reference["crs"]
        checks["transform_match"] = candidate_ds.transform == reference["transform"]
        checks["no_nodata_value"] = candidate_ds.nodata is None
        checks["reread_from_disk"] = True
        if candidate_ds.count == 1:
            values = candidate_ds.read(1)
            shape_matches = values.shape == footprint.shape
            if shape_matches:
                inside = values[footprint]
                checks["no_nan_inside_footprint"] = bool(np.isfinite(inside).all())
                checks["all_values_in_allowed_range"] = bool(
                    np.isfinite(values).all() and (values >= 0).all() and (values <= 1).all()
                )
                finite_inside = inside[np.isfinite(inside)]
                finite_values = values[np.isfinite(values)]
                details["footprint_pixels"] = int(footprint.sum())
                details["inside_min"] = float(finite_inside.min()) if finite_inside.size else None
                details["inside_max"] = float(finite_inside.max()) if finite_inside.size else None
                details["full_grid_min"] = float(finite_values.min()) if finite_values.size else None
                details["full_grid_max"] = float(finite_values.max()) if finite_values.size else None
                details["finite_pixels"] = int(finite_values.size)
                details["nodata"] = _json_safe_nodata(candidate_ds.nodata)
            else:
                checks["no_nan_inside_footprint"] = False
                checks["all_values_in_allowed_range"] = False
        else:
            checks["no_nan_inside_footprint"] = False
            checks["all_values_in_allowed_range"] = False

    checks["crs_match"] = bool(checks["crs_match"])
    passed = all(checks.values())
    return {
        "schema_version": "gemsdoe74-format-validation-v1",
        "format_scope_only": True,
        "submission_eligible": False,
        "passed": bool(passed),
        "candidate_path": str(candidate_path),
        "candidate_sha256": sha256_file(candidate_path),
        "sample_path": str(sample_path),
        "sample_grid": {
            "height": reference["height"],
            "width": reference["width"],
            "crs": reference["crs"].to_string() if reference["crs"] else None,
            "transform": list(reference["transform"]),
            "sample_nodata": _json_safe_nodata(reference["nodata"]),
        },
        **checks,
        "checks": checks,
        "details": details,
        "validated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "A format pass is not an approval to submit or download.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path, help="Candidate GeoTIFF to validate after writing.")
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE, help="Official sample-submission GeoTIFF defining the grid.")
    parser.add_argument("--receipt", type=Path, help="Optional path for a JSON format receipt.")
    args = parser.parse_args()
    try:
        report = validate_submission(args.candidate, args.sample)
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        print(json.dumps({"passed": False, "format_scope_only": True, "submission_eligible": False, "error": str(exc)}, indent=2))
        return 2
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        receipt = args.receipt if args.receipt.is_absolute() else ROOT / args.receipt
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
