#!/usr/bin/env python3
"""Fail-closed entry point for competition submission generation.

The previous implementation generated synthetic features, catalogue labels, and hidden
positives, then wrote fabricated evaluation/registry fields into its run card. It was
not a competition model. It has been disabled so it cannot accidentally produce or
promote another synthetic TIFF. Use the writer only after a real-data model and the
required holdout evaluator are implemented and validated against official inputs.
"""
import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default="docs/downloads",
        help="Reserved for a future validated submission writer; generation is currently blocked.",
    )
    parser.add_argument("--template", help="Official sample-submission GeoTIFF; required by a future pipeline.")
    parser.add_argument("--lane", default="h74-1")
    parser.add_argument("--seed", type=int, default=74)
    parser.add_argument("--min_dist", type=float, default=2.8)
    parser.parse_args()

    print("BLOCKED: no competition prediction was generated.", file=sys.stderr)
    print(
        "This repository lacks the authorized official feature stack, labels, and sample template; "
        "the legacy implementation synthesized all of these and hard-coded holdout/canary/registry fields.",
        file=sys.stderr,
    )
    print(
        "Implement and validate a real-data model plus the segment-with-buffer holdout protocol before enabling generation.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
