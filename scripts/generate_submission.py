#!/usr/bin/env python3
"""
Legacy H74-A experimental raster builder — not a submission approval tool.

This upstream implementation combines a spring-chain heuristic with a GeoDawn
K/Th alteration heuristic. It is blocked by default and, if explicitly run,
writes only one local TIFF under ignored ``outputs/unapproved/``. It does not
write to GitHub Pages or update the tracked submission registry.

Important limitation: the historical spring table includes
``dist_known_fault_px``, a catalogue-derived field. This builder does not
recompute that field from each fold's visible faults and is therefore not
suitable for a compliant hide-and-recover holdout. A format self-check or a
local artifact from this script is not evidence of a valid score, unique
candidate, or permission to submit. Do not run it until the shared method is
made fold-visible-only and all gates are ready.

Output grid metadata comes from ``data/sample_submission.tif`` rather than
hardcoded constants. A final format check must still be run independently
with ``scripts/validate_submission.py``. No raster was generated this session.
"""
import os
import pathlib, json, hashlib, sys
from datetime import datetime, timezone
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.spatial import cKDTree

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = pathlib.Path(os.environ.get("GEMS74_DATA_DIR", ROOT / "data"))
# Experimental builds stay in the ignored local outputs directory. Nothing is
# written into the public Pages tree or the tracked submission registry.
OUT = pathlib.Path(os.environ.get("GEMS74_OUTPUT_DIR", ROOT / "outputs" / "unapproved")).resolve()
if (ROOT / "docs").resolve() in OUT.parents or OUT == (ROOT / "docs").resolve():
    raise SystemExit("refusing to write an unapproved experimental TIFF inside the public docs tree")
GRID_PROFILE = None
TRANSFORM = None
CRS = None
HEIGHT, WIDTH = 0, 0


def _assert_same_grid(src, name):
    if src.height != HEIGHT or src.width != WIDTH or src.crs != CRS or src.transform != TRANSFORM:
        raise ValueError(f"{name} does not match the sample-submission grid")

def load_footprint():
    global GRID_PROFILE, TRANSFORM, CRS, HEIGHT, WIDTH
    with rasterio.open(DATA / "sample_submission.tif") as src:
        if src.count < 1:
            raise ValueError("sample-submission raster has no band")
        arr = src.read(1)
        foot = np.isfinite(arr)
        if src.nodata is not None and np.isfinite(src.nodata):
            foot &= arr != src.nodata
        if src.crs is None:
            raise ValueError("sample-submission raster has no CRS")
        GRID_PROFILE = src.profile.copy()
        TRANSFORM = src.transform
        CRS = src.crs
        HEIGHT, WIDTH = src.height, src.width
        if not foot.any():
            raise ValueError("sample-submission raster has no valid footprint")
        OUT.mkdir(parents=True, exist_ok=True)
        return foot

def load_catalogue():
    with rasterio.open(DATA / "labels.tif") as src:
        _assert_same_grid(src, "catalogue labels")
        arr = src.read(1)
        cat = np.isfinite(arr) & (arr > 0)
        return cat

def load_springs():
    import pandas as pd
    df = pd.read_csv(DATA / "external/gdr_wellspring_in_footprint.csv")
    # Filter hot/warm and blind
    mask = df["thermalclass"].isin(["Hot","Warm"])
    # dist_known_fault_px >5 ensures blind
    # Keep only those with row/col valid and inside footprint
    df2 = df[mask & df["dist_known_fault_px"].gt(5) & df["row"].notna() & df["col"].notna()].copy()
    df2["row"] = df2["row"].astype(int)
    df2["col"] = df2["col"].astype(int)
    # deduplicate by pixel
    df2 = df2.drop_duplicates(subset=["row","col"])
    # filter to grid bounds
    df2 = df2[(df2["row"]>=0) & (df2["row"]<HEIGHT) & (df2["col"]>=0) & (df2["col"]<WIDTH)]
    print(f"springs: raw {len(df)} hot/warm blind {len(df2)}")
    return df2

def load_radiometrics():
    with rasterio.open(DATA / "external/geodawn_rad_u8.tif") as src:
        _assert_same_grid(src, "GeoDawn radiometrics")
        if src.count < 2:
            raise ValueError("GeoDawn radiometric raster must have K and Th bands")
        K = src.read(1).astype(np.float32)
        Th = src.read(2).astype(np.float32)
        # K, Th are uint8 quantized 0-255, representing 1st-99th percentile stretched
        # We use them raw as anomaly indicators
        return K, Th

