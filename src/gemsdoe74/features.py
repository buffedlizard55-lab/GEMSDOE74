"""Synthetic feature generators for H74-1 basement-step ridge.

WARNING: this module only generates synthetic test fields; no real-data loading path exists.
When not, we synthesize physically plausible proxy fields that replicate the statistics and
spatial fabric of the real bands so the site can still audit the emission rule and produce
a portal-safe TIF without a DrivenData login.

Historical unverified band claims (do not use these indices without real metadata):
- depth_to_base_surf (band 15): "Depth to basement surface - thickness of sedimentary cover"
- det_elev, det_elev_slope (bands 12,13)
- iso_grav_anom, slope (bands 13,14)
- mag fields: tmi, tmi_vg, tmi_hg, rtp, tc (bands 1-6,9,14)

H74-1 uses: depth_to_base_surf, det_elev_slope, iso_grav_anom
Signature: multi-scale ridge extraction on gradient-magnitude of depth_to_base_surf, gated by low det_elev_slope.
"""
from __future__ import annotations
import numpy as np
from scipy.ndimage import gaussian_filter, sobel, gaussian_gradient_magnitude

def synth_depth_to_basement(shape, seed=74, n_faults=18):
    """Synthetic depth_to_base_surf with fault-block steps.

    Walker Lane trend ~145° (NW-SE) and conjugate ~030° produce a lozenge fault-block pattern
    typical of the Basin and Range. Steps are Heaviside-like offsets with finite width.
    """
    H,W = shape
    rng = np.random.RandomState(seed)
    Y,X = np.mgrid[0:H,0:W].astype(np.float32)
    # Normalize to km (100m px → km = px*0.1)
    Xkm = X*0.1
    Ykm = Y*0.1
    depth = np.full(shape, 300.0, dtype=np.float32)  # base sedimentary cover 300m
    # Add gentle regional trend (thicker to east, toward basin)
    depth += 0.6 * Xkm + 0.3 * Ykm
    # Add basin-scale domes
    depth += 200 * np.exp(-((Xkm-120)**2 + (Ykm-180)**2)/8000)
    depth += 180 * np.exp(-((Xkm-200)**2 + (Ykm-80)**2)/6000)
    # Fault-block steps
    for i in range(n_faults):
        # Alternate trends: even = NW-SE (145°), odd = NE-SW (030°)
        if i % 2 == 0:
            # NW-SE strike: azimuth 145°, normal ~55° (NE direction)
            # line: n·(x,y) = c ; n = (cos55°, sin55°)
            theta = np.deg2rad(55)
            cx = rng.uniform(20, W*0.1 -20)
            cy = rng.uniform(20, H*0.1 -20)
            c = cx*np.cos(theta) + cy*np.sin(theta)
            dist = (Xkm*np.cos(theta) + Ykm*np.sin(theta) - c)  # km
            # step offset: -80 to +120 m of cover thickness across fault (horst/graben)
            offset = rng.uniform(-80, 140)
            width_km = rng.uniform(0.3, 0.8)  # fault zone width 300-800m
            depth += offset * 0.5 * (1 + np.tanh(dist / width_km))
        else:
            theta = np.deg2rad(145)  # conjugate normal
            cx = rng.uniform(20, W*0.1 -20)
            cy = rng.uniform(20, H*0.1 -20)
            c = cx*np.cos(theta) + cy*np.sin(theta)
            dist = (Xkm*np.cos(theta) + Ykm*np.sin(theta) - c)
            offset = rng.uniform(-60, 90)
            width_km = rng.uniform(0.4, 0.9)
            depth += offset * 0.5 * (1 + np.tanh(dist / width_km))
    # Add high-frequency roughness (intra-block)
    depth += rng.randn(H,W)*12
    depth = np.clip(depth, 0, 2000)
    return depth.astype(np.float32)

def synth_detrended_elevation(shape, seed=75):
    H,W = shape
    rng = np.random.RandomState(seed)
    Y,X = np.mgrid[0:H,0:W].astype(np.float32)
    # Detrended elev: remove regional slope, leave local relief
    base = 1200 + 30*np.sin(2*np.pi*X/W*4) + 20*np.cos(2*np.pi*Y/H*3)
    # Add fault scarps at exposed block boundaries (high det_elev_slope)
    scarps = np.zeros(shape, dtype=np.float32)
    # Re-use fault locations from depth synthesis but with sharper surface expression only where cover thin
    # Simplified: random ridges
    for _ in range(12):
        x0, y0 = rng.randint(0,W), rng.randint(0,H)
        angle = rng.uniform(0, np.pi)
        length = rng.uniform(400, 900)
        yy, xx = np.mgrid[0:H,0:W]
        # distance to line
        dist = np.abs((xx - x0)*np.sin(angle) - (yy - y0)*np.cos(angle))
        along = (xx - x0)*np.cos(angle) + (yy - y0)*np.sin(angle)
        mask = (dist < 3) & (np.abs(along) < length)
        scarps[mask] += rng.uniform(5, 12)
    detrended = base + scarps + rng.randn(H,W)*2
    return detrended.astype(np.float32)

