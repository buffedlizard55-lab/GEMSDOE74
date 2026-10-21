#!/usr/bin/env python3
"""Validate official competition inputs and write a truthful prepared manifest.

This does not derive or cache features. It only checks that the minimum official
rasters exist and that grid geometry matches the sample submission. A previous version
wrote {"checked": true} even when required data were absent; this implementation fails
closed instead.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import rasterio

DATA = Path("data")
REQUIRED = ("sample_submission.tif", "training_features.tif", "labels.tif")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect(path: Path) -> dict:
    with rasterio.open(path) as ds:
        # Read one band at a time to avoid keeping the complete feature cube in RAM.
        finite_by_band = []
        nan_by_band = []
        for band in range(1, ds.count + 1):
            arr = ds.read(band)
            finite_by_band.append(int(np.isfinite(arr).sum()))
            nan_by_band.append(int(np.isnan(arr).sum()))
        return {
            "path": str(path),
            "sha256": sha256(path),
            "shape": [ds.height, ds.width],
            "count": ds.count,
            "dtypes": list(ds.dtypes),
            "crs": ds.crs.to_string() if ds.crs else None,
            "transform": list(ds.transform)[:6],
            "nodata": ds.nodata,
            "finite_cells_per_band": finite_by_band,
            "nan_cells_per_band": nan_by_band,
        }


def main() -> int:
    missing = [DATA / name for name in REQUIRED if not (DATA / name).is_file()]
    if missing:
        print("Cannot prepare: required official files are missing:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        print("Download only from the authorized DrivenData data page. No manifest was written.", file=sys.stderr)
        return 2

    records = {name: inspect(DATA / name) for name in REQUIRED}
    template = records["sample_submission.tif"]
    geometry = (template["shape"], template["crs"], template["transform"])
    for name in ("training_features.tif", "labels.tif"):
        record = records[name]
        if (record["shape"], record["crs"], record["transform"]) != geometry:
            raise SystemExit(f"Grid mismatch: {name} does not match sample_submission.tif")

    manifest = {
        "schema": "gemsdoe74-prepared-inputs/1",
        "status": "inputs_present_geometry_checked_features_not_cached",
        "source": "Files placed by an authorized user from the official DrivenData data page",
        "official_source": "https://www.drivendata.org/competitions/306/competition-doe-gems/data/",
        "inputs": records,
        "important": "This manifest proves local file hashes and grid metadata only; it does not independently prove download source, licence, or scientific validity.",
    }
    out = DATA / "prepared_manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {out}; inputs and grid metadata checked. Feature caching/model preparation remain separate steps.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