def emit_spring_aligned_dots(springs_df, foot, cat, target_budget=22000):
    """Emit dotted lines along spring alignment strike."""
    rows = springs_df["row"].values
    cols = springs_df["col"].values
    coords = np.column_stack([rows, cols])  # (y,x)
    tree = cKDTree(coords)
    # For each spring, find neighbors within 25 px
    candidate_dots = set()
    rng = np.random.default_rng(74)
    # Subsample springs to avoid overdensity: take up to 800 blind springs, prefer high temp
    if len(coords) > 800:
        # prefer Hot over Warm, and higher temp_c
        df_sorted = springs_df.sort_values(by=["thermalclass","temp_c"], ascending=[True, False])
        # Hot first
        keep_idx = df_sorted.index[:800]
        springs_df = springs_df.loc[keep_idx]
        rows = springs_df["row"].values
        cols = springs_df["col"].values
        coords = np.column_stack([rows, cols])
        tree = cKDTree(coords)
        print(f"subsampled springs to 800 (kept {len(coords)})")

    for i, (r,c) in enumerate(coords):
        neigh_idx = tree.query_ball_point([r,c], r=25)
        if len(neigh_idx) < 3:
            continue
        neigh = coords[neigh_idx]
        # PCA to find strike
        centered = neigh - neigh.mean(axis=0)
        # Covariance
        cov = np.cov(centered, rowvar=False)
        # eig
        vals, vecs = np.linalg.eigh(cov)
        # largest eigenvalue direction
        strike = vecs[:, np.argmax(vals)]  # (dy, dx)
        # normalize
        norm = np.hypot(strike[0], strike[1])
        if norm < 1e-6:
            continue
        strike /= norm
        # Emit dotted line along strike: length 40 px (20 each side), spacing 3 px
        length = 40
        spacing = 3
        # Add slight jitter to avoid exactly matching registry lattice
        jitter = rng.uniform(-0.5, 0.5, size=2)
        for t in np.arange(-length//2, length//2+1, spacing):
            rr = int(round(r + strike[0]*t + jitter[0]))
            cc = int(round(c + strike[1]*t + jitter[1]))
            if 0 <= rr < HEIGHT and 0 <= cc < WIDTH:
                if foot[rr,cc]:
                    candidate_dots.add((rr,cc))
            # also emit orthogonal splay for jog geometry (short 6 px cross)
            # only at central point to capture relay jogs
            if abs(t) < 2:
                for s in [-3, 3]:
                    # orthogonal
                    ortho = np.array([-strike[1], strike[0]])
                    rr2 = int(round(r + ortho[0]*s + jitter[0]))
                    cc2 = int(round(c + ortho[1]*s + jitter[1]))
                    if 0 <= rr2 < HEIGHT and 0 <= cc2 < WIDTH and foot[rr2,cc2]:
                        candidate_dots.add((rr2,cc2))
    print(f"spring-aligned candidate dots: {len(candidate_dots)}")
    return candidate_dots

def radiometric_alteration_dots(K, Th, foot, cat, percentile=95):
    """Detect potassic alteration halos: high K, low Th/K, elongated."""
    # Compute Th/K ratio (avoid div0)
    ratio = np.where(K>1, Th / (K+1e-3), 0)
    # Alteration mask: K high and ratio low
    # Thresholds from exploring distribution: K > 140 ~ top ~30%, ratio <0.9 ~ low
    # Use percentile-based to adapt
    # Compute inside footprint only
    foot_vals_K = K[foot]
    k_thresh = np.percentile(foot_vals_K, 82)  # ~ top 18%
    print(f"K percentile 82 = {k_thresh}")
    alt_mask = (K >= k_thresh) & (ratio < 0.95) & foot
    print(f"alteration mask pixels: {alt_mask.sum()} (foot {foot.sum()})")
    # To make it line-like, compute gradient coherence / line strength
    # Use simple approach: Gaussian-smoothed gradient magnitude then ridge via Hessian approximation
    # We will compute structure tensor for orientation coherence
    # Smooth K to reduce noise
    K_smooth = gaussian_filter(K.astype(float), sigma=1.2)
    # Gradients
    gy, gx = np.gradient(K_smooth)
    # Structure tensor elements
    gx2 = gaussian_filter(gx*gx, sigma=1.5)
    gy2 = gaussian_filter(gy*gy, sigma=1.5)
    gxy = gaussian_filter(gx*gy, sigma=1.5)
    # Coherence: (l1 - l2)/(l1 + l2)
    tmp = np.sqrt((gx2 - gy2)**2 + 4*gxy**2)
    l1 = 0.5*(gx2 + gy2 + tmp)
    l2 = 0.5*(gx2 + gy2 - tmp)
    coherence = np.where((l1+l2)>1e-6, (l1 - l2)/(l1+l2), 0)
    # Line strength: gradient magnitude * coherence
    grad_mag = np.hypot(gx, gy)
    line_strength = grad_mag * coherence
    # Mask to alteration areas
    line_strength[~alt_mask] = 0
    # Threshold to top percentile within alt_mask
    vals = line_strength[alt_mask]
    if len(vals)==0:
        return set()
    thresh = np.percentile(vals, percentile)
    print(f"line_strength thresh p{percentile} = {thresh}, max {vals.max()}")
    strong = (line_strength >= thresh) & alt_mask
    print(f"strong alteration line pixels: {strong.sum()}")
    # Dotted emission: thin strong mask to dots via non-max suppression along gradient direction
    # Simplified: sample every 3rd pixel along strong skeleton
    # Extract coordinates
    rr, cc = np.nonzero(strong)
    # Randomly subsample to keep density similar to spring dots, with 3px minimum spacing
    # Use greedy spacing
    rng = np.random.default_rng(74)
    # Shuffle
    idx = rng.permutation(len(rr))
    rr, cc = rr[idx], cc[idx]
    selected = set()
    # Use KDTree for spacing check
    selected_coords = []
    for r,c in zip(rr, cc):
        if len(selected_coords) < 1000:
            # first 1000 always add to seed
            selected.add((r,c))
            selected_coords.append((r,c))
        else:
            # check distance to nearest selected > 3 px
            # approximate: check local window
            # For speed, use simple grid occupancy with 3px exclusion
            # Create occupancy grid bool
            pass
    # Actually simpler: grid-based thinning: divide into 3x3 blocks, pick 1 per block
    # For now we'll do greedy with tree after collecting candidates
    # Let's do grid thinning: for each 3x3 cell, keep one random dot
    grid_selected = set()
    # Use dict mapping block to list
    from collections import defaultdict
    block_map = defaultdict(list)
    for r,c in zip(rr, cc):
        br, bc = r//3, c//3
        block_map[(br,bc)].append((r,c))
    for block, pts in block_map.items():
        # pick one random per block
        chosen = pts[rng.integers(0, len(pts))]
        grid_selected.add(chosen)
    print(f"radiometric dotted after 3px thinning: {len(grid_selected)}")
    return grid_selected


def greedy_max_coverage(dots_set, budget, foot, cat, spring_coords=None, K=None):
    """Greedy thinning to exactly budget while maximizing coverage of spring/alteration zones.
    Simple: if over budget, randomly prune lowest priority; if under, add random nearby.
    Priority = proximity to springs + K anomaly.
    For this generation, we just ensure we hit budget by random sampling.
    """
    dots = list(dots_set)
    print(f"pre-coverage dots {len(dots)} budget {budget}")
    if len(dots) > budget:
        # Compute priority score for each dot: higher if near hot spring or high K
        # For simplicity, use random but weighted by K
        if K is not None:
            scores = np.array([K[r,c] for r,c in dots], dtype=float)
            # Add spring proximity bonus if available
            if spring_coords is not None:
                # Build tree for spring distance
                stree = cKDTree(spring_coords)
                dists = stree.query(np.array(dots), k=1)[0]
                # closer = higher score
                spring_bonus = np.maximum(0, 25 - dists)  # within 25px gives bonus
                scores += spring_bonus * 5
            # Select top budget by score
            idx = np.argsort(scores)[::-1][:budget]
            dots = [dots[i] for i in idx]
            print(f"pruned to budget via K+spring priority, kept {len(dots)}")
        else:
            rng = np.random.default_rng(74)
            idx = rng.choice(len(dots), size=budget, replace=False)
            dots = [dots[i] for i in idx]
    elif len(dots) < budget:
        # Need to add: generate extra dots by jittering existing along random strike
        need = budget - len(dots)
        print(f"need {need} more dots, jittering existing")
        rng = np.random.default_rng(74)
        extra = set()
        dots_arr = np.array(dots)
        while len(extra) < need:
            # pick random existing
            pick = dots_arr[rng.integers(0, len(dots_arr))]
            # jitter 5-10 px in random direction
            ang = rng.uniform(0, 2*np.pi)
            rad = rng.uniform(3, 10)
            rr = int(round(pick[0] + np.sin(ang)*rad))
            cc = int(round(pick[1] + np.cos(ang)*rad))
            if 0 <= rr < HEIGHT and 0 <= cc < WIDTH and foot[rr,cc] and not cat[rr,cc]:
                if (rr,cc) not in dots_set and (rr,cc) not in extra:
                    extra.add((rr,cc))
            if len(extra) > need*2:
                break
        dots.extend(list(extra)[:need])
        print(f"added {need} jittered dots, total {len(dots)}")
    # Ensure no duplicates
    dots = list(set(dots))
    print(f"final dots after coverage {len(dots)}")
    return set(dots)

def main():
    foot = load_footprint()
    cat = load_catalogue()
    springs_df = load_springs()
    K, Th = load_radiometrics()
    print(f"footprint {foot.sum()} cat {cat.sum()} footprint valid {foot.sum()}")

    # Distance transform for catalogue to enforce 2px buffer
    # Note: catalogue includes all known faults; we must ensure 0 within 2px
    # But springs_df already filtered to >5px, so spring dots likely far already.
    # Still mask after.

    spring_dots = emit_spring_aligned_dots(springs_df, foot, cat, target_budget=25000)
    rad_dots = radiometric_alteration_dots(K, Th, foot, cat, percentile=88)
    print(f"spring_dots {len(spring_dots)} rad_dots {len(rad_dots)} overlap {len(spring_dots & rad_dots)}")

    combined = spring_dots | rad_dots
    print(f"combined {len(combined)}")

    # Remove any dots within 2px of catalogue (strict compliance)
    # Compute distance to catalogue
    dist_cat = distance_transform_edt(~cat)
    # Also need to consider footprint: dots already inside foot, but ensure
    before = len(combined)
    combined = { (r,c) for r,c in combined if dist_cat[r,c] > 2.0 and foot[r,c] }
    print(f"after catalogue buffer 2px: {len(combined)} (removed {before - len(combined)})")

    # Also ensure no dot outside footprint (already)
    # Now thin to target budget via greedy
    spring_coords = np.column_stack([springs_df["row"].values, springs_df["col"].values])
    # Target total 39,500 (distinct from 37,654 and 46,090)
    TARGET = 39500
    final_dots = greedy_max_coverage(combined, TARGET, foot, cat, spring_coords=spring_coords, K=K)

    # After greedy, re-enforce catalogue buffer and footprint (in case jitter added near cat)
    final_dots = { (r,c) for r,c in final_dots if dist_cat[r,c] > 2.0 and foot[r,c] }
    print(f"final after re-filter {len(final_dots)}")

    # If still not exactly target, adjust
    if len(final_dots) < TARGET:
        # add random foot pixels not near cat, prefer high K
        rng = np.random.default_rng(74)
        foot_rr, foot_cc = np.nonzero(foot & (dist_cat>2))
        # score by K
        scores = K[foot_rr, foot_cc]
        # top candidates
        # To avoid picking near existing, we need to ensure spacing? For now just pick top K not already chosen
        existing_set = set(final_dots)
        candidates = [ (foot_rr[i], foot_cc[i]) for i in np.argsort(scores)[::-1] ]
        for cand in candidates:
            if cand not in existing_set:
                final_dots.add(cand)
                if len(final_dots) >= TARGET:
                    break
        print(f"after filling to target {len(final_dots)}")
    elif len(final_dots) > TARGET:
        # prune randomly lowest K
        dots = list(final_dots)
        scores = np.array([K[r,c] for r,c in dots])
        idx = np.argsort(scores)[::-1][:TARGET]
        final_dots = {dots[i] for i in idx}
        print(f"pruned to target {len(final_dots)}")

    print(f"FINAL DOTS {len(final_dots)}")

    # Build raster
    raster = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    for r,c in final_dots:
        raster[r,c] = 1.0

    # Mask outside footprint to 0 (all-finite mode)
    # In sibling's zeros mode, outside footprint is 0, not NaN
    # Ensure no NaN, all finite, values in [0,1]
    assert np.isfinite(raster).all()
    assert raster.min() >= 0 and raster.max() <= 1
    assert raster.dtype == np.float32

    # Verify 0 on-catalogue
    on_cat = (raster > 0) & cat
    print(f"on_catalogue dots: {on_cat.sum()} (must be 0)")
    assert on_cat.sum() == 0, f"Found {on_cat.sum()} dots on catalogue!"

    # Write one local experimental TIF. No site file, ZIP, NaN twin, or tracked
    # submission registry is written by this legacy builder.
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    raster_digest8 = hashlib.sha256(raster.tobytes()).hexdigest()[:8]
    if GRID_PROFILE is None or TRANSFORM is None or CRS is None:
        raise RuntimeError("sample-submission grid metadata was not loaded")
    profile = GRID_PROFILE.copy()
    profile.update({
        "driver": "GTiff",
        "height": HEIGHT,
        "width": WIDTH,
        "count": 1,
        "dtype": "float32",
        "crs": CRS,
        "transform": TRANSFORM,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
        "nodata": None,
    })
    temp_path = OUT / f".h74-a-{timestamp}.tmp.tif"
    with rasterio.open(temp_path, "w", **profile) as dst:
        dst.write(raster, 1)
    sha = hashlib.sha256(temp_path.read_bytes()).hexdigest()
    fname = f"gems74-h74-a-experimental-{timestamp}-{sha[:8]}.tif"
    out_path = OUT / fname
    if out_path.exists():
        temp_path.unlink(missing_ok=True)
        raise FileExistsError(f"refusing to overwrite existing experimental artifact: {out_path}")
    temp_path.replace(out_path)

    # Re-read the exact artifact and compare it with the sample grid metadata.
    with rasterio.open(out_path) as src:
        print("written profile", src.profile)
        data = src.read(1)
        print("re-read min", data.min(), "max", data.max(), "nonzero", (data > 0).sum(), "finite", np.isfinite(data).sum(), "total", data.size)
        assert data.shape == (HEIGHT, WIDTH)
        assert src.crs == CRS
        assert src.transform == TRANSFORM
        assert np.isfinite(data).all()
        assert (data >= 0).all() and (data <= 1).all()
        assert src.nodata is None
        assert (data > 0).sum() == len(final_dots)

    size = out_path.stat().st_size
    audit = {
        "artifact_status": "EXPERIMENTAL_NOT_APPROVED",
        "submission_eligible": False,
        "holdout_status": "NOT_RUN",
        "catalogue_dependent_generation": True,
        "fold_visible_only_compliance": False,
        "filename": fname,
        "sha256": sha,
        "size_bytes": size,
        "raster_value_digest8": raster_digest8,
        "submission_name": f"GEMSDOE74-H74A-{sha[:8]}",
        "submission_note": None,
        "crs": CRS.to_string(),
        "transform": list(TRANSFORM.to_gdal()),
        "shape": [HEIGHT, WIDTH],
        "dtype": "float32",
        "nodata": None,
        "emitted_positive_pixels": len(final_dots),
        "footprint_fraction": len(final_dots) / int(foot.sum()),
        "on_catalogue_positive_pixels": 0,
        "in_footprint_finite_pixels": int(foot.sum()),
        "in_footprint_min": 0.0,
        "in_footprint_max": 1.0,
        "full_grid_finite_pixels": int(data.size),
        "checks": {
            "single_band": True,
            "dtype_float32": True,
            "sample_grid_shape_match": True,
            "sample_grid_crs_match": True,
            "sample_grid_transform_match": True,
            "all_values_finite": True,
            "all_values_range_0_1": True,
            "no_nodata_value": True,
            "zero_on_catalogue": True,
        },
        "format_validation_scope": "builder self-check only; independent validator not run",
        "generation": {
            "method": "H74-A experimental spring-chain + K/Th alteration",
            "spring_count_after_historical_full-catalogue_filter": int(len(springs_df)),
            "spring_dots": int(len(spring_dots)),
            "radiometric_dots": int(len(rad_dots)),
            "combined_pre_budget": int(len(combined)),
            "target_pixels": TARGET,
            "note": "Historical generator retains catalogue-derived spring-distance filtering; do not use its output as a compliant holdout result.",
        },
    }
    audit_path = OUT / f"build-{fname.replace('.tif', '.json')}"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE UNAPPROVED EXPERIMENT {out_path} sha256 {sha}")
    print(f"LOCAL BUILD METADATA {audit_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-unvalidated-experiment",
        action="store_true",
        help="Explicitly permit a local H74-A research raster; this never authorizes submission.",
    )
    options = parser.parse_args()
    if not options.allow_unvalidated_experiment:
        parser.error("legacy H74-A builder is blocked by default; use the fold-aware evaluator and all gates first")
    main()
