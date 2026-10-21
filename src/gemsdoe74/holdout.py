"""Spatially-blocked hide-and-recover holdout.

Protocol (per brief):
- Withhold whole fault segments with a buffer, derive every catalogue-based feature only from visible faults, mask visible faults pixel-exactly, score pooled DTI (α0.2 β0.8 300m triangular kernel).
- Template cached feature stack, evaluate_holdout.py, submission_writer.py reused (no private fork).
- 4-fold quadrants (NE/NW/SE/SW) to prevent autocorrelation leakage.

Leakage canary: test each feature alone on holdout; AUC>0.90 flagged as leakage until proven otherwise.

These are legacy diagnostic helpers, NOT a buffered whole-segment evaluator. No automatic real-data pipeline exists.
"""
from __future__ import annotations
import numpy as np
from .metric import compute_dti, compute_dti_components

def create_spatial_block_folds(shape, valid_mask, n_rows=2, n_cols=2, seed=74):
    """4 quadrant folds (NW/NE/SW/SE). Returns list of (train_mask, val_mask)."""
    H, W = shape
    bh, bw = H//n_rows, W//n_cols
    folds = []
    for r in range(n_rows):
        for c in range(n_cols):
            val = np.zeros(shape, dtype=bool)
            r0, r1 = r*bh, (r+1)*bh if r < n_rows-1 else H
            c0, c1 = c*bw, (c+1)*bw if c < n_cols-1 else W
            val[r0:r1, c0:c1] = True
            val = val & valid_mask
            train = valid_mask & (~val)
            folds.append({"train":train,"val":val,"name":f"fold_{r}_{c}"})
    return folds

def hide_and_recover_scores(predictions, catalogue, hidden_truth, valid_mask, folds):
    """Score predictions against hidden_truth only (catalogue masked), per fold, pooling.

    catalogue: bool known faults (visible)
    hidden_truth: bool held-out positives (simulated hidden set)
    predictions: float/bianry emitted dots
    """
    results = []
    for f in folds:
        vm = f["val"] & valid_mask & ~np.asarray(catalogue, dtype=bool)
        # mask catalogue inside val (catalogue faults not counted)
        comp = compute_dti_components(predictions, hidden_truth, valid_mask=vm)
        # Also compute catalogue-masked version (FP on catalogue not penalized per staff clarification)
        # For synthetic we just report raw; staff clarification says catalogue pixels excluded from evaluation.
        results.append(comp["score"])
    return results

def bootstrap_ci(scores, n_bootstrap=1000, seed=0):
    rng = np.random.RandomState(seed)
    arr = np.array(scores)
    n = len(arr)
    if n==0: return (0.0,0.0)
    boots = [rng.choice(arr, size=n, replace=True).mean() for _ in range(n_bootstrap)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(lo), float(hi)

def leakage_canary(feature_stack: dict, labels: np.ndarray, valid_mask: np.ndarray):
    """Test each feature alone via AUC on valid pixels. Flag >0.90 as leakage.

    feature_stack: dict name→2D float array
    labels: bool truth
    """
    from sklearn.metrics import roc_auc_score
    canary = []
    flat_valid = valid_mask.ravel()
    y = labels.ravel()[flat_valid]
    for name, feat in feature_stack.items():
        x = feat.ravel()[flat_valid]
        # Missing classes/nonfinite values are not evidence of a safe feature.
        if len(y) == 0 or np.unique(y).size != 2 or not np.isfinite(x).all():
            canary.append({"feature": name, "auc": None, "flag_leakage": True,
                           "status": "invalid"})
            continue
        auc = float(roc_auc_score(y, x))
        canary.append({"feature": name, "auc": auc,
                       "flag_leakage": max(auc, 1 - auc) > 0.90,
                       "status": "measured"})
    return canary
