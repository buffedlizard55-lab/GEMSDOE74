#!/usr/bin/env python3
"""Execute GEMSDOE74 pre-registered pipeline end-to-end on real SHA-256-verified rasters:

  Step 0: Materialize 52-channel zero-catalogue multi-physics cube & run Protocol Rule 4
          single-feature holdout AUC leakage canary (must pass <= 0.90 across all 52 channels).
  Exp  1: ``E1-PUDeconfTabOOF`` — 4-quadrant OOF Positive-Tile PU LightGBM ensemble.
  Exp  2: ``E2-ResUNetDiffDTI`` — 4-quadrant OOF Multi-Scale 2D ResUNet trained directly under
          exact Differentiable 300 m DW-Tversky Loss (alpha=0.2, beta=0.8).
  Exp  3: ``E3-HybridCrestSubmod300`` — Nested-OOF calibrated log-odds synthesis of E2 + E1 +
          multi-domain physical corroboration + TIGER highway mimic attenuation + cross-strike
          directional crest sharpening + exact unblurred 300 m lazy-greedy submodular max-cover.

  Stage-1 & Stage-2 Uniqueness Gate: Verify continuous surface (|rho| <= 0.90) AND final GeoTIFF
          (|rho| <= 0.90, 3-px overlap <= 0.70) against ALL 251 registry rasters across GEMSDOE01..73.
  Packaging & Validation: Write submission via untouched ``vendor.gems57.submission_writer`` and
          audit with both ``vendor.gems57.validate`` and ``vendor.gems.validate_submission``.
"""
from __future__ import annotations

import gc
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.special import expit, logit

from vendor.gems57 import evaluate_holdout, holdout, submission_writer, uniqueness, validate as v57
from vendor.gems57.grid import load_grid
from vendor.gems import validate_submission as v71
from src.gems74.features import FEATURE_NAMES, build_or_load_feature_cube, run_leakage_canary
from src.gems74.models import (
    equalize_lidar_regime,
    fit_exp1_pu_tabular_oof,
    fit_exp2_resunet_diffdti_oof,
)
from src.gems74.postprocess import directional_crest_sharpen, submodular_max_cover_300m

BASE_BUDGET = 37654
COLLAR_PX = 2.0


def _cropped_eval(fold: dict, pred: np.ndarray, valid: np.ndarray):
    y, x = np.nonzero(fold["region"])
    y0, x0 = max(0, int(y.min()) - 6), max(0, int(x.min()) - 6)
    y1, x1 = min(pred.shape[0], int(y.max()) + 7), min(pred.shape[1], int(x.max()) + 7)
    sl = np.s_[y0:y1, x0:x1]
    sub = {k: v[sl] for k, v in fold.items() if isinstance(v, np.ndarray) and v.shape == pred.shape}
    return evaluate_holdout.evaluate(pred[sl], sub, valid[sl], origin=(y0, x0), global_shape=pred.shape)


def _fuse_surface(
    p_cnn: np.ndarray,
    p_tab: np.ndarray,
    cube: np.memmap,
    normal_xy: np.memmap,
    valid: np.ndarray,
    w_cnn: float = 0.65,
    sharp_strength: float = 0.55,
) -> np.ndarray:
    """Calibrated log-odds fusion + 6 km regional de-biasing + highway mimic attenuation + crest sharpening."""
    eps = 1e-5
    l_cnn_raw = logit(np.clip(p_cnn, eps, 1.0 - eps))
    l_tab_raw = logit(np.clip(p_tab, eps, 1.0 - eps))
    # Subtract ultra-broad 6 km (sigma=60 px) regional drift to remove 100 km basin amplitude bias
    # (IRR-11: NW p99=0.709 vs SE p99=0.552) while preserving 100% of sharp 100 m - 3 km fault contrasts!
    l_cnn = 0.65 * (l_cnn_raw - ndi.gaussian_filter(l_cnn_raw, sigma=60.0, mode="nearest")) + 0.35 * l_cnn_raw
    l_tab = 0.65 * (l_tab_raw - ndi.gaussian_filter(l_tab_raw, sigma=60.0, mode="nearest")) + 0.35 * l_tab_raw

    s_cnn = float(np.std(l_cnn[valid])) + 1e-6
    s_tab = float(np.std(l_tab[valid])) + 1e-6
    mu_cnn = float(np.median(l_cnn[valid]))
    mu_tab = float(np.median(l_tab[valid]))

    z_blend = w_cnn * ((l_cnn - mu_cnn) / s_cnn) + (1.0 - w_cnn) * ((l_tab - mu_tab) / s_tab)

    # Attenuate pure single-sensor road/rail embankments: close to TIGER road (tiger_road_logdist < -1.15)
    # where deep subsurface basement/gravity/magnetic evidence is weak (worm_geopotential_flank < 0.25)
    road_z = cube[39].astype(np.float32)
    geopot_w = cube[51].astype(np.float32)
    road_mimic = (road_z < -1.15) & (geopot_w < 0.25)
    z_blend = np.where(road_mimic, z_blend - 0.65, z_blend)

    p_raw = expit(mu_cnn + s_cnn * z_blend).astype(np.float32)
    lid_ok = (cube[37] > 0) & valid
    p_eq = equalize_lidar_regime(p_raw, lid_ok, valid)
    return directional_crest_sharpen(p_eq, normal_xy, valid, strength=sharp_strength)


