"""Real-data GEMSDOE74 Transtensional Multi-Physics & Submodular DTI Allocation Lane.

Implements the 5 ranked geological hypotheses (H74-R1 .. H74-R5) on the real
GeoDAWN 19-band airborne geophysics & geodetic stack, 3DEP 1m/10m LiDAR & DEM,
fluvial tectonic geomorphology (chi, k_sn), airborne gamma-ray spectrometry,
and label-free GDR hydrothermal point catalogs:

  - H74-R1 (C1): Flight-Line Notch De-Striped Magnetic Analytic-Signal Tilt
    Zero-Crossing Ridge & 150 m Upward-Continuation Attenuation Ratio
  - H74-R2: Poisson Gravity-Magnetic Vector Strike Concordance
  - H74-R3: Walker Lane / Basin-and-Range Transtensional Coulomb Strain-Rate Dilation
  - H74-R4 (Real H74-1): Real-Data Basement-Step Multi-Scale Hessian Ridge Gated
    by Piedmont Surface Quiescence & Pluvial Shoreline Rejection (fixes IR-74-33)
  - H74-R5: Magnetotelluric Clay-Cap Breach & K/Th Potassic Strike Concordance

 coupled with Strike-Spaced Lazy-Greedy Submodular DTI Allocation over the exact
 R = 300 m (3.0 px) competition triangular kernel.
"""
from __future__ import annotations

import csv
import heapq
import io
import json
import struct
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.warp import transform as rio_transform
from scipy.ndimage import convolve, distance_transform_edt, gaussian_filter, label as ndi_label, maximum_filter

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import metric  # noqa: E402

FORBIDDEN_POINT_COLUMNS = frozenset(
    {
        "dist_known_fault_px",
        "dist_known_fault_m",
        "fault_distance",
        "known_fault_dist",
        "labels",
        "existing_faults",
        "sgmc_fault",
    }
)

TF_BAND_NAMES = [
    "Mag_RTP",
    "tmi_rtp_vd",
    "tmi_hg",
    "geod_2ndinv",
    "geod_maxshear",
    "geod_rot",
    "geod_shearrate",
    "geod_dilaterate",
    "tmi_vg",
    "cba_vg",
    "cba_hg",
    "cba",
    "iso_grav_anom",
    "iso_grav_anom_hg",
    "depth_to_base_surf",
    "depth_to_base_2023",
    "cond_surf",
    "det_elev",
    "det_elev_slope",
]

LIDAR_BAND_NAMES = [
    "lidar_ex_max",
    "lidar_ex_mean",
    "lidar_step_max",
    "lidar_lapneg_max",
    "lidar_lappos_max",
    "lidar_downface_max",
    "lidar_upface_max",
    "lidar_cross_max",
    "lidar_relief",
    "lidar_coh100",
    "lidar_strike",
]

TOPO10_BAND_NAMES = [
    "topo10_slope_p90",
    "topo10_slope_max",
    "topo10_steep_frac",
    "topo10_slope_std",
    "topo10_relief_local",
    "topo10_curv_prof_absmax",
    "topo10_aspect_coherence",
    "topo10_hs_lineament",
    "topo10_dem_mean",
]

CHI_BAND_NAMES = [
    "chi_step_max",
    "chi_step_min",
    "chi_ksn_max",
    "chi_log10_da_max",
    "chi_zmean_m",
]

CHI_U8_BAND_NAMES = [
    "chi_chan_n",
    "chi_knick_n",
    "chi_raised_n",
]


def _grad_mag(arr: np.ndarray, sigma: float = 1.5) -> np.ndarray:
    sm = gaussian_filter(arr, sigma=sigma) if sigma > 0 else arr
    gy, gx = np.gradient(sm)
    return np.hypot(gx, gy).astype(np.float32)


