import numpy as np
from gemsdoe74.metric import compute_dti_components, dti_from_counts, triangular_kernel

def test_worked_example():
    # From problem page: TPw=3.00 FPw=1.89 FNw=2.00 -> DTI 0.60 (rounded; exact 0.60265 with α0.2 β0.8 ε1e-7)
    assert abs(dti_from_counts(3.00,1.89,2.00)-0.60265) < 1e-4
    assert abs(dti_from_counts(3.00,1.89,2.00)-0.60) < 0.01

def test_triangular_kernel():
    assert triangular_kernel(0)==1.0
    assert triangular_kernel(150)==0.5
    assert triangular_kernel(300)==0.0
    assert triangular_kernel(400)==0.0

def test_dti_identity():
    # If predictions exactly match truth, DTI should be 1 (no FP/FN)
    truth=np.zeros((10,10),bool); truth[5,5]=True; truth[5,6]=True
    preds=np.zeros((10,10),np.float32); preds[5,5]=1; preds[5,6]=1
    comp=compute_dti_components(preds, truth)
    assert comp["score"]>0.9

def test_empty():
    truth=np.zeros((5,5),bool)
    preds=np.zeros((5,5),np.float32)
    comp=compute_dti_components(preds, truth)
    assert comp["score"]==1.0

def test_fractional_probability_weighting_ir74_30():
    # Single truth pixel predicted at p=0.5: TP=0.5, FP=0.0, FN=0.5 -> DTI = 0.5 / (0.5 + 0.8*0.5) = 5/9
    from gems74.metric import dti_exact
    truth = np.zeros((10, 10), bool)
    truth[5, 5] = True
    preds = np.zeros((10, 10), np.float32)
    preds[5, 5] = 0.5
    c1 = compute_dti_components(preds, truth, epsilon=1e-12)
    c2 = dti_exact(preds, truth)
    assert abs(c1["score"] - 5.0 / 9.0) < 1e-6
    assert abs(c1["score"] - c2["dti"]) < 1e-9

    # Random fractional grid equivalence between gemsdoe74.metric and gems74.metric
    rng = np.random.default_rng(74)
    p_rand = rng.uniform(0.0, 1.0, size=(30, 30)).astype(np.float32)
    t_rand = rng.random((30, 30)) < 0.08
    r1 = compute_dti_components(p_rand, t_rand, epsilon=1e-12)
    r2 = dti_exact(p_rand, t_rand)
    assert abs(r1["tp"] - r2["tp"]) < 1e-6
    assert abs(r1["fp"] - r2["fp"]) < 1e-6
    assert abs(r1["fn"] - r2["fn"]) < 1e-6
    assert abs(r1["score"] - r2["dti"]) < 1e-7