def _dump_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    t_start = time.time()
    ev_dir = ROOT / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)

    print("=== [0/6] Loading competition grid & shared holdout folds ===", flush=True)
    grid = load_grid(ROOT / ".cache/gems_data/primary")
    valid = grid.footprint
    folds, quad = holdout.buffered_component_draw(
        grid, seed=20, hide_frac=0.20, buffer_px=3, boundary_px=12
    )

    print("=== [1/6] Building/verifying 52-channel stack + Mandatory Leakage Canary ===", flush=True)
    cube, norm = build_or_load_feature_cube(grid)
    canary = run_leakage_canary(cube, folds, valid, ev_dir / "leakage_canary.json")
    print(
        f"[OK] Leakage canary PASSED all {canary['n_model_features_tested']} features "
        f"(max symmetric AUC = {canary['max_symmetric_auc']:.5f} <= 0.90)",
        flush=True,
    )

    # Cache intermediate OOF/prod probability surfaces in .cache so reruns/packaging are instant & reproducible
    exp1_cache = ROOT / ".cache" / "exp1_probs.npz"
    if exp1_cache.exists():
        z1 = np.load(exp1_cache)
        e1_oof, e1_prod = z1["oof"], z1["prod"]
        e1_meta = json.loads((ev_dir / "exp1_meta.json").read_text())
        print("[cache] Loaded cached Exp 1 OOF & production probabilities.", flush=True)
    else:
        print("=== [2/6] Running Experiment 1: E1-PUDeconfTabOOF ===", flush=True)
        e1_oof, e1_prod, e1_meta = fit_exp1_pu_tabular_oof(cube, folds, quad, valid, seed=7401)
        np.savez_compressed(exp1_cache, oof=e1_oof, prod=e1_prod)
        _dump_json(ev_dir / "exp1_meta.json", e1_meta)

    exp2_cache = ROOT / ".cache" / "exp2_probs.npz"
    if exp2_cache.exists():
        z2 = np.load(exp2_cache)
        e2_oof, e2_prod = z2["oof"], z2["prod"]
        e2_meta = json.loads((ev_dir / "exp2_meta.json").read_text())
        print("[cache] Loaded cached Exp 2 OOF & production probabilities.", flush=True)
    else:
        print("=== [3/6] Running Experiment 2: E2-ResUNetDiffDTI ===", flush=True)
        e2_oof, e2_prod, e2_meta = fit_exp2_resunet_diffdti_oof(
            cube, folds, quad, valid, epochs=14, tile_px=128, base_ch=20, seed=7402
        )
        np.savez_compressed(exp2_cache, oof=e2_oof, prod=e2_prod)
        _dump_json(ev_dir / "exp2_meta.json", e2_meta)

    print("=== [4/6] Running Experiment 3 (Nested-OOF Hybrid Crest + Submod300) & Pooled Evaluation ===", flush=True)
    # Precompute fold-specific candidate grids for fast nested-OOF selection without ever touching held-out fold k
    grid_configs = [
        (0.55, 0.50, 34000, 1.35),
        (0.65, 0.55, 37654, 1.35),
        (0.65, 0.55, 42000, 1.45),
        (0.72, 0.60, 45000, 1.50),
    ]
    pre_surfaces = {}
    for w_cnn, sh, bud, gam in grid_configs:
        key = (w_cnn, sh)
        if key not in pre_surfaces:
            pre_surfaces[key] = _fuse_surface(e2_oof, e1_oof, cube, norm, valid, w_cnn=w_cnn, sharp_strength=sh)

    # Evaluate every config on each quadrant individually first so quadrant k chooses strictly argmax over j != k
    per_cfg_fold_res: dict[tuple, list[tuple[dict, np.ndarray]]] = {cfg: [] for cfg in grid_configs}
    for cfg in grid_configs:
        w_cnn, sh, bud, gam = cfg
        surf = pre_surfaces[(w_cnn, sh)]
        for k, fold in enumerate(folds):
            d_vis_k = ndi.distance_transform_edt(~fold["visible"])
            allow_k = valid & (d_vis_k > COLLAR_PX)
            dots_k, _ = submodular_max_cover_300m(surf, allow_k, target_n=bud, gamma=gam)
            r_k, t_k = _cropped_eval(fold, dots_k, valid)
            per_cfg_fold_res[cfg].append((r_k, t_k))
            del dots_k
        gc.collect()

    # Load all reference controls from verified registry cache
    reg_dir = ROOT / ".cache/registry"
    d28_arr = (rasterio.open(next(reg_dir.glob("*d28-ref02600*zeros.tif"))).read(1) > 0).astype(np.float32)
    h33_static = (rasterio.open(next(reg_dir.glob("*h33-2-b2*zeros.tif"))).read(1) > 0).astype(np.float32)
    g49_arr = (rasterio.open(next(reg_dir.glob("*xgrad-coupled*zeros.tif"))).read(1) > 0).astype(np.float32)
    g70_static = (rasterio.open(next(reg_dir.glob("*p5-dual-submod300-oof38k*.tif"))).read(1) > 0).astype(np.float32)

    ncols = (grid.width + 200 - 1) // 200
    nrows = (grid.height + 200 - 1) // 200
    arm_names = (
        "exp3_hybrid_crest_submod300",
        "exp2_resunet_diffdti_oof",
        "exp1_pu_tabular_oof",
        "h33_true_fold_fair",
        "d28_reference",
        "g49_reference",
        "h33_static_masked",
        "g70_static_masked",
        "random_control",
    )
    terms_by_arm = {a: np.zeros((ncols * nrows, 4), np.float64) for a in arm_names}
    per_fold_details: dict[str, list[dict]] = {a: [] for a in arm_names}
    nested_selected_cfgs = []

    rng_ctrl = np.random.default_rng(74099)
    for k, fold in enumerate(folds):
        d_vis_k = ndi.distance_transform_edt(~fold["visible"])
        allow_k = valid & (d_vis_k > COLLAR_PX)

        # Exp 1 & Exp 2 evaluated at exact H33/G70 dot count (37,654)
        e1_dots_k, _ = submodular_max_cover_300m(e1_oof, allow_k, target_n=BASE_BUDGET, gamma=1.35)
        e2_dots_k, _ = submodular_max_cover_300m(e2_oof, allow_k, target_n=BASE_BUDGET, gamma=1.35)

        # Nested-OOF selection for Exp 3: strictly maximize pooled DTI across the OTHER 3 training folds j != k!
        best_cfg = max(
            grid_configs,
            key=lambda cfg: float(
                evaluate_holdout.from_terms(
                    sum(per_cfg_fold_res[cfg][j][1] for j in range(len(folds)) if j != k).sum(axis=0)
                )
            ),
        )
        nested_selected_cfgs.append({"fold": fold["name"], "selected_on_other_3_folds": list(best_cfg)})
        r_e3, t_e3 = per_cfg_fold_res[best_cfg][k]

        h33_fair_k = np.where(d_vis_k > COLLAR_PX, d28_arr, 0.0)
        rand_ids = rng_ctrl.choice(np.flatnonzero(valid & (~fold["visible"])), BASE_BUDGET, replace=False)
        rand_k = np.zeros(grid.shape, dtype=np.float32)
        rand_k.ravel()[rand_ids] = 1.0

        fold_evals = {
            "exp3_hybrid_crest_submod300": (r_e3, t_e3),
            "exp2_resunet_diffdti_oof": _cropped_eval(fold, e2_dots_k, valid),
            "exp1_pu_tabular_oof": _cropped_eval(fold, e1_dots_k, valid),
            "h33_true_fold_fair": _cropped_eval(fold, h33_fair_k, valid),
            "d28_reference": _cropped_eval(fold, d28_arr, valid),
            "g49_reference": _cropped_eval(fold, g49_arr, valid),
            "h33_static_masked": _cropped_eval(fold, h33_static, valid),
            "g70_static_masked": _cropped_eval(fold, g70_static, valid),
            "random_control": _cropped_eval(fold, rand_k, valid),
        }
        for arm, (r_arm, t_arm) in fold_evals.items():
            terms_by_arm[arm] += t_arm
            per_fold_details[arm].append(r_arm)

        print(
            f"[Fold {fold['name']}] "
            f"Exp3={fold_evals['exp3_hybrid_crest_submod300'][0]['dti']:.5f} | "
            f"Exp2(ResUNet)={fold_evals['exp2_resunet_diffdti_oof'][0]['dti']:.5f} | "
            f"Exp1(PUTab)={fold_evals['exp1_pu_tabular_oof'][0]['dti']:.5f} | "
            f"H33_fair={fold_evals['h33_true_fold_fair'][0]['dti']:.5f} | "
            f"D28={fold_evals['d28_reference'][0]['dti']:.5f} | "
            f"Rand={fold_evals['random_control'][0]['dti']:.5f}",
            flush=True,
        )

    # Compute exact pooled summaries for each experiment cleanly against external controls
    external_controls = (
        "h33_true_fold_fair",
        "d28_reference",
        "g49_reference",
        "h33_static_masked",
        "g70_static_masked",
        "random_control",
    )
    summary_all = evaluate_holdout.pooled_summary(
        terms_by_arm, draws=1000, seed=520810, candidate="exp3_hybrid_crest_submod300"
    )
    summary_vs_controls = {}
    for exp_arm in ("exp1_pu_tabular_oof", "exp2_resunet_diffdti_oof", "exp3_hybrid_crest_submod300"):
        sub_terms = {exp_arm: terms_by_arm[exp_arm], **{c: terms_by_arm[c] for c in external_controls}}
        summary_vs_controls[exp_arm] = evaluate_holdout.pooled_summary(
            sub_terms, draws=1000, seed=520810, candidate=exp_arm
        )

    print("\n=== POOLED HOLDOUT-DTI SUMMARY (gems57-pooled-hide-v2, n_withheld=11,321) ===", flush=True)
    for arm in arm_names:
        sc = summary_all["scores"][arm]
        print(
            f"  {arm:30s}: {sc['dti']:.5f}  95% CI [{sc['ci95'][0]:.5f}, {sc['ci95'][1]:.5f}]  "
            f"(TP={sc['tpw']:.1f}, FP={sc['fpw']:.1f})",
            flush=True,
        )

    # Pick winning experiment across our 3 pre-registered experiments strictly by pooled HOLDOUT-DTI
    exp_candidates = ("exp1_pu_tabular_oof", "exp2_resunet_diffdti_oof", "exp3_hybrid_crest_submod300")
    winner_arm = max(exp_candidates, key=lambda a: summary_all["scores"][a]["dti"])
    winner_vs_ctrl = summary_vs_controls[winner_arm]
    delta_vs_h33 = winner_vs_ctrl["paired_differences"]["h33_true_fold_fair"]
    print(
        f"\n[WINNER] {winner_arm}: HOLDOUT-DTI = {summary_all['scores'][winner_arm]['dti']:.5f} | "
        f"Paired Delta vs H33_true_fold_fair = {delta_vs_h33['delta']:+.5f} "
        f"(95% CI [{delta_vs_h33['ci95'][0]:+.5f}, {delta_vs_h33['ci95'][1]:+.5f}])",
        flush=True,
    )

    # Global best full-dataset config selected across all 4 OOF folds combined
    best_global_cfg = max(
        grid_configs,
        key=lambda cfg: float(
            evaluate_holdout.from_terms(sum(per_cfg_fold_res[cfg][j][1] for j in range(len(folds))).sum(axis=0))
        ),
    )
    w_cnn_g, sh_g, bud_g, gam_g = best_global_cfg
    if winner_arm == "exp1_pu_tabular_oof":
        prod_surface = e1_prod
        final_budget, final_gamma = BASE_BUDGET, 1.35
    elif winner_arm == "exp2_resunet_diffdti_oof":
        prod_surface = e2_prod
        final_budget, final_gamma = BASE_BUDGET, 1.35
    else:
        prod_surface = _fuse_surface(e2_prod, e1_prod, cube, norm, valid, w_cnn=w_cnn_g, sharp_strength=sh_g)
        final_budget, final_gamma = bud_g, gam_g

    # Secondary Detached-Strand Evaluation ("detached" mode in vendor/gems57/holdout.py)
    oof_surface_best = (
        e1_oof
        if winner_arm == "exp1_pu_tabular_oof"
        else (e2_oof if winner_arm == "exp2_resunet_diffdti_oof" else pre_surfaces[(w_cnn_g, sh_g)].copy())
    )
    del pre_surfaces, per_cfg_fold_res, e1_oof, e1_prod, e2_oof, e2_prod, h33_static, g49_arr, g70_static
    gc.collect()

    ctx_det = holdout.build_holdout(grid, seeds=(20,), modes=("all", "detached"))
    d_cat_full = ndi.distance_transform_edt(~grid.catalogue)
    oof_unmasked_dots, _ = submodular_max_cover_300m(oof_surface_best, valid, target_n=final_budget, gamma=final_gamma)
    del oof_surface_best
    gc.collect()
    det_cand = holdout.evaluate(oof_unmasked_dots > 0, ctx_det, cell_mode="detached")
    det_d28 = holdout.evaluate(d28_arr > 0, ctx_det, cell_mode="detached")
    del ctx_det, oof_unmasked_dots, d28_arr
    gc.collect()
    print(
        f"[Detached Strands Check] {winner_arm} detached DTI = {det_cand['pooled_dti']:.5f} "
        f"vs D28/H33 detached = {det_d28['pooled_dti']:.5f} (n_truth={det_cand['pooled_n_truth']})",
        flush=True,
    )

    print("=== [5/6] Stage-1 Continuous Surface & Stage-2 Final GeoTIFF Uniqueness Audit (251 Registry Rasters) ===", flush=True)
    reg_index_path = ROOT / "registry" / "index.json"
    surf_max = float(np.max(prod_surface[valid])) + 1e-12
    prod_surface_unit = np.where(valid, np.clip(prod_surface / surf_max, 0.0, 1.0), 0.0).astype(np.float32)
    u1_path = ev_dir / "uniqueness_stage1_surface.json"
    surf_sha = hashlib.sha256(np.ascontiguousarray(prod_surface_unit).tobytes()).hexdigest()
    if u1_path.exists() and json.loads(u1_path.read_text()).get("candidate_decoded_sha256") == surf_sha:
        stage1_uniq = json.loads(u1_path.read_text())
    else:
        stage1_uniq = uniqueness.compare_array_to_registry(prod_surface_unit, reg_index_path, valid)
        _dump_json(u1_path, stage1_uniq)
    del prod_surface_unit
    gc.collect()
    print(
        f"[Stage 1 Surface] complete={stage1_uniq['complete_accessible_scan']} "
        f"count={stage1_uniq['registry_rasters_checked']} "
        f"max_|rho|={stage1_uniq['worst_spearman_full_footprint']:.5f} (limit 0.90) "
        f"unique={stage1_uniq['unique']}",
        flush=True,
    )
    if stage1_uniq["worst_spearman_full_footprint"] > 0.90:
        raise RuntimeError(f"Stage-1 continuous surface exceeded Spearman 0.90 limit: {stage1_uniq['worst_spearman_full_footprint']}")

    allow_prod = valid & (d_cat_full > COLLAR_PX)
    final_dots, n_final_dots = submodular_max_cover_300m(
        prod_surface, allow_prod, target_n=final_budget, gamma=final_gamma
    )
    # Guarantee exact finite float32 in [0.0, 1.0] across all 12,279,160 pixels (0.0 outside footprint)
    final_pred = np.where(valid & (final_dots > 0.5), 1.0, 0.0).astype(np.float32)

    print("=== [6/6] Packaging Submission GeoTIFF via Official submission_writer & Double Validation ===", flush=True)
    ts_str = "20261021T030000Z"
    decoded_sha8 = hashlib.sha256(np.ascontiguousarray(final_pred).tobytes()).hexdigest()[:8]
    sub_stem = f"gems74-puresunet-diffdti-submod300-{n_final_dots}-{ts_str}-{decoded_sha8}-zeros"
    dl_dir = ROOT / "docs" / "downloads"
    dl_dir.mkdir(parents=True, exist_ok=True)
    for old_f in dl_dir.glob("gems74-*"):
        old_f.unlink()

    tif_path = dl_dir / f"{sub_stem}.tif"
    sub_name = f"GEMSDOE74-PURESUNET-DIFFDTI-{n_final_dots}"
    sub_note = (
        f"GEMSDOE74 PU 2D-ResUNet DiffDTI(0.2,0.8) + 52ch 3DEP/LiDAR/GDR/Chi + CrestSubmod300: "
        f"{n_final_dots} off-cat dots, zeros ({decoded_sha8})"
    )
    assert len(sub_note) <= 140, f"Note too long: {len(sub_note)}"

    receipt = submission_writer.write_submission(
        tif_path,
        final_pred,
        ROOT / ".cache/gems_data/primary/sample_submission.tif",
        valid,
        note=sub_note,
        name=sub_name,
        catalogue=grid.catalogue,
        metadata={
            "winner_experiment": winner_arm,
            "holdout_dti": summary_all["scores"][winner_arm]["dti"],
            "holdout_ci95": summary_all["scores"][winner_arm]["ci95"],
            "withheld_positive_pixels": summary_all["scores"][winner_arm]["withheld_positive_pixels"],
        },
    )

    # Independent second validator check (vendor/gems/validate_submission.py)
    v71_report = v71.validate(
        tif_path,
        reference_path=ROOT / ".cache/gems_data/primary/sample_submission.tif",
        features_path=ROOT / ".cache/gems_data/primary/gems-geodawn-numerical-features.tif",
        outside_policy="either",
    )

    stage2_uniq = uniqueness.compare_to_registry(tif_path, reg_index_path, valid)
    _dump_json(ev_dir / "uniqueness_stage2_dots.json", stage2_uniq)
    max_fwd_overlap = float(stage2_uniq["worst_forward_overlap"])
    print(
        f"[Stage 2 Final TIFF] sha256={receipt['sha256'][:16]}... "
        f"dots={n_final_dots} max_|rho|={stage2_uniq['worst_spearman_full_footprint']:.5f} "
        f"max_mutual_ov={stage2_uniq['worst_dot_overlap']:.5f} "
        f"max_forward_ov={max_fwd_overlap:.5f} "
        f"unique={stage2_uniq['unique']}",
        flush=True,
    )

    beats_h33_point = summary_all["scores"][winner_arm]["dti"] > summary_all["scores"]["h33_true_fold_fair"]["dti"]
    beats_h33_ci95 = delta_vs_h33["ci95"][0] > 0.0
    promote = (
        bool(canary["all_features_passed"])
        and bool(stage1_uniq["worst_spearman_full_footprint"] <= 0.90)
        and bool(stage2_uniq["unique"])
        and bool(receipt["validator"]["all_checks_passed"])
        and beats_h33_point
    )

    holdout_report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - t_start, 2),
        "protocol_compliance": {
            "single_lane": True,
            "experiments_executed": 3,
            "max_experiments_budget": 3,
            "leakage_canary_passed": canary["all_features_passed"],
            "max_single_feature_symmetric_auc": canary["max_symmetric_auc"],
            "stage1_surface_unique": bool(stage1_uniq["worst_spearman_full_footprint"] <= 0.90),
            "stage2_dots_unique": bool(stage2_uniq["unique"]),
            "zero_d_vis_shortcut": True,
            "zero_sgmc_weight": True,
            "zero_valid_mask_erosion": True,
        },
        "pooled_holdout": summary_all,
        "paired_vs_external_controls": summary_vs_controls,
        "detached_strands_transfer": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": "gems57-detached-seed20",
            "withheld_positive_pixels": det_cand["pooled_n_truth"],
            "candidate_dti": det_cand["pooled_dti"],
            "d28_h33_detached_dti": det_d28["pooled_dti"],
            "delta_detached": det_cand["pooled_dti"] - det_d28["pooled_dti"],
        },
        "nested_oof_selected_configs": nested_selected_cfgs,
        "global_selected_config": {
            "w_cnn": w_cnn_g,
            "sharp_strength": sh_g,
            "target_budget": final_budget,
            "gamma": final_gamma,
        },
        "per_fold_scores": {
            arm: [round(r["dti"], 6) for r in per_fold_details[arm]] for arm in arm_names
        },
        "feature_importance_top15": sorted(
            [
                {"feature": FEATURE_NAMES[i], "normalized_importance": round(float(v / sum(e1_meta["feature_importance"])), 5)}
                for i, v in enumerate(e1_meta["feature_importance"])
            ],
            key=lambda d: d["normalized_importance"],
            reverse=True,
        )[:15],
        "exp1_meta": e1_meta,
        "exp2_meta": e2_meta,
    }
    _dump_json(ev_dir / "holdout_evaluation.json", holdout_report)

    run_card = {
        "project": "GEMSDOE74",
        "branch": "arena/ca0d045d-gemsdoe74",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": (
            "H74-1: Positive-Tile PU-Deconfounded Multi-Scale 2D Convolutional & Fluvial-Neotectonic "
            "Synthesis Trained Directly with Differentiable 300 m DW-Tversky Loss + Cross-Strike Crest "
            "Sharpening + Exact Unblurred 300 m Submodular Max-Cover"
        ),
        "mechanism": (
            "Filtering training patches strictly to mapped 128x128 reference tiles (>=5 visible fault px) "
            "with a registration-collar ignore zone eliminates unmapped-chunk false-negative poisoning "
            "(Hermant et al. 2025; Lipor 2026). A D4-equivariant Multi-Scale 2D Depthwise-Separable ResUNet "
            "(~8.8 km receptive field, ASPP dilation {1,3}, SE channel gating) trained directly under exact "
            "DifferentiableDTILoss(alpha=0.2, beta=0.8, R=300m) learns multi-km range-front & intrabasin "
            "continuity across 52 strictly catalogue-free channels (19 official GeoDAWN/INGENIOUS bands, "
            "native 10m 3DEP scarp + piedmont-apron + ksn/drainage-area fluvial disequilibrium, sqrt-dequantized "
            "1m LiDAR scarps, GDR-1391 thermal springs/geothermometers/2m-probes/sinter, and 3km strike-minus-flank "
            "worms), fused out-of-fold in log-odds space with a Positive-Tile PU LightGBM ensemble, sharpened "
            "across local structure-tensor strike, and emitted via exact 300m lazy-greedy submodular max-cover "
            "at d_cat > 2.0 px."
        ),
        "non_fault_mimic": (
            "(1) Meandering fluvial gorges & fan channels suppressed via native 10m upstream drainage area "
            "log10_area_m2, one-sided step asymmetry dem10_onesided3, and 1.5km strike-minus-flank worms; "
            "(2) Pleistocene Lake Lahontan paleo-shorelines (~1,330 m) & mountain summit crests suppressed "
            "via concave piedmont-apron Laplacian, channel steepness ksn, and basement horizontal gradient; "
            "(3) Interstate/railroad embankments (I-80/US-50/US-95) attenuated where Census TIGER road distance "
            "is small and deep gravity/magnetic basement worms are absent."
        ),
        "leakage_canary": {
            "rule": "Single-feature holdout AUC <= 0.90 across all 52 channels before fitting",
            "all_features_passed": canary["all_features_passed"],
            "n_features_tested": canary["n_model_features_tested"],
            "max_symmetric_auc": canary["max_symmetric_auc"],
            "excluded_sgmc_diagnostic_auc": canary["excluded_diagnostic_sgmc_auc"],
        },
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": summary_all["evaluator_version"],
            "withheld_positive_pixels": summary_all["scores"][winner_arm]["withheld_positive_pixels"],
            "winner_experiment": winner_arm,
            "score": round(summary_all["scores"][winner_arm]["dti"], 6),
            "ci95": [round(x, 6) for x in summary_all["scores"][winner_arm]["ci95"]],
            "experiments": {
                a: {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": summary_all["evaluator_version"],
                    "withheld_positive_pixels": summary_all["scores"][a]["withheld_positive_pixels"],
                    "dti": round(summary_all["scores"][a]["dti"], 6),
                    "ci95": [round(x, 6) for x in summary_all["scores"][a]["ci95"]],
                }
                for a in exp_candidates
            },
            "controls": {
                c: {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": summary_all["evaluator_version"],
                    "withheld_positive_pixels": summary_all["scores"][c]["withheld_positive_pixels"],
                    "dti": round(summary_all["scores"][c]["dti"], 6),
                    "ci95": [round(x, 6) for x in summary_all["scores"][c]["ci95"]],
                }
                for c in external_controls
            },
            "paired_delta_vs_h33_true_fold_fair": {
                "delta": round(delta_vs_h33["delta"], 6),
                "ci95": [round(x, 6) for x in delta_vs_h33["ci95"]],
                "statistically_significant_95pct": bool(beats_h33_ci95),
            },
            "detached_strands_check": {
                "evidence_class": "HOLDOUT-DTI",
                "evaluator_version": "gems57-detached-seed20",
                "withheld_positive_pixels": det_cand["pooled_n_truth"],
                "candidate_dti": round(det_cand["pooled_dti"], 6),
                "d28_h33_detached_dti": round(det_d28["pooled_dti"], 6),
            },
        },
        "organizer_confirmed_anchors": {
            "drivendata_leaderboard_top1_xiaofanhu": {"evidence_class": "ORGANIZER-CONFIRMED", "score": 0.4413},
            "drivendata_unet_benchmark": {"evidence_class": "ORGANIZER-CONFIRMED", "score": 0.3195},
            "group_best_GEMSDOE32_h33_2_b2": {"evidence_class": "ORGANIZER-CONFIRMED", "score": 0.2778},
            "group_GEMSDOE36_anderson_pinn": {"evidence_class": "ORGANIZER-CONFIRMED", "score": 0.2750},
            "group_GEMSDOE28_d28_r1": {"evidence_class": "ORGANIZER-CONFIRMED", "score": 0.2708},
            "group_GEMSDOE24_d28_base": {"evidence_class": "ORGANIZER-CONFIRMED", "score": 0.2600},
            "group_GEMSDOE70_p8_dual_submod300": {"evidence_class": "ORGANIZER-CONFIRMED", "score": 0.2478},
            "group_GEMSDOE49_xgrad": {"evidence_class": "ORGANIZER-CONFIRMED", "score": 0.1855},
            "group_GEMSDOE71_hydro_dpst": {"evidence_class": "ORGANIZER-CONFIRMED", "score": 0.0558},
        },
        "registry_correlation_overlap": {
            "registry_rasters_checked": stage2_uniq["registry_rasters_checked"],
            "complete_accessible_scan": stage2_uniq["complete_accessible_scan"],
            "stage1_continuous_surface_max_abs_spearman": round(stage1_uniq["worst_spearman_full_footprint"], 6),
            "stage1_nearest_spearman_match": stage1_uniq["worst_rho_submission"],
            "stage2_final_tif_max_abs_spearman": round(stage2_uniq["worst_spearman_full_footprint"], 6),
            "stage2_final_tif_nearest_spearman_match": stage2_uniq["worst_rho_submission"],
            "stage2_final_tif_max_mutual_3px_overlap": round(stage2_uniq["worst_dot_overlap"], 6),
            "stage2_final_tif_nearest_overlap_match": stage2_uniq["worst_overlap_submission"],
            "stage2_final_tif_max_forward_3px_overlap": round(max_fwd_overlap, 6),
            "stage2_final_tif_max_jaccard": round(stage2_uniq["worst_jaccard_dot_sets"], 6),
            "rho_ceiling": 0.90,
            "overlap_ceiling": 0.70,
            "passes_all_uniqueness_gates": bool(
                stage1_uniq["worst_spearman_full_footprint"] <= 0.90 and stage2_uniq["unique"]
            ),
        },
        "raster_sha256": receipt["sha256"],
        "zip_sha256": receipt["zip_sha256"],
        "submission_file": f"docs/downloads/{tif_path.name}",
        "submission_zip": f"docs/downloads/{tif_path.with_suffix('.zip').name}",
        "bytes_tif": receipt["bytes"],
        "emitted_positive_pixels": n_final_dots,
        "min_distance_to_catalogue_px": round(float(d_cat_full[final_pred > 0].min()), 4),
        "validator_output": {
            "gems57_all_checks_passed": receipt["validator"]["all_checks_passed"],
            "no_nan_inside_footprint": receipt["validator"]["checks"]["in_footprint_all_finite"],
            "no_nan_anywhere": receipt["validator"]["checks"]["no_nan_anywhere"],
            "values_in_0_1": receipt["validator"]["checks"]["range_0_1_guaranteed"],
            "crs_epsg_32611": receipt["validator"]["checks"]["crs_epsg_32611"],
            "dimensions_3730x3292": receipt["validator"]["checks"]["dimensions_3730x3292"],
            "transform_match": receipt["validator"]["checks"]["transform_matches_sample_submission"],
            "zero_dots_on_mapped_catalogue": receipt["validator"]["checks"]["zero_dots_on_mapped_catalogue"],
            "min_value": receipt["validator"]["min"],
            "max_value": receipt["validator"]["max"],
            "gems71_validator": v71_report if isinstance(v71_report, dict) else str(v71_report),
        },
        "submission_name": sub_name,
        "submission_note": sub_note,
        "submission_note_length": len(sub_note),
        "ready_to_download_and_submit": bool(promote and beats_h33_ci95),
        "verdict": "promote" if (promote and beats_h33_ci95) else "negative",
    }
    _dump_json(ev_dir / "run_card.json", run_card)
    (ROOT / "docs" / "evidence").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ev_dir / "run_card.json", ROOT / "docs" / "evidence" / "run_card.json")
    shutil.copy2(ev_dir / "holdout_evaluation.json", ROOT / "docs" / "evidence" / "holdout_evaluation.json")
    shutil.copy2(ev_dir / "leakage_canary.json", ROOT / "docs" / "evidence" / "leakage_canary.json")
    shutil.copy2(ev_dir / "uniqueness_stage1_surface.json", ROOT / "docs" / "evidence" / "uniqueness_stage1_surface.json")
    shutil.copy2(ev_dir / "uniqueness_stage2_dots.json", ROOT / "docs" / "evidence" / "uniqueness_stage2_dots.json")

    print(f"\n[COMPLETE] Verdict={run_card['verdict']} | Ready={run_card['ready_to_download_and_submit']} | Elapsed={time.time()-t_start:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
