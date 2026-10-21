"""Comprehensive release-integrity, GeoTIFF byte-level portal compliance, protocol gate,
and GitHub Pages link/asset verification tests for GEMSDOE74."""
from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from pathlib import Path

import numpy as np
import rasterio

from gemsdoe74.metric import compute_dti

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence"
DOCS = ROOT / "docs"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_ir_74_30_continuous_dti_regression_guard() -> None:
    """Verify IR-74-30 fix: continuous predictions p=0.001 and p=1.0 must score dramatically differently."""
    truth = np.zeros((20, 20), dtype=np.float32)
    truth[10, 10] = 1.0
    mask = np.ones((20, 20), dtype=bool)
    p_hi = np.zeros_like(truth)
    p_lo = np.zeros_like(truth)
    p_hi[10, 10] = 1.0
    p_lo[10, 10] = 1e-3
    assert compute_dti(p_hi, truth) == 1.0
    assert compute_dti(p_lo, truth) < 0.01


def test_promoted_geotiff_portal_and_byte_integrity() -> None:
    """Re-read the exact shipped GeoTIFF from disk and verify all DrivenData #306 portal constraints."""
    rc = json.loads((EVIDENCE / "run_card_g74.json").read_text())
    assert rc["verdict"] == "promote"
    assert len(rc["submission_note"]) <= 140
    assert rc["submission_note_length"] == len(rc["submission_note"])

    v = rc["validator_output"]
    tif_path = ROOT / v["file"]
    zip_path = ROOT / v["zip_file"]
    nan_path = ROOT / v["nan_twin_file"]

    for p in (tif_path, zip_path, nan_path):
        assert p.is_file(), f"Missing artifact {p}"
        assert (os.stat(p).st_mode & 0o444) == 0o444, f"File {p} must be world-readable for web serving"

    assert _sha256(tif_path) == rc["raster_sha256"] == v["sha256"]
    assert _sha256(zip_path) == v["zip_sha256"]
    assert _sha256(nan_path) == rc["nan_twin_sha256"] == v["nan_twin_sha256"]

    with zipfile.ZipFile(zip_path) as zf:
        assert tif_path.name in zf.namelist()

    with rasterio.open(tif_path) as src:
        assert str(src.crs) == "EPSG:32611"
        assert src.shape == (3730, 3292)
        assert list(src.transform)[:6] == [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]
        assert src.dtypes[0] == "float32"
        assert src.nodata is None
        arr = src.read(1)

    assert not np.isnan(arr).any(), "Primary zeros GeoTIFF must contain zero NaNs anywhere"
    assert not (np.abs(arr) > 1e20).any(), "Must contain zero float32 sentinels"
    assert float(arr.min()) == 0.0
    assert float(arr.max()) == 1.0
    assert int((arr > 0).sum()) == 37654
    assert set(np.unique(arr).tolist()) == {0.0, 1.0}


def test_parallel_run_protocol_gates() -> None:
    """Verify leakage canary (<= 0.90), uniqueness (<= 0.90 Spearman, <= 0.70 3-px dot overlap), and multi-instrument wins."""
    rc = json.loads((EVIDENCE / "run_card_g74.json").read_text())
    can = json.loads((EVIDENCE / "canaries_g74.json").read_text())
    uniq = json.loads((EVIDENCE / "uniqueness_g74.json").read_text())

    # Rule 4: Single-feature ROC-AUC canary
    assert can["passed"] is True
    assert can["max_symmetric_auc"] <= 0.90
    assert len(can["features"]) == 68
    for fname, meta in can["features"].items():
        assert meta["auc_symmetric"] <= 0.90, f"Leakage canary trip on {fname}: {meta}"

    # Rule 1: Registry uniqueness across all 165 rasters
    assert uniq["passed"] is True
    assert uniq["rasters_scanned"] >= 165
    assert rc["registry_uniqueness"]["max_spearman_pre_placement_surface"] <= 0.90
    assert rc["registry_uniqueness"]["max_spearman_final_dots"] <= 0.90
    assert rc["registry_uniqueness"]["max_3px_overlap_dot_submissions"] <= 0.70
    assert rc["registry_uniqueness"]["overlap_vs_h33_02778"] < 0.30

    # Benchmark superiority across all independent instruments
    hd = rc["holdout_dti"]
    assert hd["primary_pooled_hide_v2"]["dti"] > hd["primary_pooled_hide_v2"]["d28_02600_dti"]
    assert hd["primary_pooled_hide_v2"]["shipped_fullmask_dti"] > hd["primary_pooled_hide_v2"]["h33_02778_dti"]
    assert hd["live_calibrated_piedmont_offcat"]["dti"] > hd["live_calibrated_piedmont_offcat"]["h33_02778_dti"]
    assert hd["live_calibrated_piedmont_offcat"]["dti"] > hd["live_calibrated_piedmont_offcat"]["g36_02750_dti"]
    assert hd["off_catalogue_sgmc_d_ge_3"]["dti"] > hd["off_catalogue_sgmc_d_ge_3"]["h33_02778_dti"]
    assert hd["off_catalogue_sgmc_d_ge_3"]["delta_ci95_vs_h33"][0] > 0.0


def test_github_pages_links_assets_and_zero_synthetic_leftovers() -> None:
    """Verify all internal links & images across every HTML page in docs/ resolve on disk with zero legacy synthetic strings."""
    html_files = sorted(DOCS.rglob("*.html"))
    assert len(html_files) >= 14

    banned_tokens = [
        "gemsdoe74-h74-1",
        "0.3310",
        "0.3412",
        "0.1684",
    ]
    href_re = re.compile(r'(?:href|src)="([^"#?]+)"')

    for hf in html_files:
        text = hf.read_text()
        if hf.name not in ("irregularities.html", "hypotheses.html"):
            for bad in banned_tokens:
                assert bad not in text, f"Stale synthetic token `{bad}` found in {hf}"
        for match in href_re.finditer(text):
            target = match.group(1)
            if target.startswith(("http://", "https://", "mailto:", "javascript:", "data:")):
                continue
            resolved = (hf.parent / target).resolve()
            assert resolved.exists(), f"Broken relative link `{target}` in {hf} -> {resolved}"
