#!/usr/bin/env python3
"""Disabled legacy segment-holdout proxy.

The former script labeled connected pixels as fault segments and explicitly disabled
the prescribed collar. It also did not rebuild catalogue-derived features from the
visible segments. Despite its previous name/docstring, it was not a compliant
segment-with-buffer hide-and-recover evaluator. Its outputs are not valid
HOLDOUT-DTI and must not be used for candidate selection.
"""
import sys


def main() -> int:
    print("BLOCKED: legacy no-collar connected-component proxy is not a valid holdout evaluator.", file=sys.stderr)
    print("Implement the required segment-with-buffer protocol before scoring candidates.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
