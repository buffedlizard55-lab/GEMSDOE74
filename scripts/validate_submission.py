#!/usr/bin/env python3
"""Validate a candidate submission GeoTIFF against the competition format.

Usage:
    python scripts/validate_submission.py path/to/submission.tif
    python scripts/validate_submission.py path/to/submission.tif --footprint data/footprint.npy

Prints a JSON report and exits 0 only if every check passes.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from gems74.submission import validate_submission  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tif")
    ap.add_argument("--footprint", help=".npy bool array on the submission grid (True = inside footprint)")
    args = ap.parse_args()
    fp = np.load(args.footprint) if args.footprint else None
    report = validate_submission(args.tif, footprint=fp)
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
