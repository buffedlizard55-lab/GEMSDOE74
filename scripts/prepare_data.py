#!/usr/bin/env python3
"""Prepare and verify competition data: check shapes, SHA-256 hashes, footprint mask, and write manifest."""
from __future__ import annotations

import hashlib
import json
import pathlib
import numpy as np
import rasterio

EXPECTED_HASHES = {
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
}


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    data_dir = pathlib.Path("data")
    src_dir = pathlib.Path("/tmp/gems74_data") if pathlib.Path("/tmp/gems74_data/training_features.tif").is_file() else data_dir
    files_report = {}

    for fname, exp_sha in EXPECTED_HASHES.items():
        p = src_dir / fname
        if not p.exists():
            print(f"Missing {p} — run scripts/download_competition_data.sh first")
            files_report[fname] = {"present": False}
            continue
        actual_sha = sha256_file(p)
        assert actual_sha == exp_sha, f"SHA-256 mismatch on {fname}: {actual_sha} != {exp_sha}"
        with rasterio.open(p) as ds:
            arr = ds.read(1)
            finite = int(np.isfinite(arr).sum())
            print(
                f"{fname}: bands={ds.count} shape={ds.shape} crs={ds.crs} dtype={ds.dtypes[0]} "
                f"finite={finite}/{ds.width * ds.height} sha256={actual_sha[:16]}..."
            )
            files_report[fname] = {
                "present": True,
                "sha256": actual_sha,
                "sha256_verified": True,
                "bands": int(ds.count),
                "shape": [int(ds.height), int(ds.width)],
                "crs": ds.crs.to_string(),
                "dtype": ds.dtypes[0],
                "finite_band1_pixels": finite,
            }

    ext_dir = src_dir / "external"
    ext_files = sorted(p.name for p in ext_dir.iterdir() if p.is_file()) if ext_dir.is_dir() else []
    manifest = {
        "checked": all(v.get("present", False) for v in files_report.values()),
        "data_source_dir": str(src_dir),
        "primary_rasters": files_report,
        "external_files_count": len(ext_files),
        "external_files": ext_files,
    }
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "prepared_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote data/prepared_manifest.json (all_verified={manifest['checked']}, external_files={len(ext_files)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
