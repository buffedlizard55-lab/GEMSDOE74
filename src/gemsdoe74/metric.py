"""Exact distance-weighted Tversky Index (DTI) — verbatim from problem page 967.

Metric definition (DrivenData): https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric

Let p(x)∈[0,1] denote predicted probability, g(x)∈{0,1} ground truth.
Tversky TI(α,β)= Σp g / [ Σp g + α Σ p(1-g) + β Σ (1-p) g ]
Distance-weighted via triangular kernel k(d)=max(1−d/R,0), R=300m (3px at 100m):

  TPw = Σ_{g∈G} max_{x:d(x,g)≤R} p(x) k(d(x,g))
  FPw = Σ_{x:p(x)>0} p(x)[1−max_{g∈G} k(d(x,g))]
  FNw = Σ_{g∈G}[1−max_{x:d(x,g)≤R} p(x) k(d(x,g))]

DTI(α,β)= TPw / (TPw + α FPw + β FNw + ε)

For this competition α=0.2, β=0.8, R=300m, ε=1e-7.
Worked example in problem page: TPw=3.00 FPw=1.89 FNw=2.00 → DTI=3/(3+0.2·1.89+0.8·2)=0.60
This implementation reproduces that example (tested).

References:
- Problem page: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric
- Tversky index: https://en.wikipedia.org/wiki/Tversky_index
- CRS: https://epsg.io/32611
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
    if d_m < 0: raise ValueError("distance must be non-negative")
    if R <= 0: raise ValueError("R must be positive")
    return max(0.0, 1.0 - d_m / R)

def dti_from_counts(tp: float, fp: float, fn: float, alpha=DEFAULT_ALPHA, beta=DEFAULT_BETA, eps=DEFAULT_EPSILON) -> float:
    if min(tp, fp, fn) < 0: raise ValueError("counts must be non-negative")
    return float(tp / (tp + alpha*fp + beta*fn + eps))

def _offsets(radius_px: float):
    r = int(np.ceil(radius_px))
    out = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = float(np.hypot(dy, dx))
            if d < radius_px:
                out.append((dy, dx, 1.0 - d / radius_px))
    return out

_DEFAULT_OFFS = _offsets(DEFAULT_RADIUS_M / DEFAULT_PIXEL_M)

def compute_dti_components(predictions: np.ndarray, ground_truth: np.ndarray, valid_mask=None,
                          known_mask=None,
                          radius_m=DEFAULT_RADIUS_M, pixel_m=DEFAULT_PIXEL_M,
                          alpha=DEFAULT_ALPHA, beta=DEFAULT_BETA, epsilon=DEFAULT_EPSILON):
    preds = np.asarray(predictions, dtype=np.float64)
    truth = np.asarray(ground_truth, dtype=bool)
    if preds.shape != truth.shape:
        raise ValueError(f"shape mismatch {preds.shape} != {truth.shape}")
    active = np.ones(preds.shape, dtype=bool)
    if valid_mask is not None:
        active &= np.asarray(valid_mask, dtype=bool)
    if known_mask is not None:
        active &= ~np.asarray(known_mask, dtype=bool)
    vals = preds[active]
    if not np.isfinite(vals).all() or (vals < 0.0).any() or (vals > 1.0).any():
        raise ValueError("predictions inside active domain must be finite and in [0, 1]")
    p = np.where(active & np.isfinite(preds), preds, 0.0)
    g = truth & active
    n_truth = float(np.count_nonzero(g))
    pos_mask = p > 0.0
    n_pred_mass = float(p[pos_mask].sum())
    if n_truth == 0.0 and n_pred_mass == 0.0:
        return {"tp": 0.0, "fp": 0.0, "fn": 0.0, "n_truth": 0, "score": 1.0}
    if n_truth == 0.0:
        return {"tp": 0.0, "fp": n_pred_mass, "fn": 0.0, "n_truth": 0, "score": 0.0}
    if n_pred_mass == 0.0:
        return {"tp": 0.0, "fp": 0.0, "fn": n_truth, "n_truth": int(n_truth), "score": 0.0}

    radius_px = float(radius_m) / float(pixel_m)
    is_binary = bool(np.all((p == 0.0) | (p == 1.0)))
    if is_binary:
        pred_bin = pos_mask
        dist_to_pred_px = distance_transform_edt(~pred_bin)
        kernel_on_truth = np.maximum(0.0, 1.0 - dist_to_pred_px / radius_px)
        tp = float(np.sum(kernel_on_truth[g]))
    else:
        H, W = p.shape
        yy, xx = np.nonzero(g)
        credit = np.zeros(yy.size, dtype=np.float64)
        offs = _DEFAULT_OFFS if abs(radius_px - 3.0) < 1e-9 else _offsets(radius_px)
        for dy, dx, k_val in offs:
            ny, nx = yy + dy, xx + dx
            ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
            credit[ok] = np.maximum(credit[ok], p[ny[ok], nx[ok]] * k_val)
        tp = float(credit.sum())

    dist_to_truth_px = distance_transform_edt(~g)
    fp_kernel = np.maximum(0.0, 1.0 - dist_to_truth_px / radius_px)
    fp = float(np.sum(p[pos_mask] * (1.0 - fp_kernel[pos_mask])))
    fn = float(max(0.0, n_truth - tp))
    score = dti_from_counts(tp, fp, fn, alpha=alpha, beta=beta, eps=epsilon)
    return {"tp": tp, "fp": fp, "fn": fn, "n_truth": int(n_truth), "score": score}

def compute_dti(predictions, ground_truth, valid_mask=None, **kw):
    return compute_dti_components(predictions, ground_truth, valid_mask, **kw)["score"]