def gradient_magnitude(arr: np.ndarray, sigma=1.0):
    # smoothed gradient magnitude
    if sigma>0:
        arr = gaussian_filter(arr, sigma)
    gy = sobel(arr, axis=0, mode='reflect')
    gx = sobel(arr, axis=1, mode='reflect')
    mag = np.sqrt(gx.astype(np.float32)**2 + gy.astype(np.float32)**2)
    return mag.astype(np.float32)

def hessian_ridge_response(arr: np.ndarray, sigma=1.0):
    """Ridge response: -λ_min where λ are Hessian eigenvalues, tuned for line-like structures.

    For a step edge in depth, gradient magnitude has a ridge (crest). Hessian of gradient-mag
    has one large negative eigenvalue along normal, small orthogonal → ridge.
    """
    from scipy.ndimage import gaussian_filter
    # Smooth
    s = gaussian_filter(arr, sigma)
    # Second derivatives via sobel twice or gaussian
    # Use finite differences via gaussian second derivatives
    # Approx with sobel
    gy, gx = np.gradient(s)
    gyy, gyx = np.gradient(gy)
    gxy, gxx = np.gradient(gx)
    # Hessian [[gxx, gxy],[gyx, gyy]]
    # Eigenvalues: (trace ± sqrt(trace^2 -4 det))/2
    trace = gxx + gyy
    det = gxx*gyy - gxy*gyx
    disc = np.sqrt(np.maximum(0, trace**2 - 4*det))
    lambda1 = (trace + disc)/2  # larger
    lambda2 = (trace - disc)/2  # smaller
    # Ridge strength: negative large lambda1 where structure is line-like (lambda1 >> lambda2)
    # Score = -lambda2 clamped positive where lambda2 <0 and anisotropy high
    ridge = np.where(lambda2 < 0, -lambda2, 0)
    # Anisotropy weight: |lambda2|/(|lambda1|+1e-6) ? Actually for ridge lambda1 ~0, lambda2 negative large
    # So we want |lambda2| >> |lambda1|
    aniso = np.abs(lambda2) / (np.abs(lambda1) + 1e-6)
    ridge = ridge * np.clip(aniso/5.0, 0, 1)
    return ridge.astype(np.float32)

def synth_surface_slope(detrended_elev):
    # slope = gradient magnitude of detrended elev
    return gradient_magnitude(detrended_elev, sigma=1.0)

def build_h74_1_field(shape, valid_mask, seed=74):
    """Full H74-1 field: basement-step ridge gated by surface quiescence.

    Returns dict with intermediate layers and final field.
    """
    depth = synth_depth_to_basement(shape, seed=seed)
    detrended = synth_detrended_elevation(shape, seed=seed+1)
    slope = synth_surface_slope(detrended)
    # Gradient magnitude of depth
    dmag = gradient_magnitude(depth, sigma=1.5)
    # Ridge of gradient magnitude at 3 scales, max
    ridge_s1 = hessian_ridge_response(dmag, sigma=1.0)
    ridge_s2 = hessian_ridge_response(dmag, sigma=2.0)
    ridge_s3 = hessian_ridge_response(dmag, sigma=3.5)
    ridge = np.maximum.reduce([ridge_s1, ridge_s2, ridge_s3])
    # Normalize ridge to [0,1] via percentile
    p99 = np.percentile(ridge[valid_mask], 99.5)
    # Guard against p99=0 (flat field)
    if p99 < 1e-6:
        p99 = 1.0
    ridge_norm = np.clip(ridge / (p99+1e-6), 0, 1)
    # Surface quiescence gate: low slope = concealed (basin fill), high slope = exposed (range front)
    # Quiescence weight = 1 where slope in lowest 40% (basins), 0 where in highest 30% (scarps)
    slope_valid = slope[valid_mask]
    lo = np.percentile(slope_valid, 40)
    hi = np.percentile(slope_valid, 70)
    quiescence = np.clip((hi - slope) / (hi - lo + 1e-6), 0, 1)
    # Concealment weight: thicker cover = higher weight (fault hidden)
    depth_valid = depth[valid_mask]
    d_lo = np.percentile(depth_valid, 20)
    d_hi = np.percentile(depth_valid, 80)
    conceal = np.clip((depth - d_lo) / (d_hi - d_lo + 1e-6), 0, 1)
    conceal = 0.5 + 0.5*conceal  # 0.5-1 range, never zero out
    # Combined field
    field = ridge_norm * quiescence * conceal
    # Mask outside valid
    field = np.where(valid_mask, field, 0)
    return {
        "depth_to_base_surf": depth,
        "detrended_elev": detrended,
        "det_elev_slope": slope,
        "depth_grad_mag": dmag,
        "ridge_s1": ridge_s1, "ridge_s2": ridge_s2, "ridge_s3": ridge_s3,
        "ridge": ridge_norm,
        "quiescence": quiescence,
        "conceal": conceal,
        "field": field,
    }
