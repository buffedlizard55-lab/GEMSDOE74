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
