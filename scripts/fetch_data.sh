#!/usr/bin/env bash
set -euo pipefail
cat >&2 <<'EOF'
BLOCKED: this legacy script fetched competition-like rasters and derived products from a sibling GitHub mirror.
The mirror's authorization, provenance, and redistribution rights are not verified in this repository.
To avoid accidental unauthorized access or use, this script no longer downloads files.

Use the official DrivenData data tab with authorized account access:
  https://www.drivendata.org/competitions/306/competition-doe-gems/data/
Place authorized files in data/, verify provenance/rights, then run:
  python scripts/prepare_data.py
EOF
exit 2
