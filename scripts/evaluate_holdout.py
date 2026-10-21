#!/usr/bin/env python3
"""Canonical CLI entry point for the shared buffered-segment holdout evaluator.

All logic lives in ``evaluate_holdout_segments.py`` so the repository has one
implementation of the split, buffer, leakage canary, and pooled DTI protocol.
Catalogue-dependent methods must call that implementation with a fold-aware
builder; this CLI evaluates only explicitly declared catalogue-independent
surfaces.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_holdout_segments import (  # noqa: E402
    EVALUATOR_VERSION,
    compare_candidate_to_baseline,
    evaluate_holdout,
    feature_auc_canary,
    main,
    quadrant_ids,
)

__all__ = [
    "EVALUATOR_VERSION",
    "compare_candidate_to_baseline",
    "evaluate_holdout",
    "feature_auc_canary",
    "quadrant_ids",
]

if __name__ == "__main__":
    raise SystemExit(main())
