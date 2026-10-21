#!/usr/bin/env python3
"""Disabled legacy holdout proxy.

The former evaluator hid randomly selected catalogue pixels in four quadrants. It did
not withhold whole fault segments with a buffer, rebuild catalogue-derived features,
or implement the required exact scored-domain masking. Its outputs are not valid
HOLDOUT-DTI and must not be used for candidate selection.
"""
import sys


def main() -> int:
    print("BLOCKED: legacy pixel-random/quadrant proxy is not a valid holdout evaluator.", file=sys.stderr)
    print("Implement the required segment-with-buffer hide-and-recover evaluator before scoring candidates.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
