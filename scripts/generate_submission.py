#!/usr/bin/env python3
"""Official GEMSDOE74 real-data submission builder entry point.

Note (IR-74-31..34 fix): Earlier revisions synthesized Perlin-noise ridges and wrote
hardcoded numbers when real data was absent. This entry point strictly requires real
SHA-256-verified competition inputs (`scripts/restore_data.py`) and delegates directly
to `scripts/run_g74_experiments.py` using unmodified shared `vendor/gems57` tools.
"""
from __future__ import annotations

from run_g74_experiments import run_all

if __name__ == "__main__":
    run_all()
