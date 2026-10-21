#!/usr/bin/env python3
"""Historical noncompliant evaluator, disabled until buffered fold-local evaluation exists.

The earlier implementation selected random catalogue pixels and evaluated a precomputed
raster. It did not withhold whole fault segments plus a buffer or regenerate fold-local
catalogue features. Running it as a score-producing tool would be misleading.
"""
import sys


def main() -> int:
    print("BLOCKED: no holdout score was computed and no evidence file was changed. "
          "Implement the required whole-segment buffer, visible-only feature derivation, "
          "pixel-exact masking, pooled DTI, leakage canaries and confidence interval first.",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
