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

def compute_dti_components(predictions: np.ndarray, ground_truth: np.ndarray, valid_mask=None,
                          radius_m=DEFAULT_RADIUS_M, pixel_m=DEFAULT_PIXEL_M,
                          alpha=DEFAULT_ALPHA, beta=DEFAULT_BETA, epsilon=DEFAULT_EPSILON):
    # One canonical implementation; never silently threshold soft probabilities.
    from gems74.metric import dti_exact
    if radius_m != DEFAULT_RADIUS_M or pixel_m != DEFAULT_PIXEL_M:
        raise ValueError("Only the competition 300 m / 100 m kernel is supported")
    result = dti_exact(predictions, ground_truth, valid=valid_mask, alpha=alpha, beta=beta)
    tp, fp, fn = result["tp"], result["fp"], result["fn"]
    # Preserve the historical API's empty/empty convention for compatibility.
    score = 1.0 if tp == fp == fn == 0 else dti_from_counts(tp, fp, fn, alpha, beta, epsilon)
    return {"tp": tp, "fp": fp, "fn": fn, "score": score}

def compute_dti(predictions, ground_truth, valid_mask=None, **kw):
    return compute_dti_components(predictions, ground_truth, valid_mask, **kw)["score"]
