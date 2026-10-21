#!/usr/bin/env python3
"""
Segment-based holdout evaluation (proper hide-and-recover with whole fault segments).
Mimics GEMSDOE32 holdout.py: per quadrant, hide 20% of fault segments that touch test quadrant,
with 1.5km collar (disabled in this lightweight version for speed), scorer = DTI pooled.
"""
import pathlib, json, numpy as np, rasterio
from scipy.ndimage import label, distance_transform_edt, binary_dilation
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src.gems74.metric import dti_binary

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = pathlib.Path("/tmp/gems74_data")

def quadrant_ids(foot):
    yy,xx=np.nonzero(foot)
    ym,xm=int(np.median(yy)), int(np.median(xx))
    H,W=foot.shape
    gy,gx=np.ogrid[:H,:W]
    q=np.full((H,W), -1, dtype=np.int8)
    q[(gy<ym)&(gx<xm)&foot]=0
    q[(gy<ym)&(gx>=xm)&foot]=1
    q[(gy>=ym)&(gx<xm)&foot]=2
    q[(gy>=ym)&(gx>=xm)&foot]=3
    return q

def evaluate_segments(pred_mask, foot, cat, sgmc_off=None):
    comp, ncomp = label(cat, structure=np.ones((3,3)))
    q = quadrant_ids(foot)
    per_fold = {}
    for fold in range(4):
        test_region = q==fold
        # components touching test region
        touch = np.unique(comp[test_region & cat])
        touch = touch[touch!=0]
        rng = np.random.default_rng(74+fold)
        n_hide = max(1, int(0.20*len(touch)))
        hide_ids = rng.choice(touch, size=n_hide, replace=False)
        hidden = np.isin(comp, hide_ids)  # truth in this fold
        # Visible = catalogue not hidden
        visible = cat & ~hidden
        # Active = footprint & ~visible & test_region (scored domain)
        active = foot & ~visible & test_region
        # Truth = hidden & active (hidden should be inside test_region, so already)
        truth = hidden & active
        n_truth = truth.sum()
        pred = pred_mask & active
        # Skip if no truth
        if n_truth==0:
            per_fold[f"fold_{fold}"] = {"dti":0,"tp":0,"fp":float(pred.sum()),"fn":0,"n_truth":0}
            continue
        res = dti_binary(pred, truth, valid=active, known=np.zeros_like(active))
        per_fold[f"fold_{fold}"] = res
        if sgmc_off is not None:
            # SGMC off-catalogue truth within this quadrant's active
            sg_truth = sgmc_off & test_region & active
            # But sgmc_off already excludes near-cat, so visible mask not needed
            # Ensure sg_truth inside active
            if sg_truth.sum()>0:
                sg_res = dti_binary(pred, sg_truth, valid=active, known=np.zeros_like(active))
                per_fold[f"fold_{fold}_sgmc"] = sg_res
    # Pooled
    pooled_tp = sum(v["tp"] for k,v in per_fold.items() if "sgmc" not in k)
    pooled_fp = sum(v["fp"] for k,v in per_fold.items() if "sgmc" not in k)
    pooled_fn = sum(v["fn"] for k,v in per_fold.items() if "sgmc" not in k)
    pooled_dti = pooled_tp / (pooled_tp + 0.2*pooled_fp + 0.8*pooled_fn + 1e-12)
    # SGMC pooled
    sg_tp = sum(v["tp"] for k,v in per_fold.items() if "sgmc" in k)
    sg_fp = sum(v["fp"] for k,v in per_fold.items() if "sgmc" in k)
    sg_fn = sum(v["fn"] for k,v in per_fold.items() if "sgmc" in k)
    sg_dti = sg_tp / (sg_tp + 0.2*sg_fp + 0.8*sg_fn + 1e-12) if (sg_tp+sg_fn)>0 else 0
    return per_fold, pooled_dti, sg_dti

def main():
    foot = np.isfinite(rasterio.open(DATA/"sample_submission.tif").read(1))
    cat = rasterio.open(DATA/"labels.tif").read(1)>0
    # SGMC off
    with rasterio.open(DATA/"external/derived_sgmc_faults_100m_u8.tif") as src:
        sgmc = src.read(1)>0
    near_cat = binary_dilation(cat, iterations=3)
    sgmc_off = sgmc & ~cat & ~near_cat & foot
    print(f"sgmc_off {sgmc_off.sum()} cat {cat.sum()} foot {foot.sum()}")

    cand_path = "docs/downloads/gems74-h74-alt-spring-39500-20261021T000000Z-52f76038-zeros.tif"
    with rasterio.open(cand_path) as src:
        cand = src.read(1)>0
    # Random control same budget
    rng = np.random.default_rng(0)
    foot_not_cat = foot & ~cat
    rr,cc = np.nonzero(foot_not_cat)
    idx = rng.choice(len(rr), size=int(cand.sum()), replace=False)
    random_mask = np.zeros_like(cand, dtype=bool)
    random_mask[rr[idx], cc[idx]] = True
    # Also incumbent proxy: D28-like? For reference, use random but with low density? We'll just compare cand vs random
    for name, mask in [("H74-A", cand), ("random", random_mask)]:
        per_fold, pooled, sg_pooled = evaluate_segments(mask, foot, cat, sgmc_off)
        print(f"\n{name}: pooled CAT DTI={pooled:.5f} SGMC DTI={sg_pooled:.5f}")
        for k,v in per_fold.items():
            if "sgmc" not in k:
                print(f"  {k}: DTI {v['dti']:.4f} tp {v['tp']:.1f} fp {v['fp']:.1f} fn {v['fn']:.1f} n={v['n_truth']}")
            else:
                print(f"  {k}: DTI {v['dti']:.4f} (SGMC) tp {v['tp']:.1f}")

    # Save evidence
    per_fold_cand, pooled_cand, sg_cand = evaluate_segments(cand, foot, cat, sgmc_off)
    per_fold_rand, pooled_rand, sg_rand = evaluate_segments(random_mask, foot, cat, sgmc_off)
    evid = {
        "evaluator": "segment-based hide-and-recover 4-quadrant, hide 20% segments per fold, no collar, pooled DTI alpha0.2 beta0.8 R3px (proxy for GEMSDOE32 holdout.py)",
        "candidate": {"file": cand_path, "pixels": int(cand.sum()), "pooled_DTI_cat": pooled_cand, "pooled_DTI_sgmc": sg_cand, "per_fold": per_fold_cand},
        "random_control": {"pixels": int(random_mask.sum()), "pooled_DTI_cat": pooled_rand, "pooled_DTI_sgmc": sg_rand, "per_fold": per_fold_rand},
        "delta_cat": pooled_cand - pooled_rand,
        "delta_sgmc": sg_cand - sg_rand,
        "passes_random_cat": bool(pooled_cand > pooled_rand),
        "passes_random_sgmc": bool(sg_cand > sg_rand),
        "note": "HOLDOUT-DTI (evaluator v0.2 segment-based, 4 folds, ~12k hidden truth total). No ORGANIZER-CONFIRMED score. Holdout truth is catalogue only, so it cannot reward genuinely new faults (IR-32-PROXY-01)."
    }
    with open(ROOT/"evidence/holdout_h74a_segments.json","w") as f:
        json.dump(evid, f, indent=2)
    print("\nwrote evidence/holdout_h74a_segments.json")

if __name__ == "__main__":
    main()
