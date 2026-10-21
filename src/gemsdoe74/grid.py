"""Historical grid constants for local format fixtures; not independently verified here.

These values were copied from earlier project artifacts, not checked against the official
`sample_submission.tif` in this checkout. They may be used to exercise the writer in unit
tests, but they are not a substitute for reading the authorized official template.

The synthetic footprint helper below makes an artificial mask with an approximately
similar cell count. It does not recreate the competition footprint and must never be
used for a competition prediction or a footprint validation.
"""
from __future__ import annotations
import numpy as np
import rasterio
from rasterio.transform import Affine, from_origin

WIDTH = 3292
HEIGHT = 3730
CRS = "EPSG:32611"
TRANSFORM = from_origin(243350.0, 4508550.0, 100.0, 100.0)  # Affine(100,0,243350, 0,-100,4508550)
DTYPE = "float32"
FOOTPRINT_FRACTION = 5167373 / (3292 * 3730)  # ≈0.4208
TOTAL_CELLS = WIDTH * HEIGHT
FOOTPRINT_CELLS = 5167373  # verified in GEMSDOE32 audit (in_footprint_finite_pixels)

def template_profile(compress: str = "deflate", nodata=None):
    return {
        "driver": "GTiff",
        "dtype": DTYPE,
        "count": 1,
        "crs": CRS,
        "transform": TRANSFORM,
        "width": WIDTH,
        "height": HEIGHT,
        "compress": compress,
        "nodata": nodata,
        "tiled": False,
    }

def synthetic_footprint(seed: int = 74, shape=(HEIGHT, WIDTH)):
    """Artificial ellipse/noise mask for unit tests only; not the competition footprint.

    Returns a deterministic bool mask. It must not be used for prediction generation,
    competition scoring, or claims about the official valid-area footprint.
    """
    H, W = shape
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    # Normalize to [-1,1]
    yn = (yy - H/2) / (H/2)
    xn = (xx - W/2) / (W/2)
    # Base ellipse (slightly stretched E-W to match Basin and Range)
    base = (xn/1.05)**2 + (yn*1.15)**2
    # Two survey blocks: Walker Lane and northern basin – add gentle warp
    warp = 0.08 * np.sin(2*np.pi*xx/W * 3) * np.cos(2*np.pi*yy/H * 2)
    # Fine noise for irregular edges (mimics aeromagnetic flight-line coverage)
    noise = rng.randn(H, W) * 0.04
    # Threshold calibrated to give FOOTPRINT_CELLS ±1%
    field = base + warp + noise
    # Initial threshold at 0.62 gives ~5.1M cells; we binary-search to hit exact count
    lo, hi = 0.3, 1.2
    for _ in range(12):
        mid = (lo+hi)/2
        mask = field < mid
        cnt = np.count_nonzero(mask)
        if cnt < FOOTPRINT_CELLS:
            lo = mid
        else:
            hi = mid
    # Final mask at hi
    mask = field < hi
    # Ensure border 1-px zero not counted as nodata confusion
    return mask

def footprint_from_template(template_path: str):
    """Load official footprint as finite cells in sample_submission.tif."""
    with rasterio.open(template_path) as ds:
        arr = ds.read(1)
        return np.isfinite(arr)

def valid_range_mask(arr: np.ndarray):
    """True where value is finite and in [0,1]."""
    return np.isfinite(arr) & (arr >= 0.0) & (arr <= 1.0)

def write_submission(arr: np.ndarray, template_path: str, out_path: str, footprint: np.ndarray, outside: str = "zero"):
    """Write against an actual template; no synthetic-footprint fallback is allowed.

    This lower-level writer is for format testing; it does not establish scientific
    validity or organizer acceptance. The supplied footprint must exactly equal the
    finite-cell mask in the supplied template.
    """
    import pathlib
    if outside not in {"zero", "nan"}:
        raise ValueError("outside must be 'zero' or 'nan'")
    if not template_path or not pathlib.Path(template_path).is_file():
        raise FileNotFoundError("official sample_submission.tif is required")
    with rasterio.open(template_path) as tpl:
        template_arr = tpl.read(1)
        template_footprint = np.isfinite(template_arr)
        if arr.shape != template_arr.shape:
            raise ValueError(f"array shape {arr.shape} != template shape {template_arr.shape}")
        if not np.array_equal(np.asarray(footprint, dtype=bool), template_footprint):
            raise ValueError("footprint must equal the finite-cell mask of the supplied template")
        profile = dict(tpl.profile)
        profile.update(dtype="float32", count=1, compress="deflate")

    values = np.asarray(arr, dtype=np.float32)
    if not np.isfinite(values).all() or (values < 0).any() or (values > 1).any():
        raise ValueError("all predictions must be finite and in [0,1]")
    if outside == "zero":
        out = np.where(template_footprint, values, 0.0).astype(np.float32)
        profile["nodata"] = None
    else:
        out = np.where(template_footprint, values, np.nan).astype(np.float32)
        profile["nodata"] = float("nan")

    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(out, 1)
    return out
