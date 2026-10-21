#!/usr/bin/env python3
"""Fail-closed guard for submission generation.

The previous version generated a raster from synthetic geological-looking fields and
could label it a submission. That is not a valid competition prediction. This command
intentionally writes no file until an official feature stack, a real C1 model, and a
validated holdout implementation are available.

Use src/gemsdoe74/submission.py only after those prerequisites have been met. The
synthetic helpers remain available for unit tests/education and must never be used to
create a competition submission.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=Path("data/sample_submission.tif"))
    parser.add_argument("--out", type=Path, default=Path("docs/downloads"))
    parser.add_argument("--lane", default="c1-flightline-magnetic-edge")
    parser.add_argument("--allow-synthetic-demo", action="store_true",
                        help="Deprecated: never creates a submission; retained to explain old invocations.")
    args = parser.parse_args()

    required = [
        args.template,
        Path("data/training_features.tif"),
        Path("data/labels.tif"),
        Path("data/prepared_manifest.json"),
    ]
    missing = [str(path) for path in required if not path.is_file()]
    print("REFUSED: no competition GeoTIFF was written.", file=sys.stderr)
    if missing:
        print("Missing required official inputs:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
    print("The C1 model, cached-feature provenance, segment-buffered holdout, leakage canary, "
          "and same-holdout incumbent comparison are not implemented/verified.", file=sys.stderr)
    print("Do not use the synthetic feature generators or inherited docs/downloads TIFs as "
          "competition predictions.", file=sys.stderr)
    print("Acquire authorized official data, implement and validate the real method, then "
          "update this guard with the verified production pipeline.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
