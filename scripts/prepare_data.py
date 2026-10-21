#!/usr/bin/env python3
"""Validate required real inputs, rejecting absent files and mismatched grids."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import rasterio

def prepare(data):
    data = Path(data)
    manifest = data / 'prepared_manifest.json'
    manifest.unlink(missing_ok=True)  # never leave a stale success on failed rerun
    names = ['sample_submission.tif', 'training_features.tif', 'existing_faults.tif']
    missing = [n for n in names if not (data / n).is_file()]
    if missing:
        raise ValueError('Missing required real inputs: ' + ', '.join(missing))
    records = []
    grid = None
    for name in names:
        p = data / name
        with rasterio.open(p) as ds:
            current = (ds.shape, ds.crs, ds.transform)
            if ds.crs is None or (grid is not None and current != grid):
                raise ValueError(f'{name}: grid mismatch or missing CRS')
            grid = current
            if name != 'training_features.tif' and ds.count != 1:
                raise ValueError(f'{name}: expected single band')
            for band in range(1, ds.count + 1):
                a = ds.read(band, masked=True)
                values = a.compressed()
                if values.size == 0 or not np.isfinite(values).all():
                    raise ValueError(f'{name} band {band}: empty or nonfinite unmasked data')
            h = hashlib.sha256()
            with p.open('rb') as f:
                for chunk in iter(lambda: f.read(1 << 20), b''):
                    h.update(chunk)
            records.append({'file': name, 'sha256': h.hexdigest(), 'bands': ds.count,
                            'descriptions': ds.descriptions})
    result = {'checked': True, 'organizer_authenticated': False, 'files': records,
              'note': 'Header/integrity checks only; band semantics and rights still require provenance.'}
    manifest.write_text(json.dumps(result, indent=2) + '\n')
    return result

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='data')
    args = ap.parse_args()
    try:
        prepare(args.data)
    except (ValueError, OSError) as e:
        ap.exit(2, f'BLOCKED: {e}\n')
