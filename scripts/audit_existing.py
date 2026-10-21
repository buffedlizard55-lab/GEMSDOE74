#!/usr/bin/env python3
"""Re-read historical bytes; no training, promotion, or synthetic evaluation."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr
from gems74.submission import validate_submission

ROOT = Path(__file__).resolve().parents[1]

def main():
    data = ROOT / 'data/mirror'
    with rasterio.open(data / 'sample_submission.tif') as ds:
        a = ds.read(1, masked=True)
        foot = ~np.ma.getmaskarray(a) & np.isfinite(a.data)
        grid = (ds.shape, ds.crs, ds.transform)
    ref = data / 'h33-reference.tif'
    digest = hashlib.sha256(ref.read_bytes()).hexdigest()
    expected = json.loads((ROOT / 'evidence/h33-owner-audit.json').read_text())['zeros_tif']['sha256']
    if digest != expected:
        raise ValueError('Reference hash mismatch')
    with rasterio.open(ref) as ds:
        if (ds.shape, ds.crs, ds.transform) != grid:
            raise ValueError('Reference grid mismatch')
        reference = ds.read(1)
    near = distance_transform_edt(~((reference > 0) & foot)) <= 3
    reports = []
    for p in sorted((ROOT / 'docs/downloads').glob('*zeros.tif')):
        report = validate_submission(p, footprint=foot)
        with rasterio.open(p) as ds:
            arr = ds.read(1)
            report['template_grid_match'] = (ds.shape, ds.crs, ds.transform) == grid
        dots = (arr > 0) & foot
        report['comparison'] = {
            'scope': 'one H33 reference only; NOT complete registry clearance',
            'reference_sha256': digest,
            'surface_spearman': None,
            'surface_reason': 'original continuous surface not retained',
            'final_raster_spearman': float(spearmanr(arr[foot], reference[foot]).statistic),
            'final_dots_within_3px_fraction': float(near[dots].mean()) if dots.any() else None,
        }
        report['release_status'] = 'HOLD'
        reports.append(report)
    out = {'evidence_class': 'MEASURED-FILE-AUDIT (not a performance score)',
           'template_sha256': hashlib.sha256((data/'sample_submission.tif').read_bytes()).hexdigest(),
           'template_provenance': 'hash-pinned owner mirror, not organizer authenticated',
           'files': reports}
    (ROOT / 'evidence/file-audit-20261021.json').write_text(json.dumps(out, indent=2, allow_nan=False)+'\n')

if __name__ == '__main__':
    main()
