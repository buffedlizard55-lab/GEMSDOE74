import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_readiness  # noqa: E402


class ReadinessAuditTests(unittest.TestCase):
    def test_checkout_is_fail_closed(self):
        report = check_readiness.audit(ROOT)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertFalse(report["download_enabled"])
        self.assertIsNone(report["download_url"])
        self.assertIsNone(report["submission_name"])
        self.assertTrue(report["blockers"])
        self.assertFalse(any(report["input_files_present"].values()))
        self.assertTrue(all(report["shared_tools_present"].values()))
        self.assertFalse(report["evidence_gates"].get("spatial_holdout", False))

    def test_manifest_cannot_bypass_missing_inputs_and_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / check_readiness.MANIFEST_REL
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps({
                "schema_version": "gemsdoe74-submission-manifest-v1",
                "status": "READY",
                "download_enabled": True,
                "artifact": {"path": "docs/downloads/not-a-real-submission.tif", "sha256": "0" * 64},
            }), encoding="utf-8")
            report = check_readiness.audit(root)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertFalse(report["download_enabled"])
            self.assertIsNone(report["download_url"])

    def test_high_leakage_auc_fails_canary(self):
        # The fixture tests only the gate rule; it is not an observed model result.
        receipt = {"passed": True, "features": [{"feature": "fixture", "auc": 0.91}]}
        self.assertFalse(check_readiness._leakage_canary_ok(receipt))

    def test_invalid_json_manifest_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / check_readiness.MANIFEST_REL
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text("{not valid json", encoding="utf-8")
            report = check_readiness.audit(root)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertFalse(report["download_enabled"])
            self.assertTrue(any("cannot be read as JSON" in x for x in report["blockers"]))


if __name__ == "__main__":
    unittest.main()
