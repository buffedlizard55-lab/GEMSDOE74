"""Synthetic tests for the shared buffered-segment holdout engine.

These validate split/mask/metric mechanics only; no competition data, input
hash, geological feature, or real-data holdout score is represented here.
"""
import unittest

import numpy as np
from scipy.ndimage import distance_transform_edt, label

from scripts.evaluate_holdout_segments import (
    EVALUATOR_VERSION,
    compare_candidate_to_baseline,
    evaluate_holdout,
    quadrant_ids,
)


def synthetic_inputs():
    footprint = np.ones((80, 80), dtype=bool)
    catalogue = np.zeros_like(footprint)
    west = [3, 10, 17, 24, 31]
    east = [43, 50, 57, 64, 71]
    north = [3, 10, 17, 24, 31]
    south = [43, 50, 57, 64, 71]
    for rows, cols in ((north, west), (north, east), (south, west), (south, east)):
        for row, col in zip(rows, cols):
            catalogue[row : row + 2, col : col + 2] = True
    return footprint, catalogue


class BufferedSegmentHoldoutTests(unittest.TestCase):
    def test_reports_protocol_ci_and_whole_segment_counts(self):
        footprint, catalogue = synthetic_inputs()
        prediction = np.zeros(footprint.shape, dtype=np.float32)
        result = evaluate_holdout(
            footprint,
            catalogue,
            prediction=prediction,
            buffer_pixels=2,
            buffer_meters=200,
            draws=8,
            seed=19,
        )
        self.assertEqual(result["evaluator_version"], EVALUATOR_VERSION)
        self.assertEqual(result["label"], "HOLDOUT-DTI")
        self.assertEqual(result["point_estimate"], 0.0)
        self.assertEqual(len(result["confidence_interval_95_percent"]), 2)
        self.assertGreater(result["withheld_positive_count"], 0)
        self.assertEqual(len(result["withheld_positive_count_per_draw"]), 8)
        self.assertTrue(result["protocol"]["visible_faults_pixel_mask_exact"])
        self.assertTrue(result["protocol"]["catalogue_features_visible_only"])
        self.assertEqual(result["protocol"]["pooling"], "pooled")
        self.assertEqual(result["protocol"]["alpha"], 0.2)
        self.assertEqual(result["protocol"]["beta"], 0.8)
        self.assertEqual(result["protocol"]["kernel_meters"], 300.0)

    def test_catalogue_dependent_method_requires_builder_and_gets_buffered_mask(self):
        footprint, catalogue = synthetic_inputs()
        with self.assertRaisesRegex(ValueError, "fold-aware prediction_builder"):
            evaluate_holdout(
                footprint,
                catalogue,
                prediction=np.zeros(footprint.shape),
                catalogue_dependent=True,
                buffer_pixels=2,
                buffer_meters=200,
                draws=4,
            )

        q = quadrant_ids(footprint)
        seen = []

        def builder(visible_faults, fold, draw):
            block = q == fold
            collar = distance_transform_edt(~block) <= 2
            self.assertFalse(np.any(visible_faults & collar))
            seen.append((fold, draw, visible_faults.copy()))
            return np.zeros(footprint.shape, dtype=np.float32)

        result = evaluate_holdout(
            footprint,
            catalogue,
            prediction_builder=builder,
            catalogue_dependent=True,
            buffer_pixels=2,
            buffer_meters=200,
            draws=4,
        )
        self.assertEqual(len(seen), 16)
        self.assertTrue(result["protocol"]["catalogue_features_visible_only"])
        self.assertEqual(result["point_estimate"], 0.0)

    def test_same_baseline_comparison_does_not_pass(self):
        footprint, catalogue = synthetic_inputs()
        prediction = np.zeros(footprint.shape, dtype=np.float32)
        candidate = evaluate_holdout(footprint, catalogue, prediction=prediction, draws=4, seed=2)
        baseline = evaluate_holdout(footprint, catalogue, prediction=prediction, draws=4, seed=2)
        result = compare_candidate_to_baseline(candidate, baseline)
        self.assertEqual(result["paired_delta_mean"], 0.0)
        self.assertFalse(result["beats_current_holdout_best"])


if __name__ == "__main__":
    unittest.main()
