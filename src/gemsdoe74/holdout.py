"""Experimental holdout helpers — NOT the required competition evaluator.

`create_spatial_block_folds` only makes a simple quadrant partition. It does not
withhold complete fault segments plus a buffer. The former `hide_and_recover_scores`
helper scored synthetic/proxy truth without the required visible-only feature rebuild
and exact mask semantics; it now fails closed. Do not report its historical values as
HOLDOUT-DTI. A compliant evaluator must be implemented against authorized official
fault segment data and the organizer metric before candidate selection.

`leakage_canary` is retained as a generic helper and unit-tested on toy arrays. Running
it on toy arrays is not a real-data leakage assessment.
"""
from __future__ import annotations
import numpy as np


def create_spatial_block_folds(shape, valid_mask, n_rows=2, n_cols=2, seed=74):
    """Return a simple rectangular partition for software experiments only.

    This is not a segment-based holdout and must not be labeled as one.
    """
    H, W = shape
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if valid_mask.shape != shape:
        raise ValueError("valid_mask shape mismatch")
    if n_rows < 1 or n_cols < 1:
        raise ValueError("fold grid must be positive")
    bh, bw = H // n_rows, W // n_cols
    folds = []
    for r in range(n_rows):
        for c in range(n_cols):
            val = np.zeros(shape, dtype=bool)
            r0, r1 = r * bh, (r + 1) * bh if r < n_rows - 1 else H
            c0, c1 = c * bw, (c + 1) * bw if c < n_cols - 1 else W
            val[r0:r1, c0:c1] = True
            val &= valid_mask
            folds.append({"train": valid_mask & ~val, "val": val, "name": f"fold_{r}_{c}"})
    return folds


def hide_and_recover_scores(*args, **kwargs):
    """Prevent accidental reporting from the former invalid proxy evaluator."""
    raise NotImplementedError(
        "No compliant holdout evaluator is implemented. Required: whole-segment withholding, "
        "buffer, visible-only catalogue feature rebuild, exact masking, and pooled official DTI."
    )


def bootstrap_ci(scores, n_bootstrap=1000, seed=0):
    """Bootstrap a numeric array for unit experiments only; not an evaluator CI by itself."""
    rng = np.random.RandomState(seed)
    arr = np.asarray(scores, dtype=float)
    if arr.size == 0:
        return (0.0, 0.0)
    boots = [rng.choice(arr, size=arr.size, replace=True).mean() for _ in range(n_bootstrap)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(lo), float(hi)


def leakage_canary(feature_stack: dict, labels: np.ndarray, valid_mask: np.ndarray):
    """Compute feature-wise ROC AUC on the supplied arrays; toy-only unless data are real."""
    from sklearn.metrics import roc_auc_score

    labels = np.asarray(labels, dtype=bool)
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if labels.ndim != 2 or labels.shape != valid_mask.shape:
        raise ValueError("labels and valid_mask must be same-shaped 2-D arrays")
    y = labels[valid_mask]
    if y.size == 0 or y.all() or (~y).all():
        raise ValueError("canary needs both classes inside valid_mask")
    canary = []
    for name, feat in feature_stack.items():
        x = np.asarray(feat)
        if x.shape != labels.shape:
            raise ValueError(f"feature {name!r} shape mismatch")
        scores = x[valid_mask]
        if not np.isfinite(scores).all():
            raise ValueError(f"feature {name!r} has non-finite values inside valid_mask")
        auc = float(roc_auc_score(y, scores))
        canary.append({"feature": name, "auc": auc, "flag_leakage": auc > 0.90})
    return canary
