"""Verification of the distance-weighted Tversky index implementation.

Sources of truth:
  * Published definition and worked example:
    https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
  * Hand-computed cases below (arithmetic shown in each test).
  * A literal brute-force reference implementation (no vectorisation) is used
    to cross-check the fast implementation on random grids.
"""

import itertools
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --- shim: adapt the shared metric (src/gems74/metric.py) to the names used by these tests.
from src.gems74.metric import dti_exact as _dti_exact, kernel as _kernel_px  # noqa: E402


class metric:  # noqa: N801  (namespace shim; keeps test bodies unchanged)
    @staticmethod
    def kernel(d_m):
        return float(_kernel_px(np.asarray(d_m, dtype=float) / 100.0))

    @staticmethod
    def components(pred, truth):
        r = _dti_exact(pred, truth)
        return {"TP_w": r["tp"], "FP_w": r["fp"], "FN_w": r["fn"], "G": r["n_truth"], "DTI": r["dti"]}

    @staticmethod
    def dti(pred, truth):
        return _dti_exact(pred, truth)["dti"]




def brute_force_components(p, g, R_m=300.0, px=100.0, alpha=0.2, beta=0.8):
    """Literal transcription of the published formulas (O(N^2)); reference only."""
    H, W = p.shape
    truth = [(i, j) for i in range(H) for j in range(W) if g[i, j]]
    pred = [(i, j) for i in range(H) for j in range(W) if p[i, j] > 0]

    def k(a, b):
        d = math.hypot(a[0] - b[0], a[1] - b[1]) * px
        return max(1.0 - d / R_m, 0.0)

    TP = sum(max([p[x] * k(x, gg) for x in pred] + [0.0]) for gg in truth)
    FN = sum(1.0 - max([p[x] * k(x, gg) for x in pred] + [0.0]) for gg in truth)
    FP = sum(p[x] * (1.0 - max([k(x, gg) for gg in truth] + [0.0])) for x in pred)
    dti = TP / (TP + alpha * FP + beta * FN + 1e-12)
    return TP, FP, FN, dti


def _single_truth(H=9, W=9, centre=(4, 4)):
    g = np.zeros((H, W), bool)
    g[centre] = True
    return g


def test_published_worked_example_arithmetic():
    # Published example: TP_w=3.00, FP_w=1.89, FN_w=2.00 -> TI_w = 0.60
    ti = 3.00 / (3.00 + 0.2 * 1.89 + 0.8 * 2.00)
    assert ti == pytest.approx(0.60, abs=0.01)


def test_kernel_values():
    assert metric.kernel(0.0) == pytest.approx(1.0)
    assert metric.kernel(100.0) == pytest.approx(2.0 / 3.0)
    assert metric.kernel(200.0) == pytest.approx(1.0 / 3.0)
    assert metric.kernel(300.0) == pytest.approx(0.0)
    assert metric.kernel(500.0) == pytest.approx(0.0)


def test_perfect_prediction_scores_one():
    g = _single_truth()
    p = g.astype(float)
    c = metric.components(p, g)
    assert c["TP_w"] == pytest.approx(1.0)
    assert c["FP_w"] == pytest.approx(0.0)
    assert c["FN_w"] == pytest.approx(0.0)
    assert c["DTI"] == pytest.approx(1.0, abs=1e-9)


def test_half_confidence_on_truth():
    # TP=0.5, FN=0.5, FP=0 -> 0.5 / (0.5 + 0.8*0.5) = 0.5 / 0.9
    g = _single_truth()
    p = np.zeros_like(g, float)
    p[4, 4] = 0.5
    c = metric.components(p, g)
    assert c["TP_w"] == pytest.approx(0.5)
    assert c["FN_w"] == pytest.approx(0.5)
    assert c["FP_w"] == pytest.approx(0.0)
    assert c["DTI"] == pytest.approx(0.5 / 0.9, abs=1e-9)


def test_neighbour_at_100m():
    # Predict 1.0 one pixel east (d=100 m): k=2/3
    # TP=2/3, FN=1/3, FP=1*(1-2/3)=1/3 -> DTI = (2/3)/(2/3 + 0.2/3 + 0.8/3) = 2/3
    g = _single_truth()
    p = np.zeros_like(g, float)
    p[4, 5] = 1.0
    c = metric.components(p, g)
    assert c["TP_w"] == pytest.approx(2.0 / 3.0)
    assert c["FN_w"] == pytest.approx(1.0 / 3.0)
    assert c["FP_w"] == pytest.approx(1.0 / 3.0)
    assert c["DTI"] == pytest.approx(2.0 / 3.0, abs=1e-9)


def test_200m_away_earns_one_third():
    # k(200 m)=1/3: TP=1/3, FN=2/3, FP=2/3 -> DTI=(1/3)/(1/3 + 2/3) = 1/3
    g = _single_truth()
    p = np.zeros_like(g, float)
    p[4, 6] = 1.0
    c = metric.components(p, g)
    assert c["TP_w"] == pytest.approx(1.0 / 3.0)
    assert c["DTI"] == pytest.approx(1.0 / 3.0, abs=1e-9)


def test_300m_away_earns_nothing():
    # d = R exactly: kernel 0, so the prediction is a pure false positive.
    g = _single_truth()
    p = np.zeros_like(g, float)
    p[4, 7] = 1.0
    c = metric.components(p, g)
    assert c["TP_w"] == pytest.approx(0.0)
    assert c["FP_w"] == pytest.approx(1.0)
    assert c["DTI"] == pytest.approx(0.0, abs=1e-9)


def test_empty_prediction_scores_zero():
    g = _single_truth()
    assert metric.dti(np.zeros_like(g, float), g) == pytest.approx(0.0, abs=1e-9)


def test_no_truth_pixels():
    p = np.zeros((9, 9))
    p[0, 0] = 0.7
    c = metric.components(p, np.zeros((9, 9), bool))
    assert c["G"] == 0
    assert c["FP_w"] == pytest.approx(0.7)
    assert c["DTI"] == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_fast_matches_brute_force_on_random_grids(seed):
    rng = np.random.default_rng(seed)
    H, W = 14, 13
    g = rng.random((H, W)) < 0.08
    p = np.where(rng.random((H, W)) < 0.3, rng.random((H, W)), 0.0)
    fast = metric.components(p, g)
    TP, FP, FN, dti = brute_force_components(p, g)
    assert fast["TP_w"] == pytest.approx(TP, rel=1e-9, abs=1e-9)
    assert fast["FP_w"] == pytest.approx(FP, rel=1e-9, abs=1e-9)
    assert fast["FN_w"] == pytest.approx(FN, rel=1e-9, abs=1e-9)
    assert fast["DTI"] == pytest.approx(dti, rel=1e-9, abs=1e-9)
    assert fast["TP_w"] + fast["FN_w"] == pytest.approx(fast["G"])


def test_rejects_out_of_range_and_nan():
    g = _single_truth()
    with pytest.raises(ValueError):
        metric.dti(np.full(g.shape, 1.5), g)
    with pytest.raises(ValueError):
        metric.dti(np.full(g.shape, -0.1), g)
    bad = np.zeros(g.shape)
    bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        metric.dti(bad, g)


def test_shape_mismatch():
    with pytest.raises(ValueError):
        metric.dti(np.zeros((3, 3)), np.zeros((3, 4), bool))
