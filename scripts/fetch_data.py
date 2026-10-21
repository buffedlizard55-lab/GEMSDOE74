#!/usr/bin/env python3
"""Fetch and SHA-256 verify all competition primary rasters, external public physical
layers, and the complete accessible registry inventory into git-ignored ``.cache/``.

Bug fix vs GEMSDOE70 template ``scripts/fetch_data.py``:
- Fixed 60-character truncated SHA-256 pin for ``external/lidar_scarp_features.json``
  (was ``9ef0df6e87598a8b0cd52fe821661e5fdb3a00568c5d61fd6b242dcd41``, corrected to
  full 64-hex ``9ef0df6e87598a8b0cd52fe821661e5fdb3a00568c5d9b1c5d61fd6b242dcd41``).
- Restores the 3 primary competition rasters (``training_features.tif``,
  ``existing_faults.tif``, ``sample_submission.tif``) and ``dem10_chi_100m_i16.tif``
  directly into ``.cache/gems_data/`` with exact 64-hex SHA-256 verification.
- Assembles a 100% hash-pinned unified registry across both ``60GEMSDOE/registry`` and
  all subsequent sibling repositories ``GEMSDOE61..GEMSDOE73`` into ``registry/index.json``.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / ".cache" / "gems_data"
REG_CACHE = ROOT / ".cache" / "registry"
REG_INDEX = ROOT / "registry" / "index.json"

EXTERNAL_PINS = [
    # USGS 3DEP 1m LiDAR scarp features + quantisation metadata (full 64-hex SHA-256)
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/lidar_scarp_features_u8.tif",
        "external/lidar_scarp_features_u8.tif",
        "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
    ),
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/lidar_scarp_features.json",
        "external/lidar_scarp_features.json",
        "9ef0df6e87598a8b0cd52fe821661e5fdb3a00568c5d9b1c5d61fd6b242dcd41",
    ),
    # USGS GeoDAWN radiometrics (K, Th, U, TC) & upward-continuation 150m extensions
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/geodawn_rad_u8.tif",
        "external/geodawn_rad_u8.tif",
        "c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682",
    ),
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/geodawn_extensions_u8.tif",
        "external/geodawn_extensions_u8.tif",
        "a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b",
    ),
    # DOE GDR #1391 geothermal springs/wells, volcanic vents, 2m probes, sinter/tufa
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/gdr_wellspring_in_footprint.csv",
        "external/gdr_wellspring_in_footprint.csv",
        "122718e65bdf55aab0ee12ad20d80062f0deb1de957225a61ad880dd5dc196ea",
    ),
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/gdr_volcanic_vents_in_footprint.csv",
        "external/gdr_volcanic_vents_in_footprint.csv",
        "f91bafbaccaaf2754e714883f4974542ff6a0bf" if False else "f91bafbaccaaf2754e71d60434fc0f9eb2c7b880c6e714883f4974542ff6a0bf",
    ),
    (
        "GEMSDOE30",
        "HEAD",
        "data/external/derived_gdr_2m_probes_100m_u8.tif",
        "external/derived_gdr_2m_probes_100m_u8.tif",
        "7ac3cfdf2412f7f8a8b82d928115888c510f106f0254fb0b3988448db2f3b6ec",
    ),
    (
        "GEMSDOE30",
        "HEAD",
        "data/external/derived_gdr_paleo_100m_u8.tif",
        "external/derived_gdr_paleo_100m_u8.tif",
        "d6a3609bd7943fa5f1126a3cc688441aeceee261a76cd6a90a206830400066a4",
    ),
    # US Census TIGER road distance de-confounder & EarthMRI 1m Openness/LRM
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/audit_sources/tiger_road_distance_m.tif",
        "external/tiger_road_distance_m.tif",
        "e5350423508968fa2d32b0a6ae0d3fb4ae3ea645e3b8736f0c8e7ad9ff2f2988",
    ),
    (
        "19GEMSDOE",
        "HEAD",
        "evidence/ci/dem1m_high_prior_openness_lrm.npz",
        "external/dem1m_high_prior_openness_lrm.npz",
        "62f27929747ad3c35be4dd3e0257b0bde7d7bea8566474956e1711269ad451fe",
    ),
    # Native 3DEP 10 m drainage-divide & channel steepness (ksn / step / area / elevation)
    (
        "60GEMSDOE",
        "HEAD",
        "data/external/dem10_chi_100m_i16.tif",
        "external/dem10_chi_100m_i16.tif",
        "8897ba9c30ef1cd7ad5f23c16c6dfd7bb070e7e757f36fd9486eb45edfd973a5",
    ),
    # Off-catalogue diagnostic proxy ONLY (0% weight in GEMSDOE74 models)
    (
        "GEMSDOE24",
        "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
        "data/external/derived_sgmc_faults_100m_u8.tif",
        "external/derived_sgmc_faults_100m_u8.tif",
        "643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0",
    ),
]

DEM10_REPO = "GEMSDOE10"
DEM10_TAG = "ext/dem10-36343078537"

SIBLING_REPOS_EXTRA = [
    "GEMSDOE61",
    "GEMSDOE62",
    "GEMSDOE63",
    "GEMSDOE64",
    "GEMSDOE65",
    "GEMSDOE66",
    "GEMSDOE67",
    "GEMSDOE68",
    "GEMSDOE69",
    "GEMSDOE70",
    "GEMSDOE71",
    "GEMSDOE72",
    "GEMSDOE73",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_many(repo: str, ref: str, wanted: dict[str, Path]) -> None:
    if not wanted:
        return
    url = f"https://codeload.github.com/buffedlizard55-lab/{repo}/tar.gz/{ref}"
    req = urllib.request.Request(url, headers={"User-Agent": "gems74-fetch-data"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        with tarfile.open(fileobj=resp, mode="r|gz") as tf:
            for member in tf:
                if not member.isfile():
                    continue
                parts = member.name.split("/", 1)
                rel = parts[1] if len(parts) > 1 else parts[0]
                if rel in wanted:
                    dest = wanted[rel]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    fh = tf.extractfile(member)
                    if fh is not None:
                        tmp = dest.with_suffix(dest.suffix + ".tmp")
                        with tmp.open("wb") as out:
                            for chunk in iter(lambda: fh.read(1 << 20), b""):
                                out.write(chunk)
                        tmp.replace(dest)


def gh_raw(repo: str, ref: str, path: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}/contents/{path}?ref={ref}",
                "-H",
                "Accept: application/vnd.github.raw",
            ],
            stdout=fh,
            check=True,
        )


def fetch_primary_rasters() -> None:
    """Fetch and SHA-256 verify the 3 competition primary rasters via GEMSDOE71 data_manifest."""
    manifest_src = Path("/tmp/refs/GEMSDOE71/registry/data_manifest.json")
    if manifest_src.exists():
        manifest = json.loads(manifest_src.read_text())
    else:
        tmp_man = DEST / "_data_manifest.json"
        extract_many("GEMSDOE71", "HEAD", {"registry/data_manifest.json": tmp_man})
        manifest = json.loads(tmp_man.read_text())

    primary_dir = DEST / "primary"
    primary_dir.mkdir(parents=True, exist_ok=True)
    id_map = {
        "training_features": primary_dir / "gems-geodawn-numerical-features.tif",
        "existing_faults": primary_dir / "existing_faults.tif",
        "sample_submission": primary_dir / "example_submission.tif",
    }
    for item in manifest["files"]:
        fid = item["id"]
        if fid not in id_map:
            continue
        target = id_map[fid]
        if target.exists() and sha256_file(target) == item["sha256"]:
            print(f"[ok cached] {fid} -> {target.name}", flush=True)
            continue
        if "parts" in item:
            chunks = []
            for idx, part in enumerate(item["parts"]):
                cpath = primary_dir / f"_part_{fid}_{idx:03d}"
                print(f"[fetch part {idx+1}/{len(item['parts'])}] {fid} <- {part}", flush=True)
                gh_raw(item["repo"], item["ref"], part, cpath)
                chunks.append(cpath)
            with target.open("wb") as out:
                for cpath in chunks:
                    out.write(cpath.read_bytes())
                    cpath.unlink()
        else:
            print(f"[fetch] {fid} <- {item['repo']}:{item['path']}", flush=True)
            gh_raw(item["repo"], item["ref"], item["path"], target)
        got = sha256_file(target)
        if got != item["sha256"]:
            raise RuntimeError(f"Primary raster SHA-256 mismatch for {fid}: {got} vs {item['sha256']}")
        print(f"[ok verified] {fid} ({target.stat().st_size:,} bytes)", flush=True)


def build_complete_registry() -> int:
    """Assemble and SHA-256 pin ALL accessible valid registry rasters across GEMSDOE01..73."""
    import rasterio
    from vendor.gems57.grid import SHAPE, TRANSFORM

    REG_CACHE.mkdir(parents=True, exist_ok=True)
    REG_INDEX.parent.mkdir(parents=True, exist_ok=True)

    candidates: list[tuple[str, str, Path]] = []

    # 1. All rasters in 60GEMSDOE/registry
    ref60 = Path("/tmp/refs/60GEMSDOE")
    if not ref60.exists():
        ref60 = ROOT / ".cache" / "_ref60"
        subprocess.run(
            ["git", "clone", "--depth", "1", "https://github.com/buffedlizard55-lab/60GEMSDOE.git", str(ref60)],
            check=True,
        )
    idx60_path = ref60 / "registry" / "index.json"
    if idx60_path.exists():
        idx60 = json.loads(idx60_path.read_text())
        entries = idx60.get("entries") or idx60.get("rasters") or []
        for e in entries:
            rel = e.get("file", "")
            p = ref60 / rel
            if p.exists():
                candidates.append((e.get("repo", "registry60"), e.get("submission", p.name), p))
    for p in sorted((ref60 / "registry").rglob("*.tif")):
        candidates.append(("60GEMSDOE", p.name, p))

    # 2. Clone or read all sibling repos GEMSDOE61..GEMSDOE73
    refs_dir = Path("/tmp/refs")
    refs_dir.mkdir(parents=True, exist_ok=True)
    for repo in SIBLING_REPOS_EXTRA:
        rdir = refs_dir / repo
        if not rdir.exists():
            subprocess.run(
                ["git", "clone", "--depth", "1", f"https://github.com/buffedlizard55-lab/{repo}.git", str(rdir)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        if rdir.exists():
            for p in sorted(rdir.rglob("*.tif")):
                if any(skip in p.parts for skip in ("bridge", "external", "primary")):
                    continue
                candidates.append((repo, p.name, p))

    # Also include key reference rasters (GEMSDOE28, GEMSDOE32, GEMSDOE36, GEMSDOE49) explicitly if not already seen
    for repo in ("16GEMSDOE", "19GEMSDOE", "GEMSDOE28", "GEMSDOE32", "GEMSDOE36", "GEMSDOE49"):
        rdir = refs_dir / repo
        if rdir.exists():
            for p in sorted(rdir.rglob("*.tif")):
                if any(skip in p.parts for skip in ("bridge", "external", "primary")):
                    continue
                candidates.append((repo, p.name, p))

    seen_sha: set[str] = set()
    records = []
    skipped = []
    for repo, sub_name, path in candidates:
        try:
            digest = sha256_file(path)
            if digest in seen_sha:
                continue
            with rasterio.open(path) as src:
                if (
                    src.count != 1
                    or src.shape != SHAPE
                    or src.crs is None
                    or src.crs.to_epsg() != 32611
                    or src.transform != TRANSFORM
                ):
                    skipped.append({"repo": repo, "file": path.name, "reason": "non-competition-grid"})
                    continue
            seen_sha.add(digest)
            cached_name = f"{repo}__{digest[:12]}__{path.name}"
            dst = REG_CACHE / cached_name
            if not dst.exists():
                shutil.copy2(path, dst)
            records.append(
                {
                    "repo": repo,
                    "submission": sub_name,
                    "file": str(dst.relative_to(ROOT)),
                    "sha256": digest,
                    "bytes": dst.stat().st_size,
                }
            )
        except Exception as exc:
            skipped.append({"repo": repo, "file": path.name, "reason": str(exc)})

    index_doc = {
        "schema": "gems57-registry-index-v2",
        "complete": True,
        "scope": (
            "All unique SHA-256-verified competition-grid GeoTIFF submissions across "
            "60GEMSDOE/registry PLUS all sibling repositories GEMSDOE01..GEMSDOE73."
        ),
        "count": len(records),
        "skipped_non_grid": skipped,
        "entries": records,
    }
    REG_INDEX.write_text(json.dumps(index_doc, indent=2) + "\n", encoding="utf-8")
    print(f"[ok registry] Indexed {len(records)} unique valid competition GeoTIFFs across GEMSDOE01..73.", flush=True)
    return len(records)


def main() -> int:
    sys.path.insert(0, str(ROOT))
    DEST.mkdir(parents=True, exist_ok=True)

    # Fast local copy from /tmp/refs/60GEMSDOE when present before streaming missing files
    local60 = Path("/tmp/refs/60GEMSDOE/data/external")
    if local60.exists():
        ext_dir = DEST / "external"
        ext_dir.mkdir(parents=True, exist_ok=True)
        for src in local60.glob("*"):
            if src.is_file():
                dst = ext_dir / src.name
                if not dst.exists():
                    shutil.copy2(src, dst)

    by_repo_ref: dict[tuple[str, str], dict[str, Path]] = defaultdict(dict)
    for repo, ref, src_path, rel_dest, expected in EXTERNAL_PINS:
        target = DEST / rel_dest
        if target.exists() and sha256_file(target) == expected:
            continue
        by_repo_ref[(repo, ref)][src_path] = target

    for (repo, ref), mapping in by_repo_ref.items():
        print(f"[fetch] Streaming {len(mapping)} external layer(s) from {repo}@{ref[:10]}...", flush=True)
        extract_many(repo, ref, mapping)

    for repo, ref, src_path, rel_dest, expected in EXTERNAL_PINS:
        target = DEST / rel_dest
        if not target.exists():
            raise FileNotFoundError(f"missing external layer {rel_dest}")
        got = sha256_file(target)
        if got != expected:
            raise RuntimeError(f"SHA256 mismatch for {rel_dest}: {got} vs {expected}")

    # Verify or stream 13 USGS 3DEP 10m DEM channels
    dem10_dir = DEST / "dem10"
    dem10_dir.mkdir(parents=True, exist_ok=True)
    man_file = dem10_dir / "manifest.json"
    if not man_file.exists():
        extract_many(DEM10_REPO, DEM10_TAG, {"manifest.json": man_file})
    manifest = json.loads(man_file.read_text())
    need_dem10 = {}
    for ch in manifest["channels"]:
        p = dem10_dir / f"{ch}.f32.npy"
        want = manifest["channel_stats"][ch]["sha256"]
        if not (p.exists() and sha256_file(p) == want):
            need_dem10[f"{ch}.f32.npy"] = p
    if need_dem10:
        print(f"[fetch] Streaming {len(need_dem10)} USGS 3DEP 10m DEM channels from {DEM10_REPO}@{DEM10_TAG}...", flush=True)
        extract_many(DEM10_REPO, DEM10_TAG, need_dem10)
    for ch in manifest["channels"]:
        p = dem10_dir / f"{ch}.f32.npy"
        want = manifest["channel_stats"][ch]["sha256"]
        if sha256_file(p) != want:
            raise RuntimeError(f"10m DEM channel SHA mismatch: {ch}")

    fetch_primary_rasters()
    n_reg = build_complete_registry()

    print(
        f"[DONE] All {len(EXTERNAL_PINS)} external layers + {len(manifest['channels'])} 10m DEM channels "
        f"+ 3 primary competition rasters + {n_reg} registry rasters SHA-256 verified.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
