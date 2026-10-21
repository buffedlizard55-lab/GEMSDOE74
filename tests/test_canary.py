"""Unit tests for leakage_canary; these are not real-data leakage results."""
import numpy as np

from gemsdoe74.holdout import hide_and_recover_scores, leakage_canary
import pytest


def test_canary_flags_a_feature_that_encodes_the_labels():
    labels = np.zeros((20, 20), dtype=bool)
    labels[::2, ::2] = True
    mask = np.ones_like(labels, dtype=bool)

    result = leakage_canary({"deliberate_label_copy": labels.astype(float)}, labels, mask)

    assert len(result) == 1
    assert result[0]["auc"] == 1.0
    assert result[0]["flag_leakage"] is True


def test_canary_does_not_flag_independent_deterministic_feature():
    labels = np.zeros((20, 20), dtype=bool)
    labels[::2, ::2] = True
    mask = np.ones_like(labels, dtype=bool)
    # Feature varies spatially but is independent of the checkerboard labels.
    feature = np.random.RandomState(17).normal(size=labels.shape)

    result = leakage_canary({"independent_noise": feature}, labels, mask)

    assert len(result) == 1
    assert result[0]["auc"] < 0.90
    assert result[0]["flag_leakage"] is False


def test_legacy_holdout_helper_fails_closed():
    with pytest.raises(NotImplementedError, match="No compliant holdout evaluator"):
        hide_and_recover_scores(None, None, None, None, None)
