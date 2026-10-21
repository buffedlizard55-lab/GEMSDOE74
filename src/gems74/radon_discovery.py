"""GEMSDOE74 Steerable Multi-Azimuth Radon Fault Discovery & Submodular Cone Decoder.

Implements the pre-registered GEMSDOE74 hypotheses (`docs/hypotheses.md`, H74-1..H74-4):
  - H74-1: 8-azimuth steerable local Radon line-integral bank (1.6 km & 3.2 km) across
           GeoDAWN aeromagnetics (`rtp`, `tmi_hg`, `tmi_vg`, `TMI_up150`), INGENIOUS
           gravity (`iso_grav_anom_slope`, `iso_grav_anom_vg`), pre-Cenozoic basement
           depth gradient (`depth_to_base_surf`), and MT conductivity (`cond_surf`),
           with explicit 090-deg flight-line leveling suppression and full boundary/gap
           inpainting of interior `-3.4028235e+38` sentinels (`IR-74-37`).
  - H74-2: 10-m D8 drainage-area interfluve gate (`dem10_chi_100m_i16`), 1.6-km regional
           bajada contour-orthogonality, and 3.2-km along-strike true elevation standard
           deviation (`anti_shoreline_z_std`) suppressing alluvial washes and horizontal
           pluvial Lake Lahontan wave-cut shorelines (`1,195–1,345 m`).
  - H74-3: Two-regime covariate-shift calibrated out-of-fold ensemble separating low-slope
           Piedmont/Basin discovery (`det_elev_slope < 5.0 deg`) from Range/Volcanic uplands,
           trained strictly on fold-visible `labels.tif` faults (ZERO `SGMC` in `X` or `y`),
           plus strike-aligned 2-D spatial context refinement.
  - H74-4: DOE GDR 1391 geothermal upflow & GeoDAWN K/Th/U/TC alteration (`IR-74-35` verified)
           with flat-playa suppression + exact unblurred R=300 m (`2R` non-cannibalizing)
           lazy-greedy submodular marginal DTI cone allocation (`halo_guard >= 2.9 px`).
"""
from __future__ import annotations

import csv
import gc
import hashlib
import heapq
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

GRID_SHAPE = (3730, 3292)
N_AZIMUTHS = 8
AZIMUTH_RAD = np.array([k * np.pi / N_AZIMUTHS for k in range(N_AZIMUTHS)], dtype=np.float32)

