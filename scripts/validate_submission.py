#!/usr/bin/env python3
"""File-only validation; a pass never authorizes promotion or claims model skill."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
import rasterio
from gems74.submission import validate_submission

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('submission', type=Path)
    ap.add_argument('--template', type=Path, required=True)
    args = ap.parse_args()
    with rasterio.open(args.template) as t, rasterio.open(args.submission) as s:
        a = t.read(1, masked=True)
        footprint = ~np.ma.getmaskarray(a) & np.isfinite(a.data)
        match = t.shape == s.shape and t.crs == s.crs and t.transform == s.transform
    if not match or not footprint.any():
        print(json.dumps({'passed': False, 'reason': 'template grid mismatch or empty footprint'}))
        return 1
    result = validate_submission(args.submission, footprint=footprint)
    result['checks']['template_grid_match'] = match
    result['promotion'] = 'NOT ASSESSED'
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
