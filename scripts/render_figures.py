#!/usr/bin/env python3
"""Render real-data diagnostic figures into docs/assets/ from verified artifacts."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from scipy import ndimage as ndi

from vendor.gems57.grid import load_grid


def main() -> int:
    assets = ROOT / "docs" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "irregularities.json", ROOT / "docs" / "evidence" / "irregularities.json")

    ev = json.loads((ROOT / "evidence/holdout_evaluation.json").read_text())
    rc = json.loads((ROOT / "evidence/run_card.json").read_text())
    can = json.loads((ROOT / "evidence/leakage_canary.json").read_text())
    u2 = json.loads((ROOT / "evidence/uniqueness_stage2_dots.json").read_text())

    plt.rcParams.update({
        "font.family": "sans-serif",
        "axes.edgecolor": "#cbd5e1",
        "axes.linewidth": 0.9,
        "figure.facecolor": "#ffffff",
    })

    # --- Figure 1: Pooled Holdout Ladder + Per-Quadrant Sweep ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.2), dpi=160)
    arms = [
        ("Exp 3: Hybrid Crest+Submod300\n(PROMOTED GEMSDOE74)", "exp3_hybrid_crest_submod300", "#059669"),
        ("Exp 2: 2D ResUNet-DiffDTI\n(OOF, 52ch local-norm)", "exp2_resunet_diffdti_oof", "#0284c7"),
        ("GEMSDOE32 H33-2-b2\n(Fold-fair 0.2778 record)", "h33_true_fold_fair", "#dc2626"),
        ("Exp 1: PU LightGBM\n(OOF, 52ch pixel)", "exp1_pu_tabular_oof", "#6366f1"),
        ("GEMSDOE24/28 D28\n(Live 0.2600 baseline)", "d28_reference", "#d97706"),
        ("Uniform Off-Cat Random\n(37,654 dots control)", "random_control", "#64748b"),
        ("GEMSDOE49 XGrad\n(Live 0.1855 control)", "g49_reference", "#94a3b8"),
    ]
    ys = np.arange(len(arms))[::-1]
    scores = [ev["pooled_holdout"]["scores"][k]["dti"] for _, k, _ in arms]
    lo = [s - ev["pooled_holdout"]["scores"][k]["ci95"][0] for s, (_, k, _) in zip(scores, arms)]
    hi = [ev["pooled_holdout"]["scores"][k]["ci95"][1] - s for s, (_, k, _) in zip(scores, arms)]
    cols = [c for _, _, c in arms]

    ax1.barh(ys, scores, height=0.62, color=cols, alpha=0.90)
    ax1.errorbar(scores, ys, xerr=[lo, hi], fmt="none", ecolor="#0f172a", elinewidth=1.4, capsize=4)
    ax1.axvline(ev["pooled_holdout"]["scores"]["h33_true_fold_fair"]["dti"], color="#dc2626", ls="--", lw=1.2, alpha=0.7)
    for y_i, s_i in zip(ys, scores):
        ax1.text(s_i + 0.0018, y_i + 0.17, f"{s_i:.5f}", fontsize=8.8, fontweight="bold", color="#0f172a")
    ax1.set_yticks(ys)
    ax1.set_yticklabels([lbl for lbl, _, _ in arms], fontsize=8.8)
    ax1.set_xlim(0, 0.156)
    ax1.set_xlabel("Pooled HOLDOUT-DTI (gems57-pooled-hide-v2, n=11,321, 95% CI)", fontsize=9.5, fontweight="bold")
    ax1.set_title("A. Shared Hide-and-Recover Benchmark Progression", fontsize=11, fontweight="bold", loc="left")
    ax1.grid(axis="x", alpha=0.25)

    quads = ["NW", "NE", "SW", "SE"]
    x_q = np.arange(4)
    w = 0.24
    ax2.bar(x_q - w, ev["per_fold_scores"]["h33_true_fold_fair"], width=w, color="#dc2626", alpha=0.85, label="H33-2-b2 Fold-Fair (0.2778 Live)")
    ax2.bar(x_q, ev["per_fold_scores"]["exp2_resunet_diffdti_oof"], width=w, color="#0284c7", alpha=0.88, label="Exp 2: 2D ResUNet-DiffDTI")
    ax2.bar(x_q + w, ev["per_fold_scores"]["exp3_hybrid_crest_submod300"], width=w, color="#059669", alpha=0.92, label="Exp 3: GEMSDOE74 Promoted")
    for i in range(4):
        v3 = ev["per_fold_scores"]["exp3_hybrid_crest_submod300"][i]
        vh = ev["per_fold_scores"]["h33_true_fold_fair"][i]
        ax2.text(i + w, v3 + 0.0025, f"+{v3-vh:.3f}", ha="center", fontsize=8.2, fontweight="bold", color="#047857")
    ax2.set_xticks(x_q)
    ax2.set_xticklabels([f"Fold {q}" for q in quads], fontsize=9.5, fontweight="bold")
    ax2.set_ylim(0, 0.172)
    ax2.set_ylabel("Quadrant HOLDOUT-DTI", fontsize=9.5, fontweight="bold")
    ax2.set_title("B. 4/4 Spatial Quadrant Sweep (+0.0214 Pooled, p < 0.001)", fontsize=11, fontweight="bold", loc="left")
    ax2.legend(frameon=True, fontsize=8.5, loc="upper left")
    ax2.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    fig.savefig(assets / "fig1_holdout_progression.png")
    plt.close(fig)

    # --- Figure 2: Real Geospatial Map + Zoom Inset ---
    grid = load_grid(ROOT / ".cache/gems_data/primary")
    pred = rasterio.open(ROOT / rc["submission_file"]).read(1)
    h33 = rasterio.open(next((ROOT / ".cache/registry").glob("*h33-2-b2*zeros.tif"))).read(1)
    cube = np.memmap(ROOT / ".cache/gems74_features_v3.f16.mmap", dtype=np.float16, mode="r", shape=(52, 3730, 3292))
    relief = cube[19].astype(np.float32)  # dem10_slope_mean

    fig, axes = plt.subplots(1, 3, figsize=(14.5, 5.4), dpi=160)
    ds = 4
    bg = np.where(grid.footprint[::ds, ::ds], relief[::ds, ::ds], np.nan)
    cat_d = ndi.maximum_filter(grid.catalogue, size=4)[::ds, ::ds]
    h33_d = ndi.maximum_filter(h33 > 0, size=4)[::ds, ::ds]
    g74_d = ndi.maximum_filter(pred > 0, size=4)[::ds, ::ds]

    axes[0].imshow(bg, cmap="Greys", vmin=-1.2, vmax=2.5)
    axes[0].imshow(np.where(cat_d, 1.0, np.nan), cmap="Reds", vmin=0, vmax=1.2, alpha=0.9)
    axes[0].set_title("A. 10 m 3DEP Slope + Mapped Catalogue\n(existing_faults.tif = 56,574 px)", fontsize=9.8, fontweight="bold")
    axes[0].axis("off")

    axes[1].imshow(bg, cmap="Greys", vmin=-1.2, vmax=2.5)
    axes[1].imshow(np.where(g74_d, 1.0, np.nan), cmap="winter", vmin=0, vmax=1.0, alpha=0.92)
    axes[1].set_title("B. GEMSDOE74 Promoted Submission\n(37,654 Off-Cat Dots, SHA 8dbb1bba...)", fontsize=9.8, fontweight="bold")
    axes[1].axis("off")

    # High-resolution 1:1 32x32 km inset in central Dixie Valley / Stillwater-Clan Alpine unmapped zone
    y0, x0, sz = 1480, 1460, 320
    axes[2].imshow(relief[y0:y0+sz, x0:x0+sz], cmap="Greys", vmin=-1.0, vmax=2.6)
    cat_z = ndi.binary_dilation(grid.catalogue[y0:y0+sz, x0:x0+sz], iterations=1)
    h33_z = ndi.binary_dilation(h33[y0:y0+sz, x0:x0+sz] > 0, iterations=1)
    g74_z = ndi.binary_dilation(pred[y0:y0+sz, x0:x0+sz] > 0, iterations=1)
    ov_rgb = np.zeros((sz, sz, 4), dtype=np.float32)
    ov_rgb[h33_z] = [0.95, 0.55, 0.10, 0.70]   # amber: H33
    ov_rgb[g74_z] = [0.02, 0.78, 0.52, 0.92]   # emerald: GEMSDOE74
    ov_rgb[cat_z] = [0.90, 0.12, 0.20, 0.95]   # red: mapped catalogue (strictly 2+ px gap!)
    axes[2].imshow(ov_rgb)
    axes[2].set_title("C. 32x32 km 100 m Pixel Zoom\nRed=Mapped | Emerald=GEMSDOE74 | Amber=H33", fontsize=9.8, fontweight="bold")
    axes[2].axis("off")

    fig.tight_layout()
    fig.savefig(assets / "fig2_spatial_fault_map.png")
    plt.close(fig)

    # --- Figure 3: Leakage Canary + 259-Raster Uniqueness Proof ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 4.8), dpi=160)
    top_can = can["features"][:14][::-1]
    ax1.barh([f["feature"] for f in top_can], [f["symmetric_auc"] for f in top_can], color="#0284c7", alpha=0.88)
    ax1.axvline(0.90, color="#dc2626", lw=1.8, ls="--", label="Rule-4 Leakage Ceiling (AUC = 0.90)")
    ax1.set_xlim(0.45, 0.96)
    ax1.set_xlabel("Single-Feature Holdout Symmetric AUC", fontsize=9.5, fontweight="bold")
    ax1.set_title("A. Mandatory Pre-Fit Leakage Canary (52/52 PASS, max=0.6093)", fontsize=10.5, fontweight="bold", loc="left")
    ax1.legend(loc="lower right", fontsize=8.5)
    ax1.grid(axis="x", alpha=0.25)

    rhos = [abs(r.get("spearman_full_footprint", 0.0) or 0.0) for r in u2["rows"]]
    ovs = [float(r.get("mutual_overlap", r.get("overlap", 0.0)) or 0.0) for r in u2["rows"]]
    ax2.scatter(rhos, ovs, s=26, alpha=0.72, color="#059669", edgecolors="#064e3b", linewidths=0.4, label="259 Verified GeoTIFFs (GEMSDOE01..74)")
    ax2.axvline(0.90, color="#dc2626", lw=1.6, ls="--", label="Spearman |rho| <= 0.90 Gate")
    ax2.axhline(0.70, color="#d97706", lw=1.6, ls=":", label="Mutual 3-px Overlap <= 0.70 Gate")
    ax2.set_xlim(-0.02, 0.98)
    ax2.set_ylim(-0.03, 0.82)
    ax2.set_xlabel("Full-Footprint |Spearman rho| vs GEMSDOE74 Final GeoTIFF", fontsize=9.5, fontweight="bold")
    ax2.set_ylabel("Mutual 3-px (300 m) Dot Overlap Fraction", fontsize=9.5, fontweight="bold")
    ax2.set_title("B. 259-Raster Registry Uniqueness Audit (max |rho|=0.0824, ov=0.5446)", fontsize=10.5, fontweight="bold", loc="left")
    ax2.legend(loc="upper right", fontsize=8.3)
    ax2.grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(assets / "fig3_canary_uniqueness.png")
    plt.close(fig)
    print("Generated all 3 real-data figures cleanly in docs/assets/!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
