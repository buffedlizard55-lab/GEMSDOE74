"""Check the marginal-credit rule used in docs/analysis-0-2778.html (section 3).

Claim: adding one isolated pixel with p=1 that earns kernel credit c against an
otherwise-uncovered truth pixel changes the Tversky denominator
(TP + 0.2 FP + 0.8 FN) by exactly +0.2, because c + 0.2(1-c) - 0.8c = 0.2.
Therefore DTI' > DTI  iff  c > 0.2 * DTI.

Construction (so that the threshold can discriminate):
  * truth = 6 isolated pixels, spaced >= 8 px apart;
  * base prediction fully covers 5 of them (p = 1) and leaves the 6th (anchor) uncovered;
  * base carries false-positive mass M on far-away pixels (>= 4 px from any truth);
  * the candidate pixel sits 1-3 px from the anchor only (>= 3 px from all other truth).
Varying M moves the base DTI, and varying the offset moves c, so both outcomes occur.

This checks algebra on synthetic grids. It is NOT a claim about any geological feature.
"""

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



H, W = 60, 60
TRUTH = [(10, 10), (10, 30), (30, 10), (30, 30), (50, 50), (45, 15)]
# candidate offsets from the anchor, all within the 300 m (3 px) kernel
OFFSETS = [(0, 1), (1, 1), (2, 0), (2, 1), (2, 2)]  # all within 3 px; (2,2) is 2.83 px
FP_MASS_PIXELS = [0, 20, 40, 60, 80, 100]  # number of far pixels carrying p = 0.5


def _case(off_idx: int, mass_idx: int):
    g = np.zeros((H, W), bool)
    for i, j in TRUTH:
        g[i, j] = True
    anchor = TRUTH[-1]  # left uncovered
    off = OFFSETS[off_idx]
    cand = (anchor[0] + off[0], anchor[1] + off[1])

    base = np.zeros((H, W))
    for t in TRUTH[:-1]:
        base[t] = 1.0

    def far(i, j):
        d_truth = min(np.hypot(i - a, j - b) for a, b in TRUTH)
        return d_truth >= 4 and np.hypot(i - cand[0], j - cand[1]) >= 4

    n_needed = FP_MASS_PIXELS[mass_idx]
    placed = 0
    for i in range(H):
        for j in range(W):
            if placed < n_needed and far(i, j):
                base[i, j] = 0.5
                placed += 1
    assert placed == n_needed, "grid too small for requested FP mass"

    new = base.copy()
    new[cand] = 1.0
    return g, base, new


CASES = [(o, m) for o in range(len(OFFSETS)) for m in range(len(FP_MASS_PIXELS))]


@pytest.mark.parametrize("off_idx,mass_idx", CASES)
def test_denominator_moves_by_exactly_0_2(off_idx, mass_idx):
    g, base, new = _case(off_idx, mass_idx)
    cb = metric.components(base, g)
    cn = metric.components(new, g)
    c = cn["TP_w"] - cb["TP_w"]
    assert c > 0.0
    den_b = cb["TP_w"] + 0.2 * cb["FP_w"] + 0.8 * cb["FN_w"]
    den_n = cn["TP_w"] + 0.2 * cn["FP_w"] + 0.8 * cn["FN_w"]
    assert den_n - den_b == pytest.approx(0.2, abs=1e-9)


@pytest.mark.parametrize("off_idx,mass_idx", CASES)
def test_dti_rises_iff_credit_exceeds_0_2_times_dti(off_idx, mass_idx):
    g, base, new = _case(off_idx, mass_idx)
    cb = metric.components(base, g)
    cn = metric.components(new, g)
    c = cn["TP_w"] - cb["TP_w"]
    assert c > 0.0
    rises = cn["DTI"] > cb["DTI"] + 1e-12
    assert rises == (c > 0.2 * cb["DTI"])


def test_both_outcomes_are_exercised():
    outcomes = set()
    for off_idx, mass_idx in CASES:
        g, base, new = _case(off_idx, mass_idx)
        cb = metric.components(base, g)
        cn = metric.components(new, g)
        outcomes.add(cn["DTI"] > cb["DTI"] + 1e-12)
    assert outcomes == {True, False}, "test would be vacuous if one outcome never occurs"


def test_break_even_credit_at_quoted_scores():
    # 0.2 * s at the scores quoted in the research notes (labelled as arithmetic, not as scores)
    assert 0.2 * 0.2778 == pytest.approx(0.05556, abs=1e-5)
    assert 0.2 * 0.4413 == pytest.approx(0.08826, abs=1e-5)