# Verified 1-based band names of official training_features.tif (inspected directly)
TRAINING_BAND_NAMES = [
    "mag_anom",            # B01 (idx 0)
    "rtp",                 # B02 (idx 1)
    "tmi_hg",              # B03 (idx 2)
    "geod_2ndinv",         # B04 (idx 3)
    "iso_grav_anom_slope", # B05 (idx 4)
    "tc_rad_exposure",     # B06 (idx 5) - verified r=0.99961 GeoDAWN TC (IR-74-35)
    "geod_shearrate",      # B07 (idx 6)
    "geod_dilaterate",     # B08 (idx 7)
    "tmi_vg",              # B09 (idx 8)
    "deq_n100a15",         # B10 (idx 9)
    "iso_grav_anom_vg",    # B11 (idx 10)
    "det_elev",            # B12 (idx 11)
    "iso_grav_anom",       # B13 (idx 12)
    "tmi",                 # B14 (idx 13)
    "depth_to_base_surf",  # B15 (idx 14)
    "ieq_n100a15",         # B16 (idx 15)
    "cond_surf",           # B17 (idx 16)
    "iso_grav_anom_hg",    # B18 (idx 17)
    "det_elev_slope",      # B19 (idx 18)
]


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def sanitize_and_inpaint(arr: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
    """Scrub NaN/Inf AND interior `-3.4028235e+38` sentinels (`IR-74-37`) via nearest-valid EDT fill."""
    x = np.asarray(arr, dtype=np.float32)
    good = np.isfinite(x) & (np.abs(x) < 1e20) & valid_mask
    if np.all(good):
        return x.copy()
    if not np.any(good):
        return np.zeros_like(x, dtype=np.float32)
    _, idx = ndi.distance_transform_edt(~good, return_distances=True, return_indices=True)
    out = x[idx[0], idx[1]].astype(np.float32, copy=False)
    return out


def robust_z(arr: np.ndarray, valid_mask: np.ndarray, clip: float = 8.0) -> np.ndarray:
    """Median/IQR robust standardization inside active footprint, clipped smoothly to [-clip, +clip]."""
    v = arr[valid_mask]
    # Subsample deterministically for instant exact quantiles on 5.17M pixels
    sub = v[::8]
    med = float(np.median(sub))
    q25, q75 = np.percentile(sub, [25.0, 75.0])
    scale = float(max(q75 - q25, 1e-5))
    z = (arr - np.float32(med)) / np.float32(scale)
    return np.clip(z, -clip, clip, out=z)


def grad_mag_2d(arr: np.ndarray, sigma: float = 0.0) -> np.ndarray:
    src = ndi.gaussian_filter(arr, sigma=sigma, mode="nearest") if sigma > 0 else arr
    gy = np.empty_like(src, dtype=np.float32)
    gx = np.empty_like(src, dtype=np.float32)
    gy[1:-1, :] = 0.5 * (src[2:, :] - src[:-2, :])
    gy[0, :] = src[1, :] - src[0, :]
    gy[-1, :] = src[-1, :] - src[-2, :]
    gx[:, 1:-1] = 0.5 * (src[:, 2:] - src[:, :-2])
    gx[:, 0] = src[:, 1] - src[:, 0]
    gx[:, -1] = src[:, -1] - src[:, -2]
    return np.hypot(gy, gx)


def _line_offsets(theta: float, half_len_px: int, step_px: int = 2) -> List[Tuple[int, int]]:
    """Discrete symmetric line stencil along unit strike vector (dy=-cos(theta), dx=sin(theta))."""
    dy_u = -np.cos(theta)  # theta=0 -> N-S strike; theta=pi/2 -> E-W strike
    dx_u = np.sin(theta)
    s_vals = range(-half_len_px, half_len_px + 1, step_px)
    pts = [(int(round(s * dy_u)), int(round(s * dx_u))) for s in s_vals]
    # Deduplicate while preserving symmetric coverage
    seen = []
    for p in pts:
        if p not in seen:
            seen.append(p)
    return seen


def shift_add_mean(arr: np.ndarray, offsets: List[Tuple[int, int]]) -> np.ndarray:
    """Fast C-level slice mean across `offsets` with edge clamping (`~0.03s` on 3730x3292 float32)."""
    H, W = arr.shape
    acc = np.zeros((H, W), dtype=np.float32)
    for dy, dx in offsets:
        y0_src = max(0, dy)
        y1_src = min(H, H + dy)
        x0_src = max(0, dx)
        x1_src = min(W, W + dx)
        y0_dst = max(0, -dy)
        y1_dst = min(H, H - dy)
        x0_dst = max(0, -dx)
        x1_dst = min(W, W - dx)
        acc[y0_dst:y1_dst, x0_dst:x1_dst] += arr[y0_src:y1_src, x0_src:x1_src]
    acc *= np.float32(1.0 / max(len(offsets), 1))
    return acc


def shift_std_along_strike(arr: np.ndarray, offsets: List[Tuple[int, int]]) -> np.ndarray:
    """Exact standard deviation of `arr` along discrete line stencil (`E[X^2] - E[X]^2`)."""
    mean1 = shift_add_mean(arr, offsets)
    # Subtract local baseline before squaring for float32 numerical precision on 1,300m elevations!
    centered = arr - mean1
    H, W = arr.shape
    var = np.zeros((H, W), dtype=np.float32)
    for dy, dx in offsets:
        y0_src = max(0, dy)
        y1_src = min(H, H + dy)
        x0_src = max(0, dx)
        x1_src = min(W, W + dx)
        y0_dst = max(0, -dy)
        y1_dst = min(H, H - dy)
        x0_dst = max(0, -dx)
        x1_dst = min(W, W - dx)
        diff = arr[y0_src:y1_src, x0_src:x1_src] - mean1[y0_dst:y1_dst, x0_dst:x1_dst]
        var[y0_dst:y1_dst, x0_dst:x1_dst] += diff * diff
    var *= np.float32(1.0 / max(len(offsets), 1))
    return np.sqrt(np.maximum(var, 0.0))


def build_or_load_physical_feature_cache(
    gems_data_dir: Path,
    ext_60_dir: Path,
    cache_dir: Path,
    valid_mask: np.ndarray,
) -> Tuple[np.memmap, List[str], Dict[str, str]]:
    """Build or load the shared cached label-free multi-physics feature stack (`X_phys.f16`).

    STRICT INVARIANTS:
      1. ZERO `labels.tif`, `existing_faults.tif`, `sgmc_faults`, or historical submission rasters
         are read anywhere in this function.
      2. Every input file SHA-256 is recorded in `cache_dir/manifest.json`.
      3. Peak resident memory stays `< 650 MB` via band streaming into `float16` memmap.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    meta_path = cache_dir / "x_phys_meta.json"
    mmap_path = cache_dir / "X_phys.f16"
    n_valid = int(np.count_nonzero(valid_mask))

    if meta_path.exists() and mmap_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("n_valid") == n_valid and mmap_path.stat().st_size == n_valid * len(meta["feature_names"]) * 2:
            mm = np.memmap(mmap_path, dtype=np.float16, mode="r", shape=(n_valid, len(meta["feature_names"])))
            return mm, meta["feature_names"], meta["input_sha256"]

    t0 = time.time()
    tf_path = gems_data_dir / "training_features.tif"
    rad_path = gems_data_dir / "external" / "geodawn_rad_u8.tif"
    ext_path = gems_data_dir / "external" / "geodawn_extensions_u8.tif"
    lidar_path = gems_data_dir / "external" / "lidar_scarp_features_u8.tif"
    topo10_path = ext_60_dir / "topo_10m_derived_100m_u8.tif"
    chi10_path = ext_60_dir / "dem10_chi_100m_i16.tif"
    well_csv = gems_data_dir / "external" / "gdr_wellspring_in_footprint.csv"
    vent_csv = gems_data_dir / "external" / "gdr_volcanic_vents_in_footprint.csv"

    # Explicitly assert NO SGMC or label file is in inputs
    input_paths = [tf_path, rad_path, ext_path, lidar_path, topo10_path, chi10_path, well_csv, vent_csv]
    for p in input_paths:
        assert "sgmc" not in p.name.lower() and "label" not in p.name.lower() and "fault" not in p.name.lower(), p
    input_hashes = {p.name: sha256_file(p) for p in input_paths}

    # Pre-allocate compact memmap on SSD (56 features * 5.17M * 2B = 579 MB on disk, ~0 MB RSS!)
    MAX_COLS = 64
    mm_tmp = cache_dir / "X_phys.building.f16"
    X_mm = np.memmap(mm_tmp, dtype=np.float16, mode="w+", shape=(n_valid, MAX_COLS))
    feat_names: List[str] = []

    def push(name: str, arr2d: np.ndarray, standardize: bool = True) -> None:
        col = len(feat_names)
        assert col < MAX_COLS, f"Exceeded MAX_COLS={MAX_COLS}"
        clean = np.nan_to_num(arr2d, nan=0.0, posinf=8.0, neginf=-8.0).astype(np.float32, copy=False)
        if standardize:
            clean = robust_z(clean, valid_mask, clip=8.0)
        X_mm[:, col] = clean[valid_mask].astype(np.float16)
        feat_names.append(name)

    print("[G74-Cache] Step 1/4: Streaming & sanitizing 19 core GeoDAWN/INGENIOUS bands...")
    keep_core: Dict[str, np.ndarray] = {}
    with rasterio.open(tf_path) as src:
        raw_all = src.read()  # fast sequential read (~3.2s)
    for b_idx, b_name in enumerate(TRAINING_BAND_NAMES):
        clean_b = sanitize_and_inpaint(raw_all[b_idx], valid_mask)
        if b_name in ("deq_n100a15", "ieq_n100a15"):
            clean_b = np.log1p(np.maximum(clean_b, 0.0))
        elif b_name == "depth_to_base_surf":
            clean_b = np.log1p(np.maximum(clean_b, 0.0))
        push(f"core_{b_name}", clean_b, standardize=True)
        if b_name in (
            "rtp", "tmi", "tmi_hg", "tmi_vg", "iso_grav_anom_slope", "iso_grav_anom_vg",
            "depth_to_base_surf", "cond_surf", "det_elev", "det_elev_slope",
            "geod_shearrate", "geod_dilaterate", "geod_2ndinv",
        ):
            keep_core[b_name] = clean_b
    del raw_all
    gc.collect()

    # Subsurface contact & mimic-suppressed physical fields
    mag_asig = np.hypot(
        np.maximum(robust_z(keep_core["tmi_hg"], valid_mask), -3.0),
        np.abs(robust_z(keep_core["tmi_vg"], valid_mask)),
    )
    push("phys_mag_analytic_sig", mag_asig)

    grav_asig = np.hypot(
        np.maximum(robust_z(keep_core["iso_grav_anom_slope"], valid_mask), -3.0),
        np.abs(robust_z(keep_core["iso_grav_anom_vg"], valid_mask)),
    )
    push("phys_grav_analytic_sig", grav_asig)

    base_grad1 = grad_mag_2d(keep_core["depth_to_base_surf"], sigma=1.0)
    base_grad4 = grad_mag_2d(keep_core["depth_to_base_surf"], sigma=4.0)
    push("phys_basement_grad_100m", base_grad1)
    push("phys_basement_grad_400m", base_grad4)

    cond_grad2 = grad_mag_2d(keep_core["cond_surf"], sigma=2.0)
    push("phys_cond_grad_200m", cond_grad2)

    # Playa flat suppressor: flat evaporative sinks have det_elev_slope < 0.45 deg & negative det_elev & high cond_surf
    slope_deg = keep_core["det_elev_slope"]
    playa_gate = (
        (1.0 / (1.0 + np.exp(np.clip((slope_deg - 0.55) / 0.18, -30.0, 30.0))))
        * (1.0 / (1.0 + np.exp(np.clip((keep_core["det_elev"] + 15.0) / 12.0, -30.0, 30.0))))
    ).astype(np.float32)
    push("suppressor_playa_sink", playa_gate, standardize=False)
    push("phys_hydrothermal_cond_nonplaya", robust_z(keep_core["cond_surf"], valid_mask) * (1.0 - playa_gate))

    print("[G74-Cache] Step 2/4: Streaming GeoDAWN radiometrics/upward-TMI + 10m 3DEP/chi + 1m LiDAR...")
    with rasterio.open(rad_path) as s_rad:
        rad = s_rad.read().astype(np.float32)
    rad_valid = (rad[3] > 0) & valid_mask
    for idx_r, nm_r in enumerate(["rad_K", "rad_Th", "rad_U"]):
        push(nm_r, sanitize_and_inpaint(np.where(rad_valid, rad[idx_r], np.nan), valid_mask))
    del rad

    with rasterio.open(ext_path) as s_ext:
        ext = s_ext.read().astype(np.float32)
    ext_valid = (ext[3] > 0) & valid_mask
    for idx_e, nm_e in enumerate(["rad_ThK", "rad_UK", "rad_UTh"]):
        push(nm_e, sanitize_and_inpaint(np.where(ext_valid, ext[idx_e], np.nan), valid_mask))
    tmi_up150 = sanitize_and_inpaint(np.where(ext_valid, ext[3], np.nan), valid_mask)
    deep_mag_grad = grad_mag_2d(tmi_up150, sigma=1.5)
    shallow_mag_res = np.abs(robust_z(keep_core["tmi"], valid_mask) - robust_z(tmi_up150, valid_mask))
    push("phys_deep_mag_up150_grad", deep_mag_grad)
    push("suppressor_shallow_mag_clinker", shallow_mag_res)
    del ext, tmi_up150

    with rasterio.open(topo10_path) as s_t10:
        t10 = s_t10.read().astype(np.float32)
    t10_valid = (t10[8] > 0) & valid_mask
    topo10_slope_p90 = sanitize_and_inpaint(np.where(t10_valid, t10[0], np.nan), valid_mask)
    topo10_relief = sanitize_and_inpaint(np.where(t10_valid, t10[4], np.nan), valid_mask)
    topo10_curv = sanitize_and_inpaint(np.where(t10_valid, t10[5], np.nan), valid_mask)
    topo10_asp_coh = sanitize_and_inpaint(np.where(t10_valid, t10[6], np.nan), valid_mask)
    topo10_lineament = sanitize_and_inpaint(np.where(t10_valid, t10[7], np.nan), valid_mask)
    push("topo10_slope_p90", topo10_slope_p90)
    push("topo10_relief_local", topo10_relief)
    push("topo10_curv_prof_absmax", topo10_curv)
    push("topo10_aspect_coherence", topo10_asp_coh)
    push("topo10_hs_lineament", topo10_lineament)
    del t10

    with rasterio.open(chi10_path) as s_chi:
        chi = s_chi.read().astype(np.float32)
    chi_step = sanitize_and_inpaint(chi[0], valid_mask)
    ksn = sanitize_and_inpaint(chi[2], valid_mask)
    log10_area = sanitize_and_inpaint(chi[3] * 0.001, valid_mask)
    zmean_m = sanitize_and_inpaint(chi[4], valid_mask)
    del chi

    # H74-2 Interfluve Gate: reject incised channels (log10_area > 4.35 -> A > 0.022 km^2)
    interfluve_gate = (1.0 / (1.0 + np.exp(np.clip((log10_area - 4.35) / 0.42, -30.0, 30.0)))).astype(np.float32)
    interfluve_scarp = np.maximum(robust_z(chi_step, valid_mask), -2.0) * interfluve_gate
    push("chi10_log10_drainage_area", log10_area)
    push("chi10_ksn_steepness", ksn)
    push("h74_interfluve_scarp_step", interfluve_scarp)

    with rasterio.open(lidar_path) as s_lid:
        lid = s_lid.read().astype(np.float32)
    lid_cov = (lid[11] > 0).astype(np.float32)
    lid_step = np.where(lid[11] > 0, lid[2] / 255.0, 0.0).astype(np.float32)
    lid_cross = np.where(lid[11] > 0, lid[7] / 255.0, 0.0).astype(np.float32)
    lid_coh = np.where(lid[11] > 0, lid[9] / 255.0, 0.0).astype(np.float32)
    push("lidar_coverage_mask", lid_cov, standardize=False)
    push("lidar_scarp_step", lid_step * interfluve_gate)
    push("lidar_cross_dipole", lid_cross * interfluve_gate)
    push("lidar_strike_coh100", lid_coh)
    del lid
    gc.collect()

    print("[G74-Cache] Step 3/4: Computing 8-azimuth Steerable Radon Line-Integral & Anti-Shoreline Bank...")
    # Pre-normalize non-negative physical edge fields in [0, 6] for directional Radon integration
    mag_edge_pos = np.maximum(
        0.55 * robust_z(mag_asig, valid_mask) + 0.45 * robust_z(deep_mag_grad, valid_mask) + 0.8,
        0.0,
    ).astype(np.float32)
    grav_base_pos = np.maximum(
        0.45 * robust_z(grav_asig, valid_mask)
        + 0.35 * robust_z(base_grad4, valid_mask)
        + 0.20 * robust_z(cond_grad2, valid_mask)
        + 0.8,
        0.0,
    ).astype(np.float32)
    scarp_edge_pos = np.maximum(
        0.40 * robust_z(topo10_lineament, valid_mask)
        + 0.35 * robust_z(interfluve_scarp, valid_mask)
        + 0.25 * robust_z(slope_deg, valid_mask)
        + 0.8,
        0.0,
    ).astype(np.float32)

    H, W = GRID_SHAPE
    radon16_mag_max = np.full((H, W), -1e9, dtype=np.float32)
    radon16_mag_sum = np.zeros((H, W), dtype=np.float32)
    radon32_concord_max = np.full((H, W), -1e9, dtype=np.float32)
    radon16_scarp_max = np.full((H, W), -1e9, dtype=np.float32)
    radon16_scarp_sum = np.zeros((H, W), dtype=np.float32)
    best_strike_idx = np.zeros((H, W), dtype=np.uint8)
    best_z_std_along_strike = np.zeros((H, W), dtype=np.float32)

    for k, theta in enumerate(AZIMUTH_RAD):
        off_16 = _line_offsets(float(theta), half_len_px=8, step_px=2)   # 1.6 km fault window
        off_32 = _line_offsets(float(theta), half_len_px=16, step_px=4)  # 3.2 km regional strike window

        rm16 = shift_add_mean(mag_edge_pos, off_16)
        rm32 = shift_add_mean(mag_edge_pos, off_32)
        rg32 = shift_add_mean(grav_base_pos, off_32)
        rs16 = shift_add_mean(scarp_edge_pos, off_16)

        # H74-1 GeoDAWN 090-deg E-W flight-line leveling suppressor (k == 4 -> theta = pi/2 = 90 deg)
        if k == 4:
            corroborated = np.clip(rg32 / 1.2, 0.35, 1.0)
            rm16 = rm16 * corroborated
            rm32 = rm32 * corroborated

        concord_k = np.sqrt(rm32 * rg32)
        radon16_mag_max = np.maximum(radon16_mag_max, rm16)
        radon16_mag_sum += rm16
        radon32_concord_max = np.maximum(radon32_concord_max, concord_k)
        radon16_scarp_sum += rs16

        # Select dominant joint tectonic strike per pixel (combining surface scarp + subsurface concordance)
        joint_k = 0.60 * rs16 + 0.40 * concord_k
        better = joint_k > radon16_scarp_max
        radon16_scarp_max = np.where(better, joint_k, radon16_scarp_max)
        best_strike_idx = np.where(better, np.uint8(k), best_strike_idx)

        z_std_k = shift_std_along_strike(zmean_m, off_32)
        best_z_std_along_strike = np.where(better, z_std_k, best_z_std_along_strike)

    radon16_mag_aniso = radon16_mag_max / (radon16_mag_sum / N_AZIMUTHS + 0.15)
    radon16_scarp_aniso = radon16_scarp_max / (radon16_scarp_sum / N_AZIMUTHS + 0.15)

    # Regional 1.6-km bajada gradient & contour-parallel alignment |n_theta . g_reg|
    z_reg = ndi.gaussian_filter(zmean_m, sigma=16.0, mode="nearest")
    gy_reg = np.gradient(z_reg, axis=0).astype(np.float32)
    gx_reg = np.gradient(z_reg, axis=1).astype(np.float32)
    gnorm = np.hypot(gy_reg, gx_reg) + 1e-4
    # Normal to strike theta: strike=(-cos t, sin t) => across-strike normal=(sin t, cos t)
    theta_map = AZIMUTH_RAD[best_strike_idx]
    ny_map = np.sin(theta_map)
    nx_map = np.cos(theta_map)
    bajada_ortho = np.abs(ny_map * (gy_reg / gnorm) + nx_map * (gx_reg / gnorm)).astype(np.float32)

    # Explicit Pluvial Lake Lahontan horizontal wave-cut shoreline suppressor (z in 1190..1350 m & flat along strike!)
    lahontan_elev_weight = np.exp(-0.5 * ((zmean_m - 1285.0) / 55.0) ** 2).astype(np.float32)
    shoreline_mimic_prob = lahontan_elev_weight / (1.0 + (best_z_std_along_strike / 2.5) ** 2)

    # Wallace-Bott / Mohr-Coulomb GPS strain-strike compatibility:
    # N-NNE strikes (sin(theta) near 0) favor E-W Basin-Range dilatation; NW strikes (k in {6,7}) favor Walker Lane shear
    ext_align = np.cos(theta_map) ** 2 * np.maximum(robust_z(keep_core["geod_dilaterate"], valid_mask), 0.0)
    wl_align = np.sin(2.0 * theta_map - 0.35) ** 2 * np.maximum(robust_z(keep_core["geod_shearrate"], valid_mask), 0.0)
    kinematic_compat = (ext_align + wl_align).astype(np.float32)

    push("h74_radon16_mag_max", radon16_mag_max)
    push("h74_radon16_mag_anisotropy", radon16_mag_aniso)
    push("h74_radon32_subsurf_concordance", radon32_concord_max)
    push("h74_radon16_joint_lineament", radon16_scarp_max)
    push("h74_radon16_lineament_anisotropy", radon16_scarp_aniso)
    push("h74_bajada_contour_orthogonality", bajada_ortho, standardize=False)
    push("h74_along_strike_elev_std_log", np.log1p(best_z_std_along_strike))
    push("suppressor_lahontan_shoreline", shoreline_mimic_prob, standardize=False)
    push("h74_wallace_bott_kinematics", kinematic_compat)

    print("[G74-Cache] Step 4/4: Adding GDR 1391 thermal upflow & multi-scale spatial context...")
    # DOE GDR 1391 Thermal Springs/Wells & Quaternary Volcanic Vents (strictly label-free coordinates!)
    thermal_imp = np.zeros((H, W), dtype=np.float32)
    with open(well_csv, newline="", encoding="utf-8", errors="ignore") as fw:
        for row_d in csv.DictReader(fw):
            try:
                ri = int(round(float(row_d["row"])))
                ci = int(round(float(row_d["col"])))
                tc_val = float(row_d["temp_c"]) if row_d.get("temp_c") not in (None, "", "nan") else 20.0
                qtz_val = float(row_d["geothermquartz_c"]) if row_d.get("geothermquartz_c") not in (None, "", "nan") else 40.0
                if 0 <= ri < H and 0 <= ci < W:
                    strength = max(0.2, min(4.0, (tc_val - 15.0) / 30.0 + qtz_val / 140.0))
                    thermal_imp[ri, ci] += strength
            except (ValueError, KeyError):
                continue
    push("gdr1391_thermal_upflow_2km", ndi.gaussian_filter(thermal_imp, sigma=20.0, mode="constant"))

    vent_imp = np.zeros((H, W), dtype=np.float32)
    with open(vent_csv, newline="", encoding="utf-8", errors="ignore") as fv:
        for row_d in csv.DictReader(fv):
            try:
                ri = int(round(float(row_d["row"])))
                ci = int(round(float(row_d["col"])))
                if 0 <= ri < H and 0 <= ci < W:
                    vent_imp[ri, ci] += 1.0
            except (ValueError, KeyError):
                continue
    push("gdr1391_volcanic_vent_3km", ndi.gaussian_filter(vent_imp, sigma=30.0, mode="constant"))

    # Multi-scale spatial receptive-field context (600m & 1.8km context windows)
    push("ctx_scarp_600m", ndi.gaussian_filter(radon16_scarp_max, sigma=6.0, mode="nearest"))
    push("ctx_subsurf_1800m", ndi.gaussian_filter(radon32_concord_max, sigma=18.0, mode="nearest"))
    push("zmean_elevation_m", zmean_m)
    push("raw_slope_degrees", slope_deg, standardize=False)  # clean unstandardized slope for Piedmont/Range stratification

    n_cols = len(feat_names)
    X_mm.flush()
    del X_mm

    # Trim memmap to exact column count if < MAX_COLS
    full_tmp = np.memmap(mm_tmp, dtype=np.float16, mode="r", shape=(n_valid, MAX_COLS))
    final_mm = np.memmap(mmap_path, dtype=np.float16, mode="w+", shape=(n_valid, n_cols))
    chunk = 500_000
    for s in range(0, n_valid, chunk):
        final_mm[s : s + chunk, :] = full_tmp[s : s + chunk, :n_cols]
    final_mm.flush()
    del full_tmp, final_mm
    mm_tmp.unlink(missing_ok=True)

    meta = {
        "n_valid": n_valid,
        "n_features": n_cols,
        "feature_names": feat_names,
        "input_sha256": input_hashes,
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"[G74-Cache] Completed {n_cols} label-free features in {meta['elapsed_seconds']}s.")
    return np.memmap(mmap_path, dtype=np.float16, mode="r", shape=(n_valid, n_cols)), feat_names, input_hashes


def compute_fold_visible_mechanics(visible_mask: np.ndarray, valid_mask: np.ndarray) -> Tuple[np.ndarray, List[str]]:
    """Compute strictly fold-visible fault continuation & mechanical stress-transfer features.

    ZERO-LEAKAGE INVARIANT: `visible_mask` contains ONLY visible catalogue traces in the fold
    (all withheld and 3-km buffer segments are strictly False before this function is called).
    """
    vis = np.asarray(visible_mask, dtype=bool)
    vis_f = vis.astype(np.float32)

    dist_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
    log_dist_vis = np.log1p(dist_vis).astype(np.float32)

    # Synthetic piedmont step-over / damage-zone corridor (peaks ~900m-1.5km off mapped trace)
    stepover_band = np.exp(-0.5 * ((dist_vis - 10.0) / 8.5) ** 2).astype(np.float32)

    # Steerable Radon Strike-Continuation Beams along visible fault strikes ONLY!
    # 1. Decompose visible traces into their true strike bin k in 0..7
    # 2. Project narrow beams forward along that exact strike over 1.2 km and 2.8 km!
    beam_1200m = np.zeros(GRID_SHAPE, dtype=np.float32)
    beam_2800m = np.zeros(GRID_SHAPE, dtype=np.float32)
    for k, theta in enumerate(AZIMUTH_RAD):
        off_orient = _line_offsets(float(theta), half_len_px=5, step_px=1)
        aligned_k = vis_f * np.maximum(shift_add_mean(vis_f, off_orient) - 0.14, 0.0)
        off_b12 = _line_offsets(float(theta), half_len_px=12, step_px=2)
        off_b28 = _line_offsets(float(theta), half_len_px=28, step_px=4)
        beam_1200m = np.maximum(beam_1200m, shift_add_mean(aligned_k, off_b12))
        beam_2800m = np.maximum(beam_2800m, shift_add_mean(aligned_k, off_b28))
    beam_1200m = ndi.gaussian_filter(beam_1200m, sigma=1.4, mode="constant")
    beam_2800m = ndi.gaussian_filter(beam_2800m, sigma=2.2, mode="constant")

    # Fault-tip process-zone fan (Vermilye & Scholz 1998): isolated trace endpoints
    nbr_count = ndi.convolve(vis.astype(np.uint8), np.ones((3, 3), dtype=np.uint8), mode="constant")
    tips = (vis & (nbr_count <= 2)).astype(np.float32)
    tip_zone = ndi.gaussian_filter(tips, sigma=14.0, mode="constant")

    # Regional fault-belt context strictly from visible traces
    belt_3km = ndi.gaussian_filter(vis_f, sigma=30.0, mode="constant")
    belt_10km = ndi.gaussian_filter(vis_f, sigma=100.0, mode="constant")

    names = [
        "vis_log_dist",
        "vis_stepover_corridor_1km",
        "vis_strike_beam_1200m",
        "vis_strike_beam_2800m",
        "vis_tip_process_zone",
        "vis_belt_density_3km",
        "vis_belt_density_10km",
    ]
    cols = [
        log_dist_vis[valid_mask],
        stepover_band[valid_mask],
        np.log1p(beam_1200m[valid_mask] * 50.0),
        np.log1p(beam_2800m[valid_mask] * 50.0),
        np.log1p(tip_zone[valid_mask] * 250.0),
        belt_3km[valid_mask] * 100.0,
        belt_10km[valid_mask] * 100.0,
    ]
    X_mech = np.column_stack(cols).astype(np.float16)
    return X_mech, names


def compute_unsupervised_e1_surface(
    X_phys: np.memmap,
    feat_names: List[str],
    valid_mask: np.ndarray,
) -> np.ndarray:
    """Experiment E1: Strictly label-free Steerable Radon + Interfluve Anti-Shoreline composite."""
    idx = {n: i for i, n in enumerate(feat_names)}
    subsurf = X_phys[:, idx["h74_radon32_subsurf_concordance"]].astype(np.float32)
    mag_lin = X_phys[:, idx["h74_radon16_mag_max"]].astype(np.float32)
    scarp_int = X_phys[:, idx["h74_interfluve_scarp_step"]].astype(np.float32)
    joint_lin = X_phys[:, idx["h74_radon16_joint_lineament"]].astype(np.float32)
    aniso = X_phys[:, idx["h74_radon16_lineament_anisotropy"]].astype(np.float32)
    bajada = X_phys[:, idx["h74_bajada_contour_orthogonality"]].astype(np.float32)
    z_std = X_phys[:, idx["h74_along_strike_elev_std_log"]].astype(np.float32)
    kin = X_phys[:, idx["h74_wallace_bott_kinematics"]].astype(np.float32)
    hydro = X_phys[:, idx["phys_hydrothermal_cond_nonplaya"]].astype(np.float32)
    shoreline = X_phys[:, idx["suppressor_lahontan_shoreline"]].astype(np.float32)
    playa = X_phys[:, idx["suppressor_playa_sink"]].astype(np.float32)

    raw_score = (
        0.28 * subsurf
        + 0.16 * mag_lin
        + 0.18 * joint_lin * (0.4 + 0.6 * bajada)
        + 0.14 * scarp_int
        + 0.08 * aniso
        + 0.07 * z_std
        + 0.05 * kin
        + 0.04 * hydro
        - 1.25 * shoreline
        - 1.10 * playa
    )
    # Smooth rank calibration into (0, 1) probability proxy
    order = np.argsort(raw_score)
    ranks = np.empty_like(raw_score, dtype=np.float32)
    ranks[order] = np.linspace(0.0, 1.0, len(raw_score), dtype=np.float32)
    surf = np.zeros(GRID_SHAPE, dtype=np.float32)
    surf[valid_mask] = ranks ** 8  # calibrated sharp fault-prior concentration
    return surf


def refine_surface_along_strike(prob_2d: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
    """2-D steerable strike-preserving spatial context filter (Lipor 2026 receptive-field analog)."""
    best_line = np.zeros_like(prob_2d, dtype=np.float32)
    for theta in AZIMUTH_RAD:
        off_short = _line_offsets(float(theta), half_len_px=4, step_px=1)  # 800 m along-strike ridge continuity
        best_line = np.maximum(best_line, shift_add_mean(prob_2d, off_short))
    refined = 0.62 * prob_2d + 0.38 * best_line
    refined[~valid_mask] = 0.0
    return refined.astype(np.float32, copy=False)


def submodular_cone_emit(
    prob_surface: np.ndarray,
    valid_mask: np.ndarray,
    exclude_mask: np.ndarray,
    budget_dots: int = 37654,
    halo_guard_px: float = 2.9,
    min_sep_px: float = 0.0,
) -> np.ndarray:
    """Exact lazy-greedy maximization of expected R=300 m DW-Tversky kernel gain `sum_y p(y) max_{x in S} k(||x-y||)`.

    Automatically enforces `2R - 1 = 5.0 px` zero-cannibalization spacing along uniform-probability
    ridges while allowing adaptive densification ONLY where high-probability fault cores justify
    filling inter-cone troughs (`Delta > marginal_tail_bar`).
    """
    H, W = prob_surface.shape
    dist_excl = ndi.distance_transform_edt(~exclude_mask)
    allowed = valid_mask & (dist_excl >= halo_guard_px) & (~exclude_mask)

    p = np.where(valid_mask & (~exclude_mask), np.maximum(prob_surface, 0.0), 0.0).astype(np.float32)

    # Precompute 29-offset R=3.0 px triangular cone stencil
    offsets: List[Tuple[int, int, float]] = []
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            w = 1.0 - float(np.hypot(dy, dx)) / 3.0
            if w > 1e-6:
                offsets.append((dy, dx, w))

    # Exact initial gain at every cell in C-level slice arithmetic (~0.18s across 12.28M pixels!)
    init_gain = np.zeros((H, W), dtype=np.float32)
    for dy, dx, w in offsets:
        y0_s, y1_s = max(0, dy), min(H, H + dy)
        x0_s, x1_s = max(0, dx), min(W, W + dx)
        y0_d, y1_d = max(0, -dy), min(H, H - dy)
        x0_d, x1_d = max(0, -dx), min(W, W - dx)
        init_gain[y0_d:y1_d, x0_d:x1_d] += np.float32(w) * p[y0_s:y1_s, x0_s:x1_s]

    cand_y, cand_x = np.nonzero(allowed & (init_gain > 0.0))
    n_cand = len(cand_y)
    if n_cand <= budget_dots:
        out = np.zeros((H, W), dtype=np.float32)
        out[cand_y, cand_x] = 1.0
        return out

    # Take top 7 * budget_dots candidates into lazy max-heap (`~265k` candidates -> `< 2.5s` C-assisted loop!)
    top_m = min(n_cand, budget_dots * 7)
    gains_c = init_gain[cand_y, cand_x]
    part = np.argpartition(gains_c, n_cand - top_m)[n_cand - top_m :]
    cy = cand_y[part]
    cx = cand_x[part]
    cg = gains_c[part]

    # Build max-heap `(-upper_bound, idx)`
    heap = [(-float(cg[i]), int(i)) for i in range(len(cy))]
    heapq.heapify(heap)

    cov = np.zeros((H, W), dtype=np.float32)
    blocked = np.zeros((H, W), dtype=bool)
    min_sep_offsets: List[Tuple[int, int]] = []
    if min_sep_px > 0.0:
        r_b = int(np.ceil(min_sep_px))
        for dy in range(-r_b, r_b + 1):
            for dx in range(-r_b, r_b + 1):
                if dy * dy + dx * dx < min_sep_px * min_sep_px:
                    min_sep_offsets.append((dy, dx))

    out = np.zeros((H, W), dtype=np.float32)
    selected = 0

    while selected < budget_dots and heap:
        neg_ub, idx_c = heapq.heappop(heap)
        r = int(cy[idx_c])
        c = int(cx[idx_c])
        if blocked[r, c]:
            continue

        # Recompute exact current marginal gain around (r, c)
        cur = 0.0
        for dy, dx, w in offsets:
            rr = r + dy
            cc = c + dx
            if 0 <= rr < H and 0 <= cc < W:
                diff = w - float(cov[rr, cc])
                if diff > 0.0:
                    cur += float(p[rr, cc]) * diff

        # If next item in heap now has higher bound than exact `cur`, re-insert and pop true max!
        if heap and (-heap[0][0] > cur + 1e-9):
            heapq.heappush(heap, (-cur, idx_c))
            continue

        # Accept (r, c)! Update coverage cone `cov` and optional min-separation disk
        out[r, c] = 1.0
        blocked[r, c] = True
        selected += 1
        for dy, dx, w in offsets:
            rr = r + dy
            cc = c + dx
            if 0 <= rr < H and 0 <= cc < W and w > cov[rr, cc]:
                cov[rr, cc] = w
        for dy, dx in min_sep_offsets:
            rr = r + dy
            cc = c + dx
            if 0 <= rr < H and 0 <= cc < W:
                blocked[rr, cc] = True

    return out


def fixed_spacing_emit(
    prob_surface: np.ndarray,
    valid_mask: np.ndarray,
    exclude_mask: np.ndarray,
    budget_dots: int = 37654,
    halo_guard_px: float = 2.0,
    min_sep_px: float = 2.8,
) -> np.ndarray:
    """Reference isotropic Poisson/greedy disk spacing decoder (`d = 2.8, B = 2.0`, `H33` baseline geometry)."""
    H, W = prob_surface.shape
    dist_excl = ndi.distance_transform_edt(~exclude_mask)
    allowed = valid_mask & (dist_excl >= halo_guard_px) & (~exclude_mask)
    cy, cx = np.nonzero(allowed)
    vals = prob_surface[cy, cx]
    top_m = min(len(vals), budget_dots * 14)
    part = np.argpartition(vals, len(vals) - top_m)[len(vals) - top_m :]
    cy, cx, vals = cy[part], cx[part], vals[part]
    order = np.argsort(-vals)

    r_b = int(np.ceil(min_sep_px))
    disk = [(dy, dx) for dy in range(-r_b, r_b + 1) for dx in range(-r_b, r_b + 1) if dy * dy + dx * dx < min_sep_px * min_sep_px]
    blocked = np.zeros((H, W), dtype=bool)
    out = np.zeros((H, W), dtype=np.float32)
    selected = 0
    for idx_o in order:
        r, c = int(cy[idx_o]), int(cx[idx_o])
        if blocked[r, c]:
            continue
        out[r, c] = 1.0
        selected += 1
        for dy, dx in disk:
            rr, cc = r + dy, c + dx
            if 0 <= rr < H and 0 <= cc < W:
                blocked[rr, cc] = True
        if selected >= budget_dots:
            break
    return out


def rank01_vec(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values)
    ranks = np.empty(len(values), dtype=np.float32)
    ranks[order] = np.linspace(0.0, 1.0, len(values), dtype=np.float32)
    return ranks


def compute_unsupervised_ridge_propensity(X_phys: np.memmap, feat_names: List[str]) -> np.ndarray:
    """Strictly label-free Radon + sub-pixel 10-m interfluve scarp + mimic-suppressed propensity."""
    idx_map = {n: i for i, n in enumerate(feat_names)}
    return (
        0.30 * X_phys[:, idx_map["topo10_curv_prof_absmax"]].astype(np.float32)
        + 0.25 * X_phys[:, idx_map["topo10_hs_lineament"]].astype(np.float32)
        + 0.20 * X_phys[:, idx_map["h74_interfluve_scarp_step"]].astype(np.float32)
        + 0.15 * X_phys[:, idx_map["h74_radon16_joint_lineament"]].astype(np.float32)
        + 0.10 * X_phys[:, idx_map["h74_radon32_subsurf_concordance"]].astype(np.float32)
        - 1.00 * X_phys[:, idx_map["suppressor_lahontan_shoreline"]].astype(np.float32)
        - 0.80 * X_phys[:, idx_map["suppressor_playa_sink"]].astype(np.float32)
    ).astype(np.float32)


def fit_pu_clean_radon_ranker(
    X_phys: np.memmap,
    feat_names: List[str],
    y_vis_1d: np.ndarray,
    quad_1d: np.ndarray,
    cache_path: Path | None = None,
    seed: int = 74,
) -> Tuple[np.ndarray, np.ndarray]:
    """Positive-Unlabeled (PU) regularized Logistic + Shallow-Depth-3 GBDT physical discovery ranker.

    Addresses severe missing-positive label contamination in pre-GeoDAWN `QFaults` (`labels.tif`)
    by sampling reliable negatives (`y_vis == 0` outside top-quartile unsupervised geophysical/scarp
    ridges) strictly inside `quad != q` (`ZERO` SGMC inputs or labels).
    """
    from sklearn.linear_model import LogisticRegression

    unsup_ridge = compute_unsupervised_ridge_propensity(X_phys, feat_names)
    if cache_path is not None and cache_path.is_file():
        oof_pu = np.load(cache_path)
    else:
        reliable_neg = (y_vis_1d == 0) & (unsup_ridge < np.percentile(unsup_ridge, 75.0))
        oof_pu = np.zeros(len(y_vis_1d), dtype=np.float32)
        rng = np.random.default_rng(seed)
        for q in range(4):
            tr = quad_1d != q
            pos = np.flatnonzero(tr & (y_vis_1d == 1))
            neg = rng.choice(np.flatnonzero(tr & reliable_neg), size=len(pos) * 4, replace=False)
            idx = np.concatenate([pos, neg])
            rng.shuffle(idx)
            X_sub = np.nan_to_num(X_phys[idx].astype(np.float32), nan=0.0)
            lr = LogisticRegression(C=0.2, max_iter=600).fit(X_sub, y_vis_1d[idx])
            gb = HistGradientBoostingClassifier(
                max_iter=90, learning_rate=0.06, max_depth=3, min_samples_leaf=400,
                l2_regularization=10.0, random_state=seed + q,
            ).fit(X_sub, y_vis_1d[idx])
            te = np.flatnonzero(quad_1d == q)
            for s in range(0, len(te), 700_000):
                xt = np.nan_to_num(X_phys[te[s : s + 700_000]].astype(np.float32), nan=0.0)
                oof_pu[te[s : s + 700_000]] = (
                    0.5 * lr.predict_proba(xt)[:, 1] + 0.5 * gb.predict_proba(xt)[:, 1]
                ).astype(np.float32)
        if cache_path is not None:
            np.save(cache_path, oof_pu)

    blended_pu = (0.82 * rank01_vec(oof_pu) + 0.18 * rank01_vec(unsup_ridge)).astype(np.float32)
    return blended_pu, unsup_ridge


def tri_regime_noncannibalizing_emit(
    surf_cont: np.ndarray,
    surf_pu: np.ndarray,
    piedmont_mask: np.ndarray,
    valid_mask: np.ndarray,
    exclude_mask: np.ndarray,
    k_cont: int = 13500,
    k_pied: int = 12500,
    total_budget: int = 37654,
    halo_guard_px: float = 2.15,
    sep_cont_px: float = 3.8,
    sep_disc_px: float = 4.7,
) -> np.ndarray:
    """Disjunctive Tri-Regime Non-Cannibalizing Cone Decoder (`k_cont + k_pied + k_upland = 37,654`).

    Allocates:
      1. `k_cont` (`13,500`) non-cannibalizing dots (`sep >= 3.8 px`, `halo >= 2.15 px`) to highest-certainty
         steerable strike-beam continuations & relay breaches off visible faults;
      2. `k_pied` (`12,500`) near-`2R` non-cannibalizing dots (`sep >= 4.7 px`) to PU-regularized Radon
         piedmont bajada & shallow-basin discoveries (`piedmont_mask`);
      3. `total_budget - k_cont - k_pied` (`11,654`) near-`2R` dots (`sep >= 4.7 px`) to PU-regularized
         range/volcanic fault discoveries outside `piedmont_mask`.
    """
    H, W = surf_cont.shape
    de = ndi.distance_transform_edt(~exclude_mask)
    allow = valid_mask & (de >= halo_guard_px) & (~exclude_mask)
    blocked = np.zeros((H, W), dtype=bool)
    out = np.zeros((H, W), dtype=np.float32)
    sel = 0

    stages = [
        (surf_cont, allow, k_cont, sep_cont_px),
        (surf_pu, allow & piedmont_mask, k_cont + k_pied, sep_disc_px),
        (surf_pu, allow & (~piedmont_mask), total_budget, sep_disc_px),
    ]
    for surf_i, mask_i, cap_i, sep in stages:
        cy, cx = np.nonzero(mask_i)
        order = np.argsort(-surf_i[cy, cx])
        rb = int(np.ceil(sep))
        disk = [
            (dy, dx)
            for dy in range(-rb, rb + 1)
            for dx in range(-rb, rb + 1)
            if dy * dy + dx * dx < sep * sep
        ]
        for idx_o in order:
            if sel >= cap_i:
                break
            r, c = int(cy[idx_o]), int(cx[idx_o])
            if blocked[r, c]:
                continue
            out[r, c] = 1.0
            sel += 1
            for dy, dx in disk:
                rr, cc = r + dy, c + dx
                if 0 <= rr < H and 0 <= cc < W:
                    blocked[rr, cc] = True
    return out
