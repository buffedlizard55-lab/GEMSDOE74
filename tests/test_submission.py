"""Synthetic unit tests for the shared sample-grid validator.

These tests do not validate competition data or an actual submission artifact.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

from scripts.validate_submission import validate_submission

ROOT = Path(__file__).resolve().parents[1]


class SubmissionValidatorTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.sample = self.root / "sample_submission.tif"
        self.candidate = self.root / "candidate.tif"
        self.transform = Affine(100, 0, 243350, 0, -100, 4508550)
        self.crs = "EPSG:32611"
        sample = np.ones((12, 10), dtype=np.float32)
        sample[:2, :2] = np.nan
        profile = {
            "driver": "GTiff", "height": 12, "width": 10, "count": 1,
            "dtype": "float32", "crs": self.crs, "transform": self.transform,
            "nodata": float("nan"),
        }
        with rasterio.open(self.sample, "w", **profile) as dst:
            dst.write(sample, 1)
        self.profile = dict(profile, nodata=None)

    def tearDown(self):
        self.tempdir.cleanup()

    def write_candidate(self, values=None, *, transform=None, crs=None, nodata=None, dtype="float32"):
        if values is None:
            values = np.zeros((12, 10), dtype=np.float32)
        else:
            values = np.asarray(values, dtype=dtype)
        profile = dict(
            self.profile,
            dtype=dtype,
            transform=transform or self.transform,
            crs=crs or self.crs,
            nodata=nodata,
        )
        with rasterio.open(self.candidate, "w", **profile) as dst:
            dst.write(values, 1)

    def test_matching_finite_in_range_file_passes_format_only(self):
        self.write_candidate()
        report = validate_submission(self.candidate, self.sample)
        self.assertTrue(report["passed"])
        self.assertTrue(report["format_scope_only"])
        self.assertFalse(report["submission_eligible"])
        self.assertTrue(report["checks"]["shape_match"])
        self.assertTrue(report["checks"]["crs_match"])
        self.assertTrue(report["checks"]["transform_match"])

    def test_wrong_transform_fails(self):
        self.write_candidate(transform=Affine(100, 0, 243450, 0, -100, 4508550))
        report = validate_submission(self.candidate, self.sample)
        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["transform_match"])

    def test_nan_and_out_of_range_values_fail(self):
        values = np.zeros((12, 10), dtype=np.float32)
        values[4, 4] = np.nan
        report = None
        self.write_candidate(values)
        report = validate_submission(self.candidate, self.sample)
        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["no_nan_inside_footprint"])
        values[4, 4] = 1.01
        self.write_candidate(values)
        report = validate_submission(self.candidate, self.sample)
        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["all_values_in_allowed_range"])

    def test_nodata_is_rejected(self):
        self.write_candidate(nodata=-9999)
        report = validate_submission(self.candidate, self.sample)
        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["no_nodata_value"])

    def test_all_nan_file_fails_with_json_safe_receipt(self):
        values = np.full((12, 10), np.nan, dtype=np.float32)
        self.write_candidate(values)
        report = validate_submission(self.candidate, self.sample)
        self.assertFalse(report["passed"])
        self.assertIsNone(report["details"]["inside_min"])
        import json
        json.dumps(report, allow_nan=False)

    def test_legacy_generator_is_blocked_by_default(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_submission.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("blocked by default", result.stderr)
        self.assertFalse(list((ROOT / "outputs").rglob("*.tif")) if (ROOT / "outputs").exists() else False)


if __name__ == "__main__":
    unittest.main()
