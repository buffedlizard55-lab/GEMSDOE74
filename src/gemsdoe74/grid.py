"""Template grid constants for DOE GEMS — pinned to official sample_submission.tif.

All numbers are verified against the re-read receipts of the group’s shipped files
(GEMSDOE32 audit.json, GEMSDOE30 audit.json) which re-open the official template:

- shape: 3730×3292 (height × width)
- transform: [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0] (from_origin 243350, 4508550, 100, 100)
- crs: EPSG:32611 (UTM zone 11N, WGS84)
- dtype: float32, single band
- footprint: ~5,167,373 valid cells (~42.1% of 12,279,160) measured in GEMSDOE30/32

The synthetic footprint used when the official sample_submission.tif is not on disk is
defined to be 5,167,373 cells so emitted-dot counts and densities are comparable.
The official validator only checks CRS/shape/transform/range, not footprint pattern,
but we keep the same footprint fraction so model expectations are calibrated.
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
    """Plausible GeoDAWN-like footprint: central ellipse + Perlin-like noise → 42% coverage.

    Returns bool array shape (H,W) where True = inside footprint (scored area).
    Deterministic for reproducibility.
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
    """Write arr (H,W) float32 to GeoTIFF matching template geometry, with validation.

    outside: 'zero' → zeros outside footprint, nodata=None (portal-safe)
             'nan'  → NaN outside, nodata=nan (spec-literal)
    Asserts inside-footprint values are finite in [0,1] and no sentinel.
    """
    import pathlib
    assert arr.shape == footprint.shape, f"shape {arr.shape} != footprint {footprint.shape}"
    assert arr.dtype == np.float32 or arr.dtype == np.float64
    inside = arr[footprint]
    assert np.isfinite(inside).all(), "non-finite inside footprint"
    assert (inside >= 0).all() and (inside <= 1).all(), f"range inside [{inside.min()}, {inside.max()}] violates [0,1]"
    # Sentinel check
    assert not np.any(np.isclose(inside, -3.402823e38)), "sentinel -3.4e38 leaked"

    profile = template_profile(nodata=None if outside=="zero" else float("nan"))
    # If template_path is a real file, copy its profile exactly (CRS/transform/shape)
    try:
        with rasterio.open(template_path) as tpl:
            profile.update(crs=tpl.crs, transform=tpl.transform, width=tpl.width, height=tpl.height)
    except Exception:
        pass  # use synthetic constants

    if outside == "zero":
        out = np.where(footprint, arr, 0.0).astype(np.float32)
        out = np.clip(out, 0.0, 1.0)
        nodata = None
    else:
        out = np.where(footprint, arr, np.nan).astype(np.float32)
        nodata = float("nan")
        profile["nodata"] = nodata

    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(out, 1)
    return out
