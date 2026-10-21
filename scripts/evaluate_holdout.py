#!/usr/bin/env python3
"""Fail-closed entry point for the required segment-buffered hide-and-recover test.

The former script hid random catalogue pixels in quadrants. That is not the required
whole-segment holdout with a spatial buffer, exact masking, visible-only catalogue
features, and pooled official DTI. Its output must not be reported as HOLDOUT-DTI.

This shared evaluator is deliberately blocked until its required inputs and correct
segment implementation are supplied; it does not create or overwrite evidence files.
"""
from __future__ import annotations
from pathlib import Path
import sys


def main() -> int:
    required = [
        Path("data/sample_submission.tif"),
        Path("data/training_features.tif"),
        Path("data/labels.tif"),
        Path("data/prepared_manifest.json"),
    ]
    missing = [str(path) for path in required if not path.is_file()]
    print("REFUSED: no holdout score was computed and no evidence file was changed.", file=sys.stderr)
    if missing:
        print("Missing official inputs:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
    print("Required before evaluation: whole fault-segment withholding plus buffer; derive "
          "catalogue features from visible segments only; mask visible faults pixel-exactly; "
          "pool DTI using alpha=0.2, beta=0.8 and a 300 m triangular kernel; run per-feature "
          "leakage canaries; compare the candidate and incumbent under identical folds; "
          "bootstrap a 95% CI.", file=sys.stderr)
    print("The old random-pixel quadrant proxy is not a valid substitute.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
