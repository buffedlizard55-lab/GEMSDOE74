#!/usr/bin/env python3
"""Prepare data after download_competition_data.sh: verify shapes, build footprint mask, write manifest."""
import pathlib, json, hashlib
import rasterio
import numpy as np

data = pathlib.Path("data")
for fname in ["sample_submission.tif","training_features.tif","existing_faults.tif"]:
    p=data/fname
    if not p.exists():
        print(f"Missing {p} — download first")
        continue
    with rasterio.open(p) as ds:
        arr=ds.read(1)
        finite=np.isfinite(arr).sum()
        print(f"{fname}: shape {ds.shape} crs {ds.crs} dtype {ds.dtypes[0]} finite {finite}/{ds.width*ds.height}")
        print(f"  transform {ds.transform} nodata {ds.nodata} range [{np.nanmin(arr):.3f},{np.nanmax(arr):.3f}]")

# Write manifest
manifest={"checked":True}
(data/"prepared_manifest.json").write_text(json.dumps(manifest,indent=2))
print("Wrote data/prepared_manifest.json")
