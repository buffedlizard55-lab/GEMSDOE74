"""Distance-weighted Tversky index (DTI) for the DOE GEMS Prize.

Implements the published definition from the competition problem page
(https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/):

    k(d)   = max(1 - d / R, 0),   R = 300 m (3 px at 100 m)
    TP_w   = sum_g  max_x  p(x) k(d(x,g))            (over truth pixels g)
    FP_w   = sum_x  p(x) [1 - max_g k(d(x,g))]        (over pixels with p > 0)
    FN_w   = sum_g  [1 - max_x p(x) k(d(x,g))]        (over truth pixels g)
    DTI    = TP_w / (TP_w + alpha*FP_w + beta*FN_w + eps),  alpha=0.2, beta=0.8

Pixel distances are Euclidean on the 100 m grid. Only pixels whose distance is
strictly below R contribute to the max (the kernel is zero at d >= R).

This module is the single metric implementation for this repository. It has no
dependency on any other project's code. Verification: tests/test_metric.py.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

ALPHA = 0.2
BETA = 0.8
PIXEL_M = 100.0
R_M = 300.0
EPS = 1e-12


def kernel(distance_m):
    """Triangular kernel k(d) = max(1 - d/R, 0)."""
    d = np.asarray(distance_m, dtype=float)
    return np.maximum(1.0 - d / R_M, 0.0)


def _neighbourhood(radius_px: int):
    """(dy, dx, k) for every offset with non-zero kernel weight."""
    out = []
    for dy in range(-radius_px, radius_px + 1):
        for dx in range(-radius_px, radius_px + 1):
            d = math.hypot(dx, dy) * PIXEL_M
            k = float(kernel(d))
            if k > 0.0:
                out.append((dy, dx, k))
    return out


def _check_prediction(pred: np.ndarray) -> np.ndarray:
    p = np.asarray(pred, dtype=float)
    if p.ndim != 2:
        raise ValueError(f"prediction must be 2-D, got shape {p.shape}")
    if not np.all(np.isfinite(p)):
        raise ValueError("prediction contains NaN or inf; set outside-footprint cells to 0 before scoring")
    if p.min() < 0.0 or p.max() > 1.0:
        raise ValueError(f"prediction values must lie in [0, 1]; got [{p.min()}, {p.max()}]")
    return p


def components(pred, truth, alpha: float = ALPHA, beta: float = BETA):
    """Return a dict with TP_w, FP_w, FN_w, G (truth pixel count) and DTI."""
    p = _check_prediction(pred)
    g = np.asarray(truth).astype(bool)
    if g.shape != p.shape:
        raise ValueError(f"shape mismatch: pred {p.shape} vs truth {g.shape}")

    radius = int(math.ceil(R_M / PIXEL_M))  # 3 px
    H, W = p.shape
    padded = np.pad(p, radius, mode="constant", constant_values=0.0)

    # best[i, j] = max over neighbours x of p(x) * k(d(x, (i, j)))
    best = np.zeros_like(p)
    for dy, dx, k in _neighbourhood(radius):
        shifted = padded[radius + dy: radius + dy + H, radius + dx: radius + dx + W]
        np.maximum(best, shifted * k, out=best)

    G = int(g.sum())
    TP = float(best[g].sum())
    FN = float((1.0 - best[g]).sum())

    # FP: each predicted mass is penalised by (1 - k(distance to nearest truth)).
    if G == 0:
        FP = float(p.sum())
    else:
        dist_px = ndimage.distance_transform_edt(~g)
        k_nearest = kernel(dist_px * PIXEL_M)
        FP = float((p * (1.0 - k_nearest)).sum())

    dti = TP / (TP + alpha * FP + beta * FN + EPS)
    return {"TP_w": TP, "FP_w": FP, "FN_w": FN, "G": G, "DTI": dti}


def dti(pred, truth, alpha: float = ALPHA, beta: float = BETA) -> float:
    """Distance-weighted Tversky index for a probability raster against a binary truth raster."""
    return components(pred, truth, alpha=alpha, beta=beta)["DTI"]
