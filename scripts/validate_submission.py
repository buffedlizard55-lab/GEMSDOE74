#!/usr/bin/env python3
"""Local GeoTIFF format validator; a pass is not an organizer receipt.

The optional official template enables exact geometry comparison. Without it, the
validator checks historical pinned constants only and reports template verification
as unavailable. `--labels` enables a local positive-cell/catalogue count only.
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
        crs_ok = src.crs is not None and src.crs.to_string() == PINNED_CRS
        checks["single_band"] = src.count == 1
        checks["dtype_float32"] = src.dtypes[0] == "float32"
        checks["pinned_shape"] = src.shape == PINNED_SHAPE
        checks["pinned_crs"] = crs_ok
        checks["pinned_transform"] = src.transform == PINNED_TRANSFORM
        checks["all_stored_values_finite"] = bool(np.isfinite(arr).all())
        checks["all_stored_values_in_0_1"] = bool(np.isfinite(arr).all() and (arr >= 0).all() and (arr <= 1).all())
        checks["no_negative_float32_sentinel"] = not bool(np.any(arr == SENTINEL))
        metadata = {
            "shape": list(src.shape),
            "crs": src.crs.to_string() if src.crs else None,
            "transform": list(src.transform)[:6],
            "dtype": src.dtypes[0],
            "nodata": None if src.nodata is None else ("nan" if np.isnan(src.nodata) else float(src.nodata)),
            "minimum": float(np.nanmin(arr)),
            "maximum": float(np.nanmax(arr)),
            "positive_cells": int(np.count_nonzero(arr > 0)),
            "stored_cells": int(arr.size),
        }

    template_path = Path(args.template)
    if template_path.is_file():
        with rasterio.open(template_path) as tpl, rasterio.open(path) as sub:
            checks["matches_official_template_geometry"] = (
                tpl.width == sub.width and tpl.height == sub.height and
                tpl.crs == sub.crs and tpl.transform == sub.transform
            )
            template = tpl.read(1)
            valid_footprint = np.isfinite(template)
            metadata["official_template_valid_cells"] = int(valid_footprint.sum())
            metadata["template_footprint_positive_predictions"] = int(np.count_nonzero(sub.read(1)[~valid_footprint] > 0))
    else:
        checks["matches_official_template_geometry"] = None
        metadata["official_template_valid_cells"] = None

    labels_path = Path(args.labels)
    if labels_path.is_file():
        with rasterio.open(labels_path) as lab, rasterio.open(path) as sub:
            if lab.shape != sub.shape or lab.crs != sub.crs or lab.transform != sub.transform:
                checks["labels_geometry_matches_submission"] = False
                metadata["positive_cells_overlapping_labels"] = None
            else:
                labels = lab.read(1) > 0
                pred = sub.read(1) > 0
                checks["labels_geometry_matches_submission"] = True
                metadata["positive_cells_overlapping_labels"] = int(np.count_nonzero(pred & labels))
    else:
        checks["labels_geometry_matches_submission"] = None
        metadata["positive_cells_overlapping_labels"] = None

    format_checks = [v for k, v in checks.items() if k not in ("matches_official_template_geometry", "labels_geometry_matches_submission")]
    passed = all(format_checks) and checks["matches_official_template_geometry"] is not False and checks["labels_geometry_matches_submission"] is not False
    result = {
        "file": str(path),
        "local_format_checks_passed": bool(passed),
        "checks": checks,
        "metadata": metadata,
        "interpretation": "Local format inspection only. Missing template/labels are unavailable checks; no organizer acceptance or scientific prediction validity is implied.",
    }
    print(json.dumps(result, indent=2))
    if not passed:
        return 1
    if checks["matches_official_template_geometry"] is None or checks["labels_geometry_matches_submission"] is None:
        print("LOCAL FORMAT CHECKS PASS; OFFICIAL TEMPLATE AND/OR LABEL CHECK UNAVAILABLE.")
    else:
        print("LOCAL FORMAT AND SUPPLIED-INPUT CHECKS PASS; NOT AN ORGANIZER RECEIPT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
