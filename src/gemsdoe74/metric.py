"""Exact continuous Distance-Weighted Tversky Index (DTI) — verbatim from DrivenData Page 967.

Metric definition (DrivenData):
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric

Let p(x) in [0, 1] denote predicted probability, g(x) in {0, 1} ground truth.
Distance-weighted triangular kernel k(d) = max(1 - d / R, 0), R = 300 m (3 px at 100 m):

  TP_w = sum_{g in G} max_{x : d(x, g) <= R} p(x) * k(d(x, g))
  FP_w = sum_{x : p(x) > 0} p(x) * [1 - max_{g in G} k(d(x, g))]
  FN_w = sum_{g in G} [1 - max_{x : d(x, g) <= R} p(x) * k(d(x, g))] = |G| - TP_w

  DTI(alpha, beta) = TP_w / (TP_w + alpha * FP_w + beta * FN_w + eps)

Note (IR-74-30 fix): Earlier revisions erroneously thresholded `preds > 0.0` before scoring,
treating `p = 0.001` identically to `p = 1.0`. This implementation evaluates exact continuous
`p(x) * k(d(x, g))` over all offsets within `d <= R` and uses EDT acceleration automatically
when non-zero predictions are exact binary `{0, 1}`.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

DEFAULT_RADIUS_M = 300.0
DEFAULT_PIXEL_M = 100.0
DEFAULT_ALPHA = 0.2
DEFAULT_BETA = 0.8
DEFAULT_EPSILON = 1e-7


def triangular_kernel(d_m: float, R: float = DEFAULT_RADIUS_M) -> float:
    if d_m < 0:
        raise ValueError("distance must be non-negative")
    if R <= 0:
        raise ValueError("R must be positive")
    return float(max(0.0, 1.0 - d_m / R))


def dti_from_counts(
    tp: float,
    fp: float,
    fn: float,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    eps: float = 0.0,
) -> float:
    if min(tp, fp, fn) < 0:
        raise ValueError("counts must be non-negative")
    denom = tp + alpha * fp + beta * fn + eps
    return float(tp / denom) if denom > 0.0 else 0.0


def compute_dti_components(
    predictions: np.ndarray,
    ground_truth: np.ndarray,
    valid_mask: np.ndarray | None = None,
    radius_m: float = DEFAULT_RADIUS_M,
    pixel_m: float = DEFAULT_PIXEL_M,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    epsilon: float = 0.0,
) -> dict[str, float]:
    preds = np.asarray(predictions, dtype=np.float32)
    truth = np.asarray(ground_truth, dtype=bool)
    if preds.shape != truth.shape:
        raise ValueError(f"shape mismatch {preds.shape} != {truth.shape}")
    if np.any(np.isnan(preds)):
        raise ValueError("predictions contain NaN inside scored array")
    if np.any((preds < 0.0) | (preds > 1.0)):
        raise ValueError("predictions must lie in [0.0, 1.0]")

    if valid_mask is not None:
        mask = np.asarray(valid_mask, dtype=bool)
        preds = np.where(mask, preds, 0.0)
        truth = truth & mask

    pos_mask = preds > 0.0
    n_truth = float(np.count_nonzero(truth))
    pred_mass = float(np.sum(preds, dtype=np.float64))

    if n_truth == 0.0 and pred_mass == 0.0:
        return {"tp": 0.0, "fp": 0.0, "fn": 0.0, "score": 1.0}
    if n_truth == 0.0:
        return {"tp": 0.0, "fp": pred_mass, "fn": 0.0, "score": 0.0}
    if pred_mass == 0.0:
        return {"tp": 0.0, "fp": 0.0, "fn": n_truth, "score": 0.0}

    dist_to_truth_px = distance_transform_edt(~truth)
    fp_kernel = np.maximum(0.0, 1.0 - (dist_to_truth_px * pixel_m) / radius_m)
    fp = float(np.sum(preds[pos_mask] * (1.0 - fp_kernel[pos_mask]), dtype=np.float64))

    # Fast exact path when nonzero entries are strictly binary {0.0, 1.0}
    is_binary = bool(np.all(preds[pos_mask] == 1.0))
    if is_binary:
        dist_to_pred_px = distance_transform_edt(~pos_mask)
        kernel_on_truth = np.maximum(0.0, 1.0 - (dist_to_pred_px * pixel_m) / radius_m)
        tp = float(np.sum(kernel_on_truth[truth], dtype=np.float64))
    else:
        # Exact continuous max_{||x - g|| <= R} p(x) * k(||x - g||) over disk offsets
        r_px = int(np.floor(radius_m / pixel_m))
        ty, tx = np.nonzero(truth)
        H, W = preds.shape
        best = np.zeros(len(ty), dtype=np.float32)
        for dy in range(-r_px, r_px + 1):
            for dx in range(-r_px, r_px + 1):
                w = 1.0 - (np.hypot(dy, dx) * pixel_m) / radius_m
                if w <= 0.0:
                    continue
                yy = ty + dy
                xx = tx + dx
                ok = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
                if np.any(ok):
                    cand = preds[yy[ok], xx[ok]] * np.float32(w)
                    best[ok] = np.maximum(best[ok], cand)
        tp = float(np.sum(best, dtype=np.float64))

    fn = float(max(0.0, n_truth - tp))
    score = dti_from_counts(tp, fp, fn, alpha=alpha, beta=beta, eps=epsilon)
    return {"tp": tp, "fp": fp, "fn": fn, "score": score}


def compute_dti(predictions: np.ndarray, ground_truth: np.ndarray, valid_mask: np.ndarray | None = None, **kw) -> float:
    return compute_dti_components(predictions, ground_truth, valid_mask, **kw)["score"]
