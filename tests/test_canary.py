"""Synthetic unit tests for the single-feature leakage-canary threshold.

No competition feature or catalogue was available; these tests do not claim to
have run a real-data leakage canary.
"""
import unittest

import numpy as np

from scripts.evaluate_holdout_segments import feature_auc_canary


class LeakageCanaryTests(unittest.TestCase):
    def test_strict_threshold_flags_auc_above_point_nine(self):
        truth = np.zeros((20, 20), dtype=bool)
        truth[2:8, 2:8] = True
        feature = truth.astype(np.float32)
        valid = np.ones_like(truth)
        known = np.zeros_like(truth)
        result = feature_auc_canary(feature, truth, valid, known, seed=7)
        self.assertEqual(result["auc"], 1.0)
        self.assertTrue(result["leakage_flag"])

    def test_auc_exactly_point_nine_is_not_flagged(self):
        feature = np.arange(20, dtype=np.float64).reshape(1, 20)
        truth = np.zeros((1, 20), dtype=bool)
        truth[0, [0, *range(11, 20)]] = True
        valid = np.ones_like(truth)
        known = np.zeros_like(truth)
        result = feature_auc_canary(feature, truth, valid, known, max_per_class=20)
        self.assertAlmostEqual(result["auc"], 0.90)
        self.assertFalse(result["leakage_flag"])

    def test_known_fault_pixels_are_excluded_exactly(self):
        truth = np.array([[True, False, False, False]])
        feature = np.array([[0.0, 100.0, 1.0, 2.0]])
        known = np.array([[False, True, False, False]])
        valid = np.ones_like(truth)
        result = feature_auc_canary(feature, truth, valid, known, max_per_class=10)
        self.assertEqual(result["positive_samples"], 1)
        self.assertEqual(result["negative_samples"], 1)
        self.assertFalse(result["leakage_flag"])


if __name__ == "__main__":
    unittest.main()
