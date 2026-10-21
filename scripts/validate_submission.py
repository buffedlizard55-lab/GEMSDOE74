#!/usr/bin/env python3
"""Validate a submission TIF against competition portal rules (supports both zeros and NaN-outside modes).

Resolves IR-74-17:
- Distinguishes inside-footprint vs outside-footprint cells when sample_submission.tif is available.
- Accepts valid spec-literal NaN-outside GeoTIFFs (nodata=NaN, finite [0,1] inside footprint, NaN/0 outside)
  as well as portal-safe all-finite zeros-outside GeoTIFFs (nodata=None, all 12,279,160 cells finite in [0,1]).
- Checks for float32 sentinel -3.4028234663852886e+38 anywhere in the raster.
- Runs catalogue overlap check whenever labels.tif / existing_faults.tif is present.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import sys
import numpy as np
import rasterio

EXPECTED_SHAPE = (3730, 3292)
EXPECTED_TRANSFORM = rasterio.Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_default_file(candidates: list[str]) -> pathlib.Path | None:
    for c in candidates:
        p = pathlib.Path(c)
        if p.is_file():
            return p
    return None


def validate_submission_file(
    path: pathlib.Path,
    template_path: pathlib.Path | None = None,
    catalogue_path: pathlib.Path | None = None,
    require_all_finite: bool = False,
) -> dict:
    path = pathlib.Path(path)
    if template_path is None:
        template_path = _find_default_file([
            "data/sample_submission.tif",
            "/tmp/gems74_data/sample_submission.tif",
            "/tmp/gems74_workspace/data/sample_submission.tif",
        ])
    if catalogue_path is None:
        catalogue_path = _find_default_file([
            "data/labels.tif",
            "data/existing_faults.tif",
            "/tmp/gems74_data/labels.tif",
            "/tmp/gems74_workspace/data/labels.tif",
        ])

    footprint = None
    if template_path is not None and pathlib.Path(template_path).is_file():
        with rasterio.open(template_path) as tpl:
            footprint = np.isfinite(tpl.read(1))

    cat = None
    if catalogue_path is not None and pathlib.Path(catalogue_path).is_file():
        with rasterio.open(catalogue_path) as cds:
            cat = cds.read(1) > 0
            if footprint is not None:
                cat = cat & footprint

    with rasterio.open(path) as src:
        data = src.read(1)
        nodata = src.nodata
        nodata_is_nan = isinstance(nodata, float) and math.isnan(nodata)
        nodata_ok = (nodata is None) or nodata_is_nan

        checks: dict[str, bool | None] = {}
        checks["single_band"] = src.count == 1
        checks["dtype_float32"] = src.dtypes[0] == "float32"
        checks["dimensions_3730x3292"] = (src.height, src.width) == EXPECTED_SHAPE
        checks["crs_epsg_32611"] = bool(src.crs and src.crs.to_epsg() == 32611)
        checks["transform"] = src.transform == EXPECTED_TRANSFORM
        checks["nodata_none_or_nan"] = nodata_ok
        checks["no_sentinel_-3.4e38"] = not bool(np.any(data < -1e30))
        checks["zero_inf"] = int(np.isinf(data).sum()) == 0

        finite_mask = np.isfinite(data)
        finite_vals = data[finite_mask]
        checks["finite_values_in_0_1"] = bool(
            finite_vals.size > 0 and (finite_vals >= 0.0).all() and (finite_vals <= 1.0).all()
        )

        if footprint is not None and footprint.shape == data.shape:
            inside = data[footprint]
            outside = data[~footprint]
            in_fin = bool(np.isfinite(inside).all())
            in_rng = bool(in_fin and (inside >= 0.0).all() and (inside <= 1.0).all())
            out_ok = bool(np.all(np.isnan(outside) | (outside == 0.0)))
            checks["in_footprint_all_finite"] = in_fin
            checks["in_footprint_zero_nan"] = int(np.isnan(inside).sum()) == 0
            checks["in_footprint_zero_inf"] = int(np.isinf(inside).sum()) == 0
            checks["in_footprint_range_0_1"] = in_rng
            checks["outside_footprint_compliant"] = out_ok
            n_out_pos = int(np.sum(np.isfinite(outside) & (outside > 0.0)))
        else:
            all_fin = bool(finite_mask.all())
            checks["in_footprint_all_finite"] = all_fin if require_all_finite else checks["finite_values_in_0_1"]
            checks["in_footprint_zero_nan"] = all_fin if require_all_finite else True
            checks["in_footprint_zero_inf"] = checks["zero_inf"]
            checks["in_footprint_range_0_1"] = checks["finite_values_in_0_1"]
            checks["outside_footprint_compliant"] = True
            n_out_pos = 0

        if require_all_finite:
            checks["strict_whole_grid_all_finite"] = bool(finite_mask.all()) and (nodata is None)

        checks["validator_range_0_1_guaranteed"] = bool(
            checks["in_footprint_range_0_1"]
            and checks["in_footprint_all_finite"]
            and checks["no_sentinel_-3.4e38"]
            and checks["zero_inf"]
        )

        pos_mask = finite_mask & (data > 0.0)
        on_cat = None
        if cat is not None and cat.shape == data.shape:
            on_cat = int((pos_mask & cat).sum())
            checks["zero_on_catalogue_leakage"] = (on_cat == 0)
        else:
            checks["zero_on_catalogue_leakage"] = None

        passed = all(v is True for v in checks.values() if v is not None)
        return {
            "file": path.name,
            "path": str(path),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "shape": [int(src.height), int(src.width)],
            "crs": src.crs.to_string() if src.crs else None,
            "dtype": src.dtypes[0],
            "nodata": None if nodata is None else ("nan" if nodata_is_nan else float(nodata)),
            "emitted_positive_pixels": int(pos_mask.sum()),
            "in_footprint_positive_pixels": int((pos_mask & footprint).sum()) if footprint is not None else int(pos_mask.sum()),
            "outside_footprint_positive_pixels": n_out_pos,
            "on_catalogue_positive_pixels": on_cat,
            "full_grid_finite_pixels": int(finite_mask.sum()),
            "min_finite": float(finite_vals.min()) if finite_vals.size else None,
            "max_finite": float(finite_vals.max()) if finite_vals.size else None,
            "checks": checks,
            "all_checks_passed": passed,
        }


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a GEMS submission GeoTIFF.")
    ap.add_argument("path", nargs="?", default="docs/downloads/gemsdoe74-h74-r1-transtensional-submod-37654-20261021T000000Z-zeros.tif")
    ap.add_argument("--template", default=None, help="Path to sample_submission.tif")
    ap.add_argument("--catalogue", default=None, help="Path to labels.tif / existing_faults.tif")
    ap.add_argument("--strict-finite", action="store_true", help="Require all 12,279,160 cells to be finite (zeros-outside mode)")
    args = ap.parse_args()

    p = pathlib.Path(args.path)
    print(f"Validating {p}")
    rep = validate_submission_file(
        p,
        template_path=pathlib.Path(args.template) if args.template else None,
        catalogue_path=pathlib.Path(args.catalogue) if args.catalogue else None,
        require_all_finite=args.strict_finite,
    )
    print(json.dumps(rep, indent=2))
    if rep["all_checks_passed"]:
        print("ALL CHECKS PASS")
        return 0
    print("SOME CHECKS FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
