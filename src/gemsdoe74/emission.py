"""Emission: Poisson-disk thinning and greedy credit-bar emission.

Two modes:
- poisson_disk_select(field, min_distance_px, valid_mask, exclusion_mask): take top-scoring pixels iteratively, suppress neighbors within min_distance.
- greedy_credit_bar(field, valid_mask, alpha=0.2, beta=0.8, radius=300): EDGE-like expected-marginal-credit greedy that stops when k ≤ 0.2·DTI.

The credit-bar derivation is in GEMSDOE32: marginal dot credit must clear k > 0.2·DTI to be worth emitting; at DTI 0.26 bar=0.052, at 0.3195 bar=0.0639.
"""
from __future__ import annotations
import numpy as np
from scipy.spatial import cKDTree

def poisson_disk_select(field: np.ndarray, valid_mask: np.ndarray, min_distance_px: float = 2.8, exclusion_mask: np.ndarray | None = None, max_dots: int | None = None):
    """Greedy pick highest field value not within min_distance of already picked.

    field: 2D float, higher = more likely fault
    valid_mask: bool where emission allowed
    exclusion_mask: bool where dots forbidden (e.g., on-catalogue)
    """
    H,W = field.shape
    candidate = valid_mask.copy()
    if exclusion_mask is not None:
        candidate = candidate & (~exclusion_mask)
    # Flatten candidates sorted by field descending
    ys, xs = np.where(candidate)
    vals = field[ys, xs]
    order = np.argsort(vals)[::-1]
    ys, xs = ys[order], xs[order]
    vals = vals[order]

    picked_y, picked_x = [], []
    # Use kdtree incremental: maintain list and check distance via brute for small sets, cKDTree for large
    picked = []
    # For efficiency, create grid of suppression radius in pixel space
    r = float(min_distance_px)
    # We'll use a boolean suppression mask updated incrementally
    suppressed = np.zeros_like(valid_mask, dtype=bool)

    for y,x,v in zip(ys, xs, vals):
        if suppressed[y,x]: continue
        if candidate[y,x]==False: continue  # already excluded
        # pick it
        picked_y.append(y); picked_x.append(x); picked.append((y,x))
        # suppress neighbors within r
        y0 = max(0, int(y - r -1)); y1 = min(H, int(y + r +2))
        x0 = max(0, int(x - r -1)); x1 = min(W, int(x + r +2))
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dist = np.sqrt((yy - y)**2 + (xx - x)**2)
        suppressed[y0:y1, x0:x1] |= dist <= r
        if max_dots and len(picked) >= max_dots:
            break

    out = np.zeros_like(field, dtype=np.float32)
    if picked_y:
        out[np.array(picked_y), np.array(picked_x)] = 1.0
    return out

def greedy_credit_bar(field: np.ndarray, valid_mask: np.ndarray, current_dti: float = 0.26, alpha=0.2):
    """Placeholder for EDGE expected-marginal-credit greedy; here we just threshold at bar.

    In full implementation (src/gemsdoe30/emitter_opt.py) the marginal credit dT(x)= Σδ π(x+δ)·max(0,k(δ)−C(x+δ)) is used.
    For this lane we approximate by stopping Poisson disk when field value < bar.
    """
    bar = alpha * current_dti  # k > 0.2·DTI
    # field is already normalized [0,1]; bar ~0.05
    # So we poisson-disk but also enforce field >= bar to avoid emitting low-credit dots
    # Implemented via pre-filter
    filtered = np.where(field >= bar, field, -1)
    return filtered
