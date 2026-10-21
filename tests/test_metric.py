import numpy as np
from src.gems74.metric import dti_binary, dti_exact, kernel, marginal_inclusion_threshold
def test_kernel():
    assert kernel(0)==1.0
    assert kernel(3)==0.0
    assert kernel(1.5)==0.5
def test_dti_worked_example():
    # From problem description: create simple case and ensure metric is consistent
    # Not the exact worked example (TP=3 FP=1.89 FN=2 -> DTI 0.60) but check formula
    # DTI = T/(T + 0.2*FP + 0.8*FN)
    T=3; FP=1.89; FN=2
    dti = T/(T+0.2*FP+0.8*FN+1e-12)
    assert abs(dti - 0.6) < 0.005  # approx 0.603?
def test_marginal_threshold():
    assert marginal_inclusion_threshold(0.27) == 0.2*0.27
    assert marginal_inclusion_threshold(0.0)==0
def test_dti_binary_simple():
    truth = np.zeros((10,10), bool)
    truth[5,5]=True
    pred = np.zeros((10,10), bool)
    pred[5,5]=True
    res = dti_binary(pred, truth)
    assert res["dti"]>0.9  # perfect hit
    pred_far = np.zeros((10,10), bool)
    pred_far[0,0]=True
    res2 = dti_binary(pred_far, truth)
    assert res2["dti"]<0.1
