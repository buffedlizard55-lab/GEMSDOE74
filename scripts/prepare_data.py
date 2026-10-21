#!/usr/bin/env python3
"""Validate locally placed official competition inputs and write a provenance manifest.

This script does not download data or decide usage rights. Place authorized official
files under data/ and verify provenance from the DrivenData data tab first.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

DATA = Path("data")
REQUIRED = ("sample_submission.tif", "training_features.tif", "labels.tif")
OPTIONAL_RASTERS = ("existing_faults.tif",)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    missing = [name for name in REQUIRED if not (DATA / name).is_file()]
    if missing:
        print("BLOCKED: missing required official input(s): " + ", ".join(missing), file=sys.stderr)
        print("No prepared_manifest.json was written. Obtain authorized files from the official data tab.", file=sys.stderr)
        return 2

    reference = DATA / "sample_submission.tif"
    with rasterio.open(reference) as template:
        geometry = {
            "width": template.width,
            "height": template.height,
            "shape": [template.height, template.width],
            "crs": template.crs.to_string() if template.crs else None,
            "transform": list(template.transform)[:6],
            "band_count": template.count,
            "dtype": list(template.dtypes),
            "nodata": template.nodata,
            "finite_footprint_cells": int(np.isfinite(template.read(1)).sum()),
        }
    if not geometry["crs"]:
        print("FAIL: sample_submission.tif has no CRS", file=sys.stderr)
        return 1

    datasets = []
    for name in REQUIRED[1:] + tuple(n for n in OPTIONAL_RASTERS if (DATA / n).is_file()):
        path = DATA / name
        with rasterio.open(path) as dataset:
            matches = (
                dataset.width == geometry["width"] and
                dataset.height == geometry["height"] and
                dataset.crs == rasterio.crs.CRS.from_string(geometry["crs"]) and
                dataset.transform == rasterio.Affine(*geometry["transform"])
            )
            record = {
                "file": name,
                "sha256": sha256(path),
                "shape": [dataset.height, dataset.width],
                "crs": dataset.crs.to_string() if dataset.crs else None,
                "transform": list(dataset.transform)[:6],
                "band_count": dataset.count,
                "dtype": list(dataset.dtypes),
                "nodata": dataset.nodata,
                "matches_sample_submission_geometry": bool(matches),
            }
            datasets.append(record)
            if not matches:
                print(f"FAIL: {name} geometry does not match sample_submission.tif", file=sys.stderr)

    if not all(item["matches_sample_submission_geometry"] for item in datasets):
        print("No prepared_manifest.json was written because geometry checks failed.", file=sys.stderr)
        return 1

    manifest = {
        "schema": "gemsdoe74-input-manifest/1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "provenance_status": "owner must verify files came from authorized official competition download",
        "template": {"file": reference.name, "sha256": sha256(reference), **geometry},
        "datasets": datasets,
        "status": "local geometry/integrity checks passed; scientific validity and rights not asserted",
    }
    target = DATA / "prepared_manifest.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    print(f"Wrote {target}; verify source rights and feature-band meanings before use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
