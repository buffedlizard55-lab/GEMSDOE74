"""Three-pass verification suite auditing code, data, holdout scores, uniqueness,
final GeoTIFF bytes, permissions, documentation links, and evidence discipline."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
import torch
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

from src.gems74.models import DifferentiableDTILoss
from src.gems74.postprocess import submodular_max_cover_300m
from vendor.gems57 import metric, validate as v57
from vendor.gems57.grid import EPSG, HEIGHT, TRANSFORM, WIDTH, load_grid
from vendor.gems import validate_submission as v71


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


# ==============================================================================
# PASS 1: Code, Mathematical Loss Parity, and Submodular Post-Processor Invariants
# ==============================================================================
def test_pass1_differentiable_dti_exact_parity():
    rng = np.random.default_rng(74)
    p = rng.uniform(0.0, 1.0, (72, 72)).astype(np.float32)
    y = rng.uniform(0.0, 1.0, (72, 72)) > 0.96
    active = rng.uniform(0.0, 1.0, (72, 72)) > 0.08
    d = ndi.distance_transform_edt(~(y & active))
    q = metric.kernel(d).astype(np.float32)
    res_ref = metric.dti_exact(p, y, active)
    ref = float(res_ref["dti"] if isinstance(res_ref, dict) else res_ref[0])
    crit = DifferentiableDTILoss()
    got = float(
        crit.exact_soft_dti(
            torch.from_numpy(p[None, None]),
            torch.from_numpy(y.astype(np.float32)[None, None]),
            torch.from_numpy(q[None, None]),
            torch.from_numpy(active.astype(np.float32)[None, None]),
        ).item()
    )
    assert abs(ref - got) < 1e-7, f"DiffDTI mismatch: ref={ref} got={got}"


def test_pass1_submodular_cover_respects_budget_and_allow_mask():
    rng = np.random.default_rng(75)
    prob = rng.uniform(0.0, 0.8, (64, 64)).astype(np.float32)
    allow = rng.uniform(0.0, 1.0, (64, 64)) > 0.35
    dots, n_emitted = submodular_max_cover_300m(prob, allow, target_n=120, gamma=1.35)
    assert dots.dtype == np.float32
    assert n_emitted == 120
    assert int((dots > 0).sum()) == 120
    assert int(((dots > 0) & (~allow)).sum()) == 0


# ==============================================================================
# PASS 2: Data Integrity, Pre-Fit Leakage Canary, Holdout Edge, & Uniqueness Gate
# ==============================================================================
def test_pass2_leakage_canary_and_holdout_edge():
    canary = json.loads((ROOT / "evidence/leakage_canary.json").read_text())
    assert canary["n_model_features_tested"] == 52
    assert canary["all_features_passed"] is True
    assert canary["max_symmetric_auc"] <= 0.90

    ev = json.loads((ROOT / "evidence/holdout_evaluation.json").read_text())
    assert ev["protocol_compliance"]["experiments_executed"] == 3
    assert ev["protocol_compliance"]["max_experiments_budget"] == 3
    assert ev["protocol_compliance"]["zero_d_vis_shortcut"] is True
    assert ev["protocol_compliance"]["zero_sgmc_weight"] is True
    assert ev["protocol_compliance"]["zero_valid_mask_erosion"] is True

    sc = ev["pooled_holdout"]["scores"]
    assert sc["exp3_hybrid_crest_submod300"]["withheld_positive_pixels"] == 11321
    assert sc["exp3_hybrid_crest_submod300"]["dti"] > sc["h33_true_fold_fair"]["dti"]
    delta = ev["paired_vs_external_controls"]["exp3_hybrid_crest_submod300"]["paired_differences"]["h33_true_fold_fair"]
    assert delta["delta"] > 0.020
    assert delta["ci95"][0] > 0.0  # Entire 95% CI strictly positive!

    # Sweeps all 4 spatial folds 4/4
    for i in range(4):
        assert ev["per_fold_scores"]["exp3_hybrid_crest_submod300"][i] > ev["per_fold_scores"]["h33_true_fold_fair"][i]

    # Detached-strand check also strictly beats D28/H33
    det = ev["detached_strands_transfer"]
    assert det["candidate_dti"] > det["d28_h33_detached_dti"] + 0.015


def test_pass2_two_stage_registry_uniqueness():
    u1 = json.loads((ROOT / "evidence/uniqueness_stage1_surface.json").read_text())
    u2 = json.loads((ROOT / "evidence/uniqueness_stage2_dots.json").read_text())
    assert u1["complete_accessible_scan"] is True
    assert u2["complete_accessible_scan"] is True
    assert u1["registry_rasters_checked"] == 251
    assert u2["registry_rasters_checked"] == 251
    assert u1["worst_spearman_full_footprint"] <= 0.90
    assert u2["worst_spearman_full_footprint"] <= 0.90
    assert u2["worst_dot_overlap"] <= 0.70
    assert u2["unique"] is True


# ==============================================================================
# PASS 3: Final GeoTIFF, Dual Validators, Permissions, Checksums, & Docs Links
# ==============================================================================
def test_pass3_final_geotiff_dual_validators_and_permissions():
    rc = json.loads((ROOT / "evidence/run_card.json").read_text())
    tif_path = ROOT / rc["submission_file"]
    zip_path = ROOT / rc["submission_zip"]
    json_path = tif_path.with_suffix(".json")

    for p in (tif_path, zip_path, json_path):
        assert p.is_file(), f"Missing artifact: {p}"
        mode = p.stat().st_mode & 0o777
        assert mode & 0o044 == 0o044, f"File {p.name} missing world/group read bits (IRR-12): {oct(mode)}"

    assert _sha256(tif_path) == rc["raster_sha256"]
    assert _sha256(zip_path) == rc["zip_sha256"]
    assert len(rc["submission_note"]) <= 140
    assert rc["verdict"] == "promote"
    assert rc["ready_to_download_and_submit"] is True

    # Verify single-TIFF ZIP archive byte equality
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [tif_path.name]
        assert zf.read(tif_path.name) == tif_path.read_bytes()

    # Verify both independent validators live on disk
    grid = load_grid(ROOT / ".cache/gems_data/primary")
    r57 = v57.validate(tif_path, grid.footprint, grid.catalogue)
    assert r57["all_checks_passed"] is True
    assert r57["n_nan"] == 0
    assert r57["n_infinite"] == 0
    assert r57["min"] == 0.0 and r57["max"] == 1.0
    assert r57["emitted_positive_pixels"] == 37654
    assert r57["on_catalogue_positive_pixels"] == 0

    r71 = v71.validate(
        tif_path,
        reference_path=ROOT / ".cache/gems_data/primary/sample_submission.tif",
        features_path=ROOT / ".cache/gems_data/primary/gems-geodawn-numerical-features.tif",
        outside_policy="either",
    )
    assert r71["passed"] is True
    assert r71["has_failures"] is False

    # Verify zero local dead links in docs/index.html, docs/executive-summary.html, and README.md
    for html_file in (ROOT / "docs/index.html", ROOT / "docs/executive-summary.html"):
        text = html_file.read_text(encoding="utf-8")
        for attr in re.findall(r'(?:href|src)="([^"#]+)"', text):
            if attr.startswith(("http://", "https://", "mailto:")):
                continue
            target = (html_file.parent / attr).resolve()
            assert target.exists(), f"Broken relative asset/link '{attr}' in {html_file}"

    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "HIGHEST URGENCY: We MUST generate a genuinely unique .tif submission" in readme_text
    assert rc["raster_sha256"] in readme_text
    assert rc["submission_note"] in readme_text