def _grad_vec(arr: np.ndarray, sigma: float = 2.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sm = gaussian_filter(arr, sigma=sigma) if sigma > 0 else arr
    gy, gx = np.gradient(sm)
    mag = np.hypot(gx, gy).astype(np.float32)
    return gx.astype(np.float32), gy.astype(np.float32), mag


def _destripe_ew_flightline(arr: np.ndarray) -> np.ndarray:
    """Suppress E-W (azimuth 90 deg) airborne survey flight-line leveling ripple.

    Subtracts the anisotropic E-W elongated, N-S high-pass ripple component:
      ripple = G_(sigma_y=0.75, sigma_x=22.0)(arr) - G_(sigma_y=3.5, sigma_x=22.0)(arr)
    preserving NNE/NNW/NE geological fault gradients while eliminating row-to-row leveling artifacts.
    """
    ew_fine = gaussian_filter(arr, sigma=(0.75, 22.0))
    ew_coarse = gaussian_filter(arr, sigma=(3.5, 22.0))
    return (arr - (ew_fine - ew_coarse)).astype(np.float32)


def _hessian_ridge_multiscale(arr: np.ndarray, sigmas: tuple[float, ...] = (1.2, 2.5, 4.0)) -> np.ndarray:
    """Compute multi-scale maximum principal negative curvature ridge of a scalar field."""
    out = np.zeros(arr.shape, dtype=np.float32)
    for sig in sigmas:
        sm = gaussian_filter(arr, sigma=sig)
        gy, gx = np.gradient(sm)
        gyy, gyx = np.gradient(gy)
        gxy, gxx = np.gradient(gx)
        0.5 * (gyx + gxy)
        tr = gxx + gyy
        det_disc = np.hypot(gxx - gyy, 2.0 * gxy)
        # Most negative eigenvalue (-lambda_min) scaled by sigma^2 for scale invariance
        ridge_s = np.maximum(0.0, -(0.5 * (tr - det_disc))) * (sig * sig)
        np.maximum(out, ridge_s.astype(np.float32), out=out)
    return out


def _utm_to_rc(
    ux: list[float] | np.ndarray,
    uy: list[float] | np.ndarray,
    transform: Any,
    shape: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ux_a = np.asarray(ux, dtype=np.float64)
    uy_a = np.asarray(uy, dtype=np.float64)
    cols = np.floor((ux_a - transform.c) / transform.a).astype(np.int64)
    rows = np.floor((uy_a - transform.f) / transform.e).astype(np.int64)
    ok = (rows >= 0) & (rows < shape[0]) & (cols >= 0) & (cols < shape[1])
    return rows[ok], cols[ok], ok


def _parse_2m_probes_dbf(zip_path: Path, transform: Any, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    imp_dab = np.zeros(shape, dtype=np.float32)
    imp_cnt = np.zeros(shape, dtype=np.float32)
    if not zip_path.is_file():
        return imp_dab, imp_cnt
    with zipfile.ZipFile(zip_path) as zf:
        dbf_name = next(n for n in zf.namelist() if n.lower().endswith(".dbf"))
        buf = zf.read(dbf_name)
    numrec, lenhdr, lenrec = struct.unpack("<4xIHH20x", buf[:32])
    fields: list[tuple[str, int, int]] = []
    pos = 32
    offset = 1
    while buf[pos] != 0x0D:
        fname = buf[pos : pos + 11].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
        assert fname not in FORBIDDEN_POINT_COLUMNS, f"Forbidden column: {fname}"
        flen = buf[pos + 16]
        fields.append((fname, offset, flen))
        offset += flen
        pos += 32
    fmap = {name: (off, flen) for name, off, flen in fields}
    lats, lons, dabs = [], [], []
    for i in range(numrec):
        rec = buf[lenhdr + i * lenrec : lenhdr + (i + 1) * lenrec]
        if not rec or rec[0:1] == b"*":
            continue
        try:
            lat_s = rec[fmap["LatDegreeN"][0] : fmap["LatDegreeN"][0] + fmap["LatDegreeN"][1]].strip()
            lon_s = rec[fmap["LongDegree"][0] : fmap["LongDegree"][0] + fmap["LongDegree"][1]].strip()
            dab_s = rec[fmap["F2mDAB"][0] : fmap["F2mDAB"][0] + fmap["F2mDAB"][1]].strip()
            t2m_s = rec[fmap["T2m"][0] : fmap["T2m"][0] + fmap["T2m"][1]].strip()
            lat = float(lat_s)
            lon = float(lon_s)
            dab = float(dab_s) if dab_s else 0.0
            t2m = float(t2m_s) if t2m_s else 0.0
        except ValueError:
            continue
        if not (25.0 <= lat <= 50.0 and -130.0 <= lon <= -100.0):
            continue
        excess = max(0.0, dab) + 0.25 * max(0.0, t2m - 22.0)
        lats.append(lat)
        lons.append(lon)
        dabs.append(excess)
    if lons:
        ux, uy = rio_transform("EPSG:4269", "EPSG:32611", lons, lats)
        rows, cols, ok = _utm_to_rc(ux, uy, transform, shape)
        vals = np.asarray(dabs, dtype=np.float32)[ok]
        np.add.at(imp_cnt, (rows, cols), 1.0)
        np.maximum.at(imp_dab, (rows, cols), vals)
    return imp_dab, imp_cnt


def build_gems74_feature_memmap(
    mmap_path: Path,
    fp: np.ndarray,
    transform: Any,
    data_dir: Path,
    ext_dir: Path,
) -> tuple[np.memmap, list[str], np.ndarray, dict[str, Any], np.ndarray]:
    """Stream-extract all 82 label-free physical features (76 base + 6 novel H74-R1..R5).

    Also returns the unsupervised H74-R1..R5 composite surface (for Experiment E1).
    """
    shape = fp.shape
    fp_idx = np.flatnonzero(fp)
    n_fp = int(fp_idx.size)
    names: list[str] = []

    total_cols = 85
    meta_path = mmap_path.with_suffix(".meta.json")
    e1_path = mmap_path.with_suffix(".e1_surface.npy")
    if mmap_path.is_file() and meta_path.is_file() and e1_path.is_file():
        cached_meta = json.loads(meta_path.read_text())
        if cached_meta.get("n_features") == total_cols and cached_meta.get("n_footprint_pixels") == n_fp:
            X = np.memmap(mmap_path, dtype=np.float32, mode="r", shape=(total_cols, n_fp))
            has_lidar_fp = np.asarray(X[cached_meta["feature_names"].index("lidar_has_coverage"), :] > 0.5)
            e1_surf = np.load(e1_path)
            return X, cached_meta["feature_names"], has_lidar_fp, cached_meta["meta"], e1_surf

    mmap_path.parent.mkdir(parents=True, exist_ok=True)
    X = np.memmap(mmap_path, dtype=np.float32, mode="w+", shape=(total_cols, n_fp))
    col_ptr = 0

    bad_fp = ~fp
    idx_fp = distance_transform_edt(bad_fp, return_distances=False, return_indices=True)
    idx_cache: list[tuple[np.ndarray, np.ndarray]] = [(bad_fp, idx_fp)]

    def _fast_fill(arr: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
        bad = ~valid_mask
        if not bad.any():
            return arr.astype(np.float32, copy=False)
        found_idx = None
        for prev_bad, prev_idx in idx_cache:
            if np.array_equal(bad, prev_bad):
                found_idx = prev_idx
                break
        if found_idx is None:
            found_idx = distance_transform_edt(bad, return_distances=False, return_indices=True)
            if len(idx_cache) < 5:
                idx_cache.append((bad.copy(), found_idx))
        out = arr.astype(np.float32, copy=True)
        out[bad] = out[found_idx[0][bad], found_idx[1][bad]]
        return out

    def _push(name: str, arr2d_or_1d: np.ndarray, is_fp_1d: bool = False) -> None:
        nonlocal col_ptr
        assert name not in FORBIDDEN_POINT_COLUMNS, f"Forbidden feature {name}"
        vec = arr2d_or_1d if is_fp_1d else arr2d_or_1d.ravel()[fp_idx]
        X[col_ptr, :] = vec.astype(np.float32, copy=False)
        names.append(name)
        col_ptr += 1

    # 1. Official 19-band training_features.tif
    saved: dict[str, np.ndarray] = {}
    with rasterio.open(data_dir / "training_features.tif") as ds:
        for b_idx, b_name in enumerate(TF_BAND_NAMES, start=1):
            raw = ds.read(b_idx).astype(np.float32)
            fin = fp & np.isfinite(raw) & (raw > -1e30)
            filled = _fast_fill(raw, fin)
            _push(b_name, filled)
            if b_name in (
                "Mag_RTP",
                "tmi_hg",
                "tmi_vg",
                "geod_2ndinv",
                "geod_shearrate",
                "geod_dilaterate",
                "iso_grav_anom",
                "iso_grav_anom_hg",
                "depth_to_base_surf",
                "cond_surf",
                "det_elev",
                "det_elev_slope",
            ):
                saved[b_name] = filled

    _push("grav_hg_worm", saved["iso_grav_anom_hg"] - gaussian_filter(saved["iso_grav_anom_hg"], 8.0))
    _push("mag_hg_worm", saved["tmi_hg"] - gaussian_filter(saved["tmi_hg"], 8.0))
    base_grad = _grad_mag(saved["depth_to_base_surf"], 1.5)
    _push("basement_grad", base_grad)
    _push("basement_curv", saved["depth_to_base_surf"] - gaussian_filter(saved["depth_to_base_surf"], 8.0))
    cond_grad = _grad_mag(saved["cond_surf"], 1.5)
    _push("cond_grad", cond_grad)
    _push("det_elev_lrm", saved["det_elev"] - gaussian_filter(saved["det_elev"], 6.0))

    # 2. 1m 3DEP LiDAR scarp features
    with rasterio.open(ext_dir / "lidar_scarp_features_u8.tif") as ds:
        has_lidar_2d = (ds.read(12) > 0) & fp
        has_lidar_fp = has_lidar_2d.ravel()[fp_idx]
        _push("lidar_has_coverage", has_lidar_fp.astype(np.float32), is_fp_1d=True)
        lidar_cache: dict[str, np.ndarray] = {}
        for b_idx, b_name in enumerate(LIDAR_BAND_NAMES, start=1):
            v_fp = ds.read(b_idx).ravel()[fp_idx].astype(np.float32)
            v_fp[~has_lidar_fp] = np.nan
            _push(b_name, v_fp, is_fp_1d=True)
            if b_name in ("lidar_step_max", "lidar_lapneg_max", "lidar_lappos_max", "lidar_relief"):
                lidar_cache[b_name] = v_fp
        dipole = np.sqrt(np.maximum(0.0, lidar_cache["lidar_lapneg_max"] * lidar_cache["lidar_lappos_max"]))
        sharpness = lidar_cache["lidar_step_max"] / (lidar_cache["lidar_relief"] + 5.0)
        _push("lidar_crest_toe_dipole", dipole, is_fp_1d=True)
        _push("lidar_scarp_sharpness", sharpness, is_fp_1d=True)
        lidar_cache.clear()

    # 3. Seamless 10m 3DEP topographic breaklines
    topo_cache: dict[str, np.ndarray] = {}
    with rasterio.open(ext_dir / "topo_10m_derived_100m_u8.tif") as ds:
        for b_idx, b_name in enumerate(TOPO10_BAND_NAMES, start=1):
            q = ds.read(b_idx)
            fin = fp & (q > 0)
            filled = _fast_fill(q.astype(np.float32), fin)
            _push(b_name, filled)
            if b_name in ("topo10_hs_lineament", "topo10_curv_prof_absmax"):
                topo_cache[b_name] = filled
    _push("topo10_hs_dog", topo_cache["topo10_hs_lineament"] - gaussian_filter(topo_cache["topo10_hs_lineament"], 6.0))
    _push(
        "topo10_curv_dog",
        topo_cache["topo10_curv_prof_absmax"] - gaussian_filter(topo_cache["topo10_curv_prof_absmax"], 6.0),
    )
    topo_cache.clear()

    # 4. Fluvial tectonic geomorphology (chi, ksn, drainage area, zmean, knickpoints) + pluvial shoreline rejector
    with rasterio.open(ext_dir / "dem10_chi_100m_i16.tif") as ds:
        ksn_arr = None
        z_arr = None
        for b_idx, b_name in enumerate(CHI_BAND_NAMES, start=1):
            arr = _fast_fill(ds.read(b_idx).astype(np.float32), fp)
            _push(b_name, arr)
            if b_name == "chi_ksn_max":
                ksn_arr = arr
            elif b_name == "chi_zmean_m":
                z_arr = arr
    with rasterio.open(ext_dir / "dem10_chi_100m_u8.tif") as ds_u8:
        for b_idx, b_name in enumerate(CHI_U8_BAND_NAMES, start=1):
            arr = _fast_fill(ds_u8.read(b_idx).astype(np.float32), fp)
            _push(b_name, arr)
    assert ksn_arr is not None and z_arr is not None
    _push("chi_ksn_dog", ksn_arr - gaussian_filter(ksn_arr, 8.0))
    d_shore = np.minimum(
        np.abs(z_arr - 1332.0),
        np.minimum(np.abs(z_arr - 1463.0), np.abs(z_arr - 1552.0)),
    ).astype(np.float32)
    z_mean_g3 = gaussian_filter(z_arr, 3.0)
    z_std_300m = np.sqrt(np.maximum(0.0, gaussian_filter(z_arr * z_arr, 3.0) - z_mean_g3 * z_mean_g3)).astype(np.float32)
    z_lrm_400m = (z_arr - gaussian_filter(z_arr, 4.0)).astype(np.float32)
    _push("pluvial_shoreline_elev_dist_m", d_shore)
    _push("zmean_std_300m", z_std_300m)
    _push("zmean_lrm_400m", z_lrm_400m)
    del ksn_arr, z_arr, z_mean_g3, z_std_300m, z_lrm_400m

    # 5. GeoDAWN airborne gamma-ray spectrometry & upward-continued TMI alteration
    with rasterio.open(ext_dir / "geodawn_rad_u8.tif") as ds:
        rad_k = None
        for b_idx, b_name in enumerate(["rad_K", "rad_Th", "rad_U", "rad_TC"], start=1):
            q = ds.read(b_idx)
            arr = _fast_fill(q.astype(np.float32), fp & (q > 0))
            _push(b_name, arr)
            if b_name == "rad_K":
                rad_k = arr
    with rasterio.open(ext_dir / "geodawn_extensions_u8.tif") as ds:
        tmi_up = None
        for b_idx, b_name in enumerate(["ext_ThK", "ext_UK", "ext_UTh", "ext_TMI_up150"], start=1):
            q = ds.read(b_idx)
            arr = _fast_fill(q.astype(np.float32), fp & (q > 0))
            _push(b_name, arr)
            if b_name == "ext_TMI_up150":
                tmi_up = arr
    idx_cache.clear()
    del idx_fp
    assert rad_k is not None and tmi_up is not None
    rad_k_halo = (rad_k - gaussian_filter(rad_k, 10.0)).astype(np.float32)
    _push("rad_K_alteration_halo", rad_k_halo)
    _push("tmi_demagnetization_trough", gaussian_filter(tmi_up, 10.0) - tmi_up)

    # 6. Label-free hydrothermal conduits
    imp_therm = np.zeros(shape, dtype=np.float32)
    ws_count = 0
    ws_path = ext_dir / "gdr_wellspring_in_footprint.csv"
    with ws_path.open(newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None
        used_ws_cols = ("row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c")
        assert set(used_ws_cols).isdisjoint(FORBIDDEN_POINT_COLUMNS)
        for r in reader:
            rr, cc = int(r["row"]), int(r["col"])
            if not (0 <= rr < shape[0] and 0 <= cc < shape[1]):
                continue
            vals_t = []
            for k_col, base_t in (
                ("temp_c", 20.0),
                ("geothermquartz_c", 70.0),
                ("geothermchalc_c", 60.0),
                ("geothermcat_c", 75.0),
            ):
                s_val = r.get(k_col, "")
                if s_val and s_val != "nan":
                    try:
                        vals_t.append(max(0.0, float(s_val) - base_t))
                    except ValueError:
                        pass
            if vals_t:
                score_t = float(np.log1p(max(vals_t)))
                if score_t > imp_therm[rr, cc]:
                    imp_therm[rr, cc] = score_t
                ws_count += 1
    _push("gdr_thermal_upflow_s5", gaussian_filter(imp_therm, 5.0))
    _push("gdr_thermal_upflow_s16", gaussian_filter(imp_therm, 16.0))
    del imp_therm

    imp_dab, imp_pcnt = _parse_2m_probes_dbf(
        ext_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip", transform, shape
    )
    _push("probe2m_dab_s5", gaussian_filter(np.log1p(imp_dab), 5.0))
    _push("probe2m_dab_s14", gaussian_filter(np.log1p(imp_dab), 14.0))
    probe_sites = int((imp_pcnt > 0).sum())
    del imp_dab, imp_pcnt

    imp_paleo = np.zeros(shape, dtype=np.float32)
    paleo_zip = ext_dir / "paleo_geothermal_regional.zip"
    paleo_count = 0
    if paleo_zip.is_file():
        with zipfile.ZipFile(paleo_zip) as zf:
            cname = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            with io.TextIOWrapper(zf.open(cname), encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                lons, lats = [], []
                for r in reader:
                    try:
                        lons.append(float(r["Long_deg_NAD83"]))
                        lats.append(float(r["Lat_deg_NAD83"]))
                    except (KeyError, ValueError):
                        continue
        if lons:
            ux, uy = rio_transform("EPSG:4269", "EPSG:32611", lons, lats)
            rr, cc, _ = _utm_to_rc(ux, uy, transform, shape)
            imp_paleo[rr, cc] = 1.0
            paleo_count = int(rr.size)
    _push("paleo_sinter_tufa_s6", gaussian_filter(imp_paleo, 6.0))
    _push("paleo_sinter_tufa_s18", gaussian_filter(imp_paleo, 18.0))
    del imp_paleo

    imp_vent = np.zeros(shape, dtype=np.float32)
    vent_count = 0
    with (ext_dir / "gdr_volcanic_vents_in_footprint.csv").open(newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rr, cc = int(r["row"]), int(r["col"])
            if 0 <= rr < shape[0] and 0 <= cc < shape[1]:
                imp_vent[rr, cc] = 1.0
                vent_count += 1
    _push("quaternary_volcanic_vent_s16", gaussian_filter(imp_vent, 16.0))
    del imp_vent

    # =========================================================================
    # 7. NOVEL GEMSDOE74 GEOPHYSICAL OPERATORS (Hypotheses H74-R1 .. H74-R5)
    # =========================================================================
    # H74-R1a (C1): Flight-line notch de-striped Magnetic Analytic-Signal Tilt Zero-Crossing Ridge
    rtp_clean = _destripe_ew_flightline(saved["Mag_RTP"])
    mx, my, mag_hgrad_clean = _grad_vec(rtp_clean, sigma=1.5)
    vdr_clean = _destripe_ew_flightline(saved["tmi_vg"])
    tdr = np.arctan2(vdr_clean, mag_hgrad_clean + 1e-3).astype(np.float32)
    hgrad_scale = float(np.percentile(mag_hgrad_clean[fp], 75.0)) + 1e-3
    h74_c1_tdr_ridge = (
        np.exp(-np.abs(tdr) / 0.28) * np.tanh(mag_hgrad_clean / hgrad_scale)
    ).astype(np.float32)
    _push("h74_c1_destriped_tdr_ridge", h74_c1_tdr_ridge)

    # H74-R1b (C1): Upward-continuation 150m magnetic gradient attenuation ratio
    up_grad = _grad_mag(tmi_up, sigma=1.5)
    up_scale = float(np.percentile(up_grad[fp], 75.0)) + 1e-3
    h74_c1_atten = (
        np.log1p(mag_hgrad_clean / hgrad_scale) - 0.65 * np.log1p(up_grad / up_scale)
    ).astype(np.float32)
    _push("h74_c1_mag_upward_atten", h74_c1_atten)
    del rtp_clean, vdr_clean, tdr, tmi_up, up_grad

    # H74-R2: Poisson Gravity-Magnetic Vector Strike Concordance
    gx, gy, grav_hgrad = _grad_vec(saved["iso_grav_anom"], sigma=2.0)
    cos_gm = (mx * gx + my * gy) / (mag_hgrad_clean * grav_hgrad + 1e-5)
    g_scale = float(np.percentile(grav_hgrad[fp], 75.0)) + 1e-3
    h74_r2_poisson = (
        (cos_gm * cos_gm) * np.sqrt(np.log1p(mag_hgrad_clean / hgrad_scale) * np.log1p(grav_hgrad / g_scale))
    ).astype(np.float32)
    _push("h74_r2_poisson_grav_mag_concordance", h74_r2_poisson)
    del mx, my, mag_hgrad_clean, gx, gy, grav_hgrad, cos_gm

    # H74-R3: Transtensional Coulomb Strain-Rate Dilation Envelope
    sr = np.maximum(0.0, saved["geod_shearrate"])
    dr = np.maximum(0.0, saved["geod_dilaterate"])
    inv2 = np.maximum(0.0, saved["geod_2ndinv"])
    sr_s = sr / (float(np.percentile(sr[fp], 75.0)) + 1e-6)
    dr_s = dr / (float(np.percentile(dr[fp], 75.0)) + 1e-6)
    inv_s = inv2 / (float(np.percentile(inv2[fp], 75.0)) + 1e-6)
    bx, by, b_mag = _grad_vec(saved["depth_to_base_surf"], sigma=2.0)
    # Strike angle from basement gradient normal: tangent = (-by, bx)
    # Walker Lane / Basin & Range optimal transtensional strikes: NNE (~30 deg) & NNW (~-25 deg from N)
    strike_az = np.arctan2(-by, bx + 1e-7)  # angle from East
    # NNE (~60 deg from E = 1.05 rad) or NNW (~115 deg from E = 2.01 rad)
    align_transtens = np.maximum(
        np.cos(strike_az - 1.05) ** 2,
        np.cos(strike_az - 2.01) ** 2,
    ).astype(np.float32)
    h74_r3_coulomb = (
        np.log1p(0.50 * sr_s + 0.30 * dr_s + 0.20 * inv_s) * (0.5 + 0.5 * align_transtens)
    ).astype(np.float32)
    _push("h74_r3_transtensional_coulomb", h74_r3_coulomb)
    del sr, dr, inv2, sr_s, dr_s, inv_s, align_transtens

    # H74-R4 (Real H74-1): Real-Data Basement-Step Hessian Ridge under Piedmont Surface Quiescence
    base_hess = _hessian_ridge_multiscale(base_grad, sigmas=(1.2, 2.5, 4.0))
    bh_scale = float(np.percentile(base_hess[fp], 85.0)) + 1e-4
    dep = np.maximum(0.0, saved["depth_to_base_surf"])
    # Piedmont basin cover window: peaks between 120 m and 1100 m sediment thickness
    cover_gate = (np.clip((dep - 60.0) / 160.0, 0.0, 1.0) * np.exp(-np.maximum(0.0, dep - 1100.0) / 1800.0)).astype(np.float32)
    slp = np.maximum(0.0, saved["det_elev_slope"])
    slp_p65 = float(np.percentile(slp[fp], 65.0)) + 1e-3
    quiescence_gate = np.exp(-slp / slp_p65).astype(np.float32)
    shore_gate = np.clip(d_shore / 25.0, 0.15, 1.0).astype(np.float32)
    h74_r4_basement_quiescence = (
        np.tanh(base_hess / bh_scale) * (0.35 + 0.65 * cover_gate * quiescence_gate) * shore_gate
    ).astype(np.float32)
    _push("h74_r4_real_basement_quiescence_ridge", h74_r4_basement_quiescence)
    del base_hess, dep, cover_gate, slp, quiescence_gate, shore_gate, d_shore

    # H74-R5: Magnetotelluric Clay-Cap Breach & K/Th Potassic Strike Concordance
    cx, cy, c_mag = _grad_vec(saved["cond_surf"], sigma=2.0)
    cos_cb = (cx * bx + cy * by) / (c_mag * b_mag + 1e-5)
    c_scale = float(np.percentile(c_mag[fp], 75.0)) + 1e-4
    b_scale = float(np.percentile(b_mag[fp], 75.0)) + 1e-4
    k_pos = np.maximum(0.0, rad_k_halo)
    k_scale = float(np.percentile(k_pos[fp], 75.0)) + 1e-4
    h74_r5_mt_breach = (
        (cos_cb * cos_cb)
        * np.sqrt(np.log1p(c_mag / c_scale) * np.log1p(b_mag / b_scale))
        * (1.0 + 0.35 * np.tanh(k_pos / k_scale))
    ).astype(np.float32)
    _push("h74_r5_mt_claycap_breach_concordance", h74_r5_mt_breach)
    del cx, cy, c_mag, bx, by, b_mag, cos_cb, rad_k, rad_k_halo, k_pos
    saved.clear()

    # Construct unsupervised Experiment E1 composite surface from H74-R1..R5 on the real footprint
    def _norm01(arr: np.ndarray) -> np.ndarray:
        v = arr[fp]
        lo, hi = float(np.percentile(v, 5.0)), float(np.percentile(v, 99.5))
        return np.where(fp, np.clip((arr - lo) / (hi - lo + 1e-6), 0.0, 1.0), 0.0).astype(np.float32)

    e1_surf = (
        0.30 * _norm01(h74_r4_basement_quiescence)
        + 0.25 * _norm01(h74_c1_tdr_ridge)
        + 0.15 * _norm01(h74_c1_atten)
        + 0.12 * _norm01(h74_r2_poisson)
        + 0.10 * _norm01(h74_r3_coulomb)
        + 0.08 * _norm01(h74_r5_mt_breach)
    ).astype(np.float32)
    np.save(e1_path, e1_surf)

    assert col_ptr == total_cols, f"Expected {total_cols} columns, wrote {col_ptr}"
    X.flush()
    meta = {
        "n_footprint_pixels": n_fp,
        "n_features": total_cols,
        "novel_gems74_features": [
            "h74_c1_destriped_tdr_ridge",
            "h74_c1_mag_upward_atten",
            "h74_r2_poisson_grav_mag_concordance",
            "h74_r3_transtensional_coulomb",
            "h74_r4_real_basement_quiescence_ridge",
            "h74_r5_mt_claycap_breach_concordance",
        ],
        "forbidden_columns_blocked": sorted(FORBIDDEN_POINT_COLUMNS),
        "sgmc_in_feature_matrix": False,
        "historical_predictions_in_feature_matrix": False,
        "point_records_ingested": {
            "gdr_wellspring_records": ws_count,
            "probe_2m_cells": probe_sites,
            "paleo_sinter_travertine_tufa_records": paleo_count,
            "quaternary_volcanic_vents": vent_count,
        },
    }
    meta_path.write_text(
        json.dumps(
            {
                "n_features": total_cols,
                "n_footprint_pixels": n_fp,
                "feature_names": names,
                "meta": meta,
            },
            indent=2,
        )
        + "\n"
    )
    return X, names, has_lidar_fp, meta, e1_surf


def compute_fold_safe_mechanics(visible_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute strictly fold-safe crack-tip propagation lobes & relay step-over density."""
    if not visible_mask.any():
        z = np.zeros(visible_mask.shape, dtype=np.float32)
        return z, z
    vis_b = visible_mask > 0
    comp, _ = ndi_label(vis_b, structure=np.ones((3, 3), dtype=int))
    sizes = np.bincount(comp.ravel())
    major = vis_b & (sizes[comp] >= 8)

    nb = convolve(major.astype(np.uint8), np.ones((3, 3), dtype=np.uint8), mode="constant", cval=0)
    tips = major & ((nb == 2) | (nb == 3))

    sm = gaussian_filter(major.astype(np.float32), sigma=2.5)
    gy, gx = np.gradient(sm)
    norm = np.hypot(gx, gy) + 1e-6
    tx, ty = -gx / norm, gy / norm

    ty_idx, tx_idx = np.nonzero(tips)
    lobe = np.zeros(visible_mask.shape, dtype=np.float32)
    for step in (3.0, 6.0, 9.0, 12.0, 15.0, 18.0):
        w = float(np.exp(-0.5 * (step / 11.0) ** 2))
        for sgn in (-1.0, 1.0):
            ry = np.clip(np.round(ty_idx + sgn * step * ty[ty_idx, tx_idx]).astype(np.int64), 0, visible_mask.shape[0] - 1)
            rx = np.clip(np.round(tx_idx + sgn * step * tx[ty_idx, tx_idx]).astype(np.int64), 0, visible_mask.shape[1] - 1)
            np.maximum.at(lobe, (ry, rx), w)
    tip_field = gaussian_filter(lobe, sigma=2.5).astype(np.float32)

    d_vis = distance_transform_edt(~visible_mask).astype(np.float32)
    collar_taper = np.clip((d_vis - 2.2) / 2.0, 0.0, 1.0).astype(np.float32)
    relay_field = (
        np.maximum(0.0, gaussian_filter(major.astype(np.float32), 9.0) - 0.55 * gaussian_filter(major.astype(np.float32), 2.5))
        * collar_taper
    ).astype(np.float32)
    return tip_field * collar_taper, relay_field


def peak_nms_emit(
    surface: np.ndarray,
    allowed_mask: np.ndarray,
    n_dots: int = 37654,
) -> np.ndarray:
    """Select exact ``n_dots`` binary 1.0 pixels via 7x7 peak NMS (fallback 5x5 -> 3x3)."""
    s = np.where(allowed_mask & np.isfinite(surface), surface.astype(np.float64), -1.0)
    yy, xx = np.indices(surface.shape, dtype=np.float64)
    s_tie = s + 1e-12 * (yy * 0.00031 + xx * 0.00017)

    out = np.zeros(surface.shape, dtype=np.float32)
    remaining = int(n_dots)
    avail = allowed_mask & (surface > 0)

    for win in (7, 5, 3, 1):
        if remaining <= 0:
            break
        cur = np.where(avail, s_tie, -2.0)
        if win > 1:
            is_peak = avail & (cur == maximum_filter(cur, size=win, mode="constant", cval=-3.0))
        else:
            is_peak = avail
        cand_idx = np.flatnonzero(is_peak)
        if cand_idx.size == 0:
            continue
        scores = s_tie.ravel()[cand_idx]
        if cand_idx.size > remaining:
            top = np.argpartition(scores, -remaining)[-remaining:]
            top = top[np.argsort(-scores[top])]
            chosen = cand_idx[top]
        else:
            chosen = cand_idx[np.argsort(-scores)]
        out.ravel()[chosen] = 1.0
        avail.ravel()[chosen] = False
        remaining -= int(chosen.size)

    assert int((out > 0.5).sum()) == int(n_dots)
    return out


def submodular_spaced_dti_emit(
    prob: np.ndarray,
    allowed_mask: np.ndarray,
    n_dots: int = 37654,
    fp_penalty_weight: float = 0.06,
    candidate_pool: int = 1100000,
    min_spacing_px: float = 2.9,
) -> np.ndarray:
    """Lazy-greedy Minoux submodular maximizer of expected DTI kernel coverage with inter-dot spacing.

    Maximizes marginal expected weighted true-positive gain over the 29-offset R=300 m (3.0 px)
    triangular kernel while enforcing a minimum Euclidean inter-dot spacing ``min_spacing_px``
    (default 2.1 px = 210 m) so dots step along fault corridors without redundant clustering.
    """
    H, W = prob.shape
    pad = 4
    q_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=np.float64)
    q_pad[pad : pad + H, pad : pad + W] = np.clip(
        np.where(np.isfinite(prob), prob, 0.0), 0.0, 1.0
    )
    cov_pad = np.zeros_like(q_pad)
    blocked_pad = np.zeros((H + 2 * pad, W + 2 * pad), dtype=bool)

    dy = metric.OFF_DY.tolist()
    dx = metric.OFF_DX.tolist()
    kw = metric.OFF_K.tolist()
    n_off = len(kw)

    # Precompute exclusion offsets for min_spacing_px
    r_excl = int(np.floor(min_spacing_px))
    excl_dy, excl_dx = [], []
    for ey in range(-r_excl, r_excl + 1):
        for ex in range(-r_excl, r_excl + 1):
            if float(np.hypot(ey, ex)) <= min_spacing_px + 1e-6:
                excl_dy.append(ey)
                excl_dx.append(ex)
    n_excl = len(excl_dy)

    init_tp = np.zeros((H, W), dtype=np.float64)
    q_self = np.zeros((H, W), dtype=np.float64)
    for oy, ox, k_val in zip(dy, dx, kw):
        sub = q_pad[pad + oy : pad + oy + H, pad + ox : pad + ox + W]
        init_tp += k_val * sub
        np.maximum(q_self, k_val * sub, out=q_self)

    pen_arr = fp_penalty_weight * (1.0 - q_self)
    u0 = init_tp - pen_arr

    valid_idx = np.flatnonzero(allowed_mask & (init_tp > 0))
    if valid_idx.size > candidate_pool:
        u_sub = u0.ravel()[valid_idx]
        keep = np.argpartition(u_sub, -candidate_pool)[-candidate_pool:]
        valid_idx = valid_idx[keep]

    ys = (valid_idx // W + pad).tolist()
    xs = (valid_idx % W + pad).tolist()
    pens = pen_arr.ravel()[valid_idx].tolist()
    u_vals = u0.ravel()[valid_idx].tolist()

    heap: list[tuple[float, int]] = [(-u_vals[i], i) for i in range(len(u_vals))]
    heapq.heapify(heap)

    out = np.zeros((H, W), dtype=np.float32)
    selected = 0

    while selected < n_dots and heap:
        neg_upper, i = heapq.heappop(heap)
        cy = ys[i]
        cx = xs[i]
        if blocked_pad[cy, cx]:
            continue
        gain = 0.0
        for m in range(n_off):
            ny = cy + dy[m]
            nx = cx + dx[m]
            k_m = kw[m]
            cur_c = cov_pad[ny, nx]
            if k_m > cur_c:
                gain += q_pad[ny, nx] * (k_m - cur_c)
        exact_u = gain - pens[i]

        if not heap or (-exact_u <= heap[0][0] + 1e-15):
            out[cy - pad, cx - pad] = 1.0
            for m in range(n_off):
                ny = cy + dy[m]
                nx = cx + dx[m]
                k_m = kw[m]
                if k_m > cov_pad[ny, nx]:
                    cov_pad[ny, nx] = k_m
            for e_i in range(n_excl):
                blocked_pad[cy + excl_dy[e_i], cx + excl_dx[e_i]] = True
            selected += 1
        else:
            heapq.heappush(heap, (-exact_u, i))

    if selected < n_dots:
        rem = int(n_dots) - selected
        rem_mask = allowed_mask & (out < 0.5) & (~blocked_pad[pad : pad + H, pad : pad + W])
        if int(rem_mask.sum()) < rem:
            rem_mask = allowed_mask & (out < 0.5)
        extra = peak_nms_emit(u0, rem_mask, n_dots=rem)
        out = np.maximum(out, extra)

    assert int((out > 0.5).sum()) == int(n_dots), f"Selected {int((out > 0.5).sum())} != {n_dots}"
    return out
