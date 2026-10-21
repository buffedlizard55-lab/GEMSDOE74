#!/usr/bin/env python3
"""Local GeoTIFF checks; a pass is not an organizer receipt.

When an official sample-submission template is available, validate geometry and
inside/outside values against its finite footprint. Without it, report all footprint-
dependent checks as unavailable and only check pinned metadata/value invariants.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

PINNED_CRS = "EPSG:32611"
PINNED_SHAPE = (3730, 3292)
PINNED_TRANSFORM = Affine(100, 0, 243350, 0, -100, 4508550)
SENTINEL = np.float32(-3.4028234663852886e38)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="docs/downloads/gemsdoe74-h74-1-basement-step-35641-20261021T000000Z-100b4b19-zeros.tif")
    parser.add_argument("--template", default="data/sample_submission.tif")
    parser.add_argument("--labels", default="data/labels.tif")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.is_file():
        parser.error(f"GeoTIFF not found: {path}")

    checks = {}
    with rasterio.open(path) as src:
        arr = src.read(1)
        checks["single_band"] = src.count == 1
        checks["dtype_float32"] = src.dtypes[0] == "float32"
        checks["pinned_shape"] = src.shape == PINNED_SHAPE
        checks["pinned_crs"] = src.crs is not None and src.crs.to_string() == PINNED_CRS
        checks["pinned_transform"] = src.transform == PINNED_TRANSFORM
        checks["no_infinity"] = not bool(np.isinf(arr).any())
        checks["no_negative_float32_sentinel"] = not bool(np.any(arr == SENTINEL))
        finite = np.isfinite(arr)
        finite_values = arr[finite]
        checks["has_finite_predictions"] = bool(finite_values.size > 0)
        checks["finite_values_in_0_1"] = bool(finite_values.size > 0 and (finite_values >= 0).all() and (finite_values <= 1).all())
        metadata = {
            "shape": list(src.shape),
            "crs": src.crs.to_string() if src.crs else None,
            "transform": list(src.transform)[:6],
            "dtype": src.dtypes[0],
            "nodata": None if src.nodata is None else ("nan" if np.isnan(src.nodata) else float(src.nodata)),
            "minimum_finite": float(finite_values.min()) if finite_values.size else None,
            "maximum_finite": float(finite_values.max()) if finite_values.size else None,
            "finite_cells": int(finite.sum()),
            "stored_cells": int(arr.size),
            "positive_cells": int(np.count_nonzero(arr > 0)),
        }

    template_path = Path(args.template)
    if template_path.is_file():
        with rasterio.open(template_path) as tpl, rasterio.open(path) as sub:
            template = tpl.read(1)
            candidate = sub.read(1)
            footprint = np.isfinite(template)
            geom_match = (
                tpl.count == 1 and sub.width == tpl.width and sub.height == tpl.height and
                sub.crs == tpl.crs and sub.transform == tpl.transform
            )
            checks["matches_official_template_geometry"] = bool(geom_match)
            if geom_match:
                inside = candidate[footprint]
                outside = candidate[~footprint]
                checks["inside_footprint_finite_in_0_1"] = bool(
                    np.isfinite(inside).all() and (inside >= 0).all() and (inside <= 1).all()
                )
                checks["outside_footprint_null_or_nan"] = bool(np.isnan(outside).all())
                checks["nodata_none_or_nan"] = bool(
                    sub.nodata is None or (isinstance(sub.nodata, float) and np.isnan(sub.nodata))
                )
                metadata["official_template_valid_cells"] = int(footprint.sum())
                metadata["outside_cells"] = int((~footprint).sum())
            else:
                checks["inside_footprint_finite_in_0_1"] = None
                checks["outside_footprint_null_or_nan"] = None
                checks["nodata_none_or_nan"] = None
                metadata["official_template_valid_cells"] = None
                metadata["outside_cells"] = None
    else:
        checks["matches_official_template_geometry"] = None
        checks["inside_footprint_finite_in_0_1"] = None
        checks["outside_footprint_null_or_nan"] = None
        checks["nodata_none_or_nan"] = None
        metadata["official_template_valid_cells"] = None
        metadata["outside_cells"] = None

    labels_path = Path(args.labels)
    if labels_path.is_file():
        with rasterio.open(labels_path) as lab, rasterio.open(path) as sub:
            labels_match = (
                lab.count == 1 and lab.width == sub.width and lab.height == sub.height and
                lab.crs == sub.crs and lab.transform == sub.transform
            )
            checks["labels_geometry_matches_submission"] = bool(labels_match)
            if labels_match:
                labels = lab.read(1) > 0
                metadata["positive_cells_overlapping_labels"] = int(
                    np.count_nonzero((sub.read(1) > 0) & labels)
                )
            else:
                metadata["positive_cells_overlapping_labels"] = None
    else:
        checks["labels_geometry_matches_submission"] = None
        metadata["positive_cells_overlapping_labels"] = None

    failed = [name for name, result in checks.items() if result is False]
    unavailable = [name for name, result in checks.items() if result is None]
    result = {
        "file": str(path),
        "local_checks_passed": not failed,
        "checks": checks,
        "metadata": metadata,
        "failed_checks": failed,
        "unavailable_checks": unavailable,
        "interpretation": "Local file checks only. Missing official template/labels leave footprint/catalogue checks unavailable; no scientific validity or organizer acceptance is implied.",
    }
    print(json.dumps(result, indent=2))
    if failed:
        print("LOCAL CHECKS FAILED.")
        return 1
    if unavailable:
        print("LOCAL CHECKS PASS; OFFICIAL TEMPLATE/FOOTPRINT AND/OR LABEL CHECKS UNAVAILABLE.")
    else:
        print("LOCAL FORMAT AND SUPPLIED-INPUT CHECKS PASS; NOT AN ORGANIZER RECEIPT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
