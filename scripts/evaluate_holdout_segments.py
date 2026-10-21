#!/usr/bin/env python3
"""Buffered whole-segment spatial holdout for GEMSDOE74.

The evaluator divides the valid footprint into four spatial quadrants. In each
replicate it withholds whole 8-connected catalogue components assigned to each
quadrant, removes a 1.5 km spatial collar from the catalogue supplied to any
feature/prediction builder, and scores only the quadrant core. All non-hidden
catalogue pixels are passed to the metric as an exact known-fault mask (there
is no dilated scoring mask). The primary result is pooled DTI (alpha=0.2,
beta=0.8, 300 m triangular kernel) across the four disjoint quadrants.

A fixed candidate surface is accepted only when the caller explicitly declares
that it is catalogue-independent. Catalogue-dependent methods must provide a
fold/draw builder that receives only the visible-catalogue mask. This prevents
an already-built surface that used the full catalogue from being presented as
a hide-and-recover result. The CLI handles fixed, catalogue-independent
surfaces; catalogue-dependent experiments should call ``evaluate_holdout``
with a fold-aware builder from the shared method implementation.

The 95% interval is the empirical 2.5th–97.5th percentile across repeated
segment-holdout draws. It is a HOLDOUT-DTI uncertainty interval, not an
organizer score or a population-level guarantee. It must be reported with the
evaluator version and the exact primary-draw withheld-positive count.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, label
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.gems74.metric import ALPHA, BETA, RADIUS_PX, dti_binary, dti_exact  # noqa: E402

EVALUATOR_VERSION = "segments-buffered-repeated-v1.0.0"
LABEL = "HOLDOUT-DTI"
DEFAULT_BUFFER_METERS = 1500.0
DEFAULT_PIXEL_SIZE_METERS = 100.0
DEFAULT_DRAWS = 100
DEFAULT_HIDE_FRACTION = 0.20
DEFAULT_SEED = 74
KERNEL_METERS = 300.0

PredictionBuilder = Callable[[np.ndarray, int, int], np.ndarray]
FeatureBuilder = Callable[[np.ndarray, int, int], np.ndarray]


def quadrant_ids(footprint: np.ndarray) -> np.ndarray:
    """Assign valid pixels to NW, NE, SW, SE using median valid row/column."""
    footprint = np.asarray(footprint, dtype=bool)
    if footprint.ndim != 2 or not footprint.any():
        raise ValueError("footprint must be a nonempty 2-D mask")
    rows, cols = np.nonzero(footprint)
    row_mid, col_mid = int(np.median(rows)), int(np.median(cols))
    gy, gx = np.ogrid[: footprint.shape[0], : footprint.shape[1]]
    q = np.full(footprint.shape, -1, dtype=np.int8)
    q[(gy < row_mid) & (gx < col_mid) & footprint] = 0
    q[(gy < row_mid) & (gx >= col_mid) & footprint] = 1
    q[(gy >= row_mid) & (gx < col_mid) & footprint] = 2
    q[(gy >= row_mid) & (gx >= col_mid) & footprint] = 3
    return q


def _component_folds(components: np.ndarray, n_components: int, q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Assign each complete component to the quadrant containing most of its pixels."""
    if n_components <= 0:
        raise ValueError("catalogue contains no fault segments inside the footprint")
    flat_components = components.ravel()
    component_sizes = np.bincount(flat_components, minlength=n_components + 1)[1:]
    pixels_by_quadrant = []
    for fold in range(4):
        in_fold = (q == fold).ravel() & (flat_components > 0)
        pixels_by_quadrant.append(
            np.bincount(flat_components[in_fold], minlength=n_components + 1)[1:]
        )
    folds = np.argmax(np.stack(pixels_by_quadrant, axis=0), axis=0).astype(np.int8)
    return folds, component_sizes.astype(np.int64)


def _bbox(mask: np.ndarray) -> tuple[slice, slice]:
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    if rows.size == 0 or cols.size == 0:
        raise ValueError("each spatial quadrant must contain valid footprint pixels")
    return slice(int(rows[0]), int(rows[-1]) + 1), slice(int(cols[0]), int(cols[-1]) + 1)


def _checked_prediction(prediction: np.ndarray, footprint: np.ndarray, *, name: str) -> np.ndarray:
    pred = np.asarray(prediction)
    if pred.ndim != 2 or pred.shape != footprint.shape:
        raise ValueError(f"{name} prediction shape must match the footprint")
    inside = pred[footprint]
    if not np.isfinite(inside).all() or (inside < 0).any() or (inside > 1).any():
        raise ValueError(f"{name} predictions inside the footprint must be finite and in [0, 1]")
    return pred.astype(np.float64, copy=False)


def _score(prediction: np.ndarray, truth: np.ndarray, valid: np.ndarray, known: np.ndarray) -> dict:
    """Use the exact shared metric; take its faster binary path for 0/1 rasters."""
    active = np.asarray(valid, bool) & ~np.asarray(known, bool)
    vals = np.asarray(prediction)[active]
    is_binary = np.isin(vals, (0, 1)).all()
    if is_binary:
        return dti_binary(prediction, truth, valid=valid, known=known, alpha=ALPHA, beta=BETA)
    return dti_exact(prediction, truth, valid=valid, known=known, alpha=ALPHA, beta=BETA)


def feature_auc_canary(
    feature: np.ndarray,
    truth: np.ndarray,
    valid: np.ndarray,
    known: np.ndarray,
    *,
    seed: int = DEFAULT_SEED,
    max_per_class: int = 20_000,
) -> dict:
    """Estimate single-feature ROC AUC on the exact scored pixels.

    Positives and negatives are sampled separately for bounded memory. An AUC
    strictly above 0.90 is flagged as a leakage canary, not silently accepted.
    The feature must already be built from the fold's visible faults when it is
    catalogue-dependent.
    """
    feature = np.asarray(feature, dtype=np.float64)
    truth = np.asarray(truth, dtype=bool)
    valid = np.asarray(valid, dtype=bool)
    known = np.asarray(known, dtype=bool)
    if feature.ndim != 2 or feature.shape != truth.shape or feature.shape != valid.shape or feature.shape != known.shape:
        raise ValueError("feature, truth, valid, and known masks must share a 2-D grid")
    active = valid & ~known & np.isfinite(feature)
    positive = np.flatnonzero(active & truth)
    negative = np.flatnonzero(active & ~truth)
    if not positive.size or not negative.size:
        raise ValueError("feature AUC needs at least one held-out positive and one negative")
    n_each = min(int(max_per_class), positive.size, negative.size)
    rng = np.random.default_rng(seed)
    if positive.size > n_each:
        positive = rng.choice(positive, size=n_each, replace=False)
    if negative.size > n_each:
        negative = rng.choice(negative, size=n_each, replace=False)
    flat = feature.ravel()
    scores = np.concatenate((flat[positive], flat[negative]))
    y = np.concatenate((np.ones(positive.size, dtype=np.uint8), np.zeros(negative.size, dtype=np.uint8)))
    ranks = rankdata(scores, method="average")
    n_pos = int(positive.size)
    n_neg = int(negative.size)
    auc = (float(ranks[:n_pos].sum()) - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return {
        "auc": float(auc),
        "leakage_flag": bool(auc > 0.90),
        "positive_samples": n_pos,
        "negative_samples": n_neg,
        "threshold": 0.90,
        "threshold_rule": "strictly greater than 0.90 is flagged",
    }


def _draw_segment_ids(
    component_folds: np.ndarray,
    *,
    fold: int,
    hide_fraction: float,
    seed: int,
    draw: int,
) -> np.ndarray:
    ids = np.flatnonzero(component_folds == fold) + 1
    if ids.size == 0:
        return ids
    n_hide = max(1, int(round(hide_fraction * ids.size)))
    n_hide = min(n_hide, ids.size)
    rng = np.random.default_rng(np.random.SeedSequence([seed, draw, fold]))
    return np.sort(rng.choice(ids, size=n_hide, replace=False))


def evaluate_holdout(
    footprint: np.ndarray,
    catalogue: np.ndarray,
    *,
    prediction: np.ndarray | None = None,
    prediction_builder: PredictionBuilder | None = None,
    catalogue_dependent: bool = False,
    canary_builders: dict[str, FeatureBuilder] | None = None,
    buffer_pixels: int | None = None,
    buffer_meters: float = DEFAULT_BUFFER_METERS,
    hide_fraction: float = DEFAULT_HIDE_FRACTION,
    draws: int = DEFAULT_DRAWS,
    seed: int = DEFAULT_SEED,
    candidate_id: str = "candidate",
) -> dict:
    """Evaluate one candidate with repeated, buffered, whole-segment spatial holdouts.

    ``prediction_builder`` and each ``canary_builder`` receive only
    ``(visible_fault_mask, fold_index, draw_index)``. Set ``catalogue_dependent``
    when any predictive feature depends on catalogue locations; that mode
    requires a builder and fails closed without one. For a catalogue-independent
    surface, pass its fixed 2-D ``prediction`` and leave the flag false.
    """
    footprint = np.asarray(footprint, dtype=bool)
    catalogue = np.asarray(catalogue, dtype=bool)
    if footprint.ndim != 2 or catalogue.shape != footprint.shape or not footprint.any():
        raise ValueError("footprint and catalogue must be equal-shaped, nonempty 2-D grids")
    if not math.isfinite(buffer_meters) or buffer_meters < 0:
        raise ValueError("buffer size must be finite and nonnegative")
    if buffer_pixels is None:
        buffer_pixels = int(math.ceil(buffer_meters / DEFAULT_PIXEL_SIZE_METERS))
    if type(buffer_pixels) is not int or buffer_pixels < 0:
        raise ValueError("buffer_pixels must be a nonnegative integer")
    if not (0.0 < hide_fraction <= 1.0):
        raise ValueError("hide_fraction must be in (0, 1]")
    if draws < 2:
        raise ValueError("at least two repeated holdout draws are required for a 95% interval")
    if catalogue_dependent and prediction_builder is None:
        raise ValueError("catalogue-dependent features require a fold-aware prediction_builder")
    if not catalogue_dependent and prediction is None and prediction_builder is None:
        raise ValueError("provide a fixed prediction or a prediction_builder")
    if prediction is not None and prediction_builder is not None:
        raise ValueError("provide either a fixed prediction or prediction_builder, not both")

    catalogue = catalogue & footprint
    component_mask, n_components = label(catalogue, structure=np.ones((3, 3), dtype=np.uint8))
    if n_components == 0:
        raise ValueError("catalogue contains no connected fault segments inside the footprint")
    quadrants = quadrant_ids(footprint)
    component_folds, component_sizes = _component_folds(component_mask, n_components, quadrants)
    blocks = {fold: (quadrants == fold) & footprint for fold in range(4)}
    bboxes = {fold: _bbox(blocks[fold]) for fold in range(4)}
    buffered_blocks: dict[int, np.ndarray] = {}
    for fold in range(4):
        # Euclidean buffer around the spatial test block; its pixels are not
        # available to catalogue-derived feature builders.
        distance_to_block = distance_transform_edt(~blocks[fold])
        buffered_blocks[fold] = (distance_to_block <= buffer_pixels) & footprint
        del distance_to_block

    fixed_prediction = None
    if prediction is not None:
        fixed_prediction = _checked_prediction(prediction, footprint, name=candidate_id)

    canary_builders = canary_builders or {}
    if any(not isinstance(name, str) or not name.strip() for name in canary_builders):
        raise ValueError("canary feature names must be nonempty strings")
    canary_observations: dict[str, list[dict]] = {name: [] for name in canary_builders}
    draw_results: list[dict] = []

    for draw in range(draws):
        fold_results: dict[str, dict] = {}
        pooled_tp = pooled_fp = pooled_fn = 0.0
        withheld_positive_count = withheld_segment_count = 0
        for fold in range(4):
            selected_ids = _draw_segment_ids(
                component_folds,
                fold=fold,
                hide_fraction=hide_fraction,
                seed=seed,
                draw=draw,
            )
            if selected_ids.size == 0:
                fold_results[f"fold_{fold}"] = {"status": "no_segments_assigned"}
                continue
            hidden = np.isin(component_mask, selected_ids)
            # The full selected segments are withheld, even if they cross a
            # quadrant boundary. The collar additionally removes all catalogue
            # pixels near the test block from feature construction.
            visible_features = catalogue & ~hidden & ~buffered_blocks[fold]
            known_exact = catalogue & ~hidden
            valid = blocks[fold]

            if prediction_builder is not None:
                pred = _checked_prediction(
                    prediction_builder(visible_features.copy(), fold, draw), footprint, name=candidate_id
                )
            else:
                pred = fixed_prediction
            assert pred is not None

            sl = bboxes[fold]
            valid_sub = valid[sl]
            hidden_sub = hidden[sl]
            known_sub = known_exact[sl]
            pred_sub = pred[sl]
            result = _score(pred_sub, hidden_sub, valid_sub, known_sub)
            fold_results[f"fold_{fold}"] = {
                "status": "scored" if result["n_truth"] else "no_withheld_positive_in_test_block",
                "withheld_segment_count": int(selected_ids.size),
                "withheld_positive_count": int(result["n_truth"]),
                "tp": float(result["tp"]),
                "fp": float(result["fp"]),
                "fn": float(result["fn"]),
                "dti": float(result["dti"]),
                "coverage": float(result["coverage"]),
            }
            pooled_tp += float(result["tp"])
            pooled_fp += float(result["fp"])
            pooled_fn += float(result["fn"])
            withheld_positive_count += int(result["n_truth"])
            withheld_segment_count += int(selected_ids.size)

            for name, builder in canary_builders.items():
                feature = np.asarray(builder(visible_features.copy(), fold, draw), dtype=np.float64)
                if feature.shape != footprint.shape:
                    raise ValueError(f"canary feature {name!r} does not match the footprint shape")
                canary_observations[name].append(
                    feature_auc_canary(
                        feature[sl], hidden_sub, valid_sub, known_sub,
                        seed=seed + 1_000_003 * draw + 101 * fold,
                    )
                )

        denom = pooled_tp + ALPHA * pooled_fp + BETA * pooled_fn + 1e-12
        pooled_dti = float(pooled_tp / denom) if withheld_positive_count else 0.0
        draw_results.append(
            {
                "draw": draw,
                "pooled_dti": pooled_dti,
                "tp": pooled_tp,
                "fp": pooled_fp,
                "fn": pooled_fn,
                "withheld_positive_count": withheld_positive_count,
                "withheld_segment_count": withheld_segment_count,
                "folds": fold_results,
            }
        )

    scores = np.asarray([row["pooled_dti"] for row in draw_results], dtype=np.float64)
    if not np.isfinite(scores).all() or draw_results[0]["withheld_positive_count"] <= 0:
        raise ValueError("holdout generated no withheld positive pixels or non-finite DTI values")
    ci = np.percentile(scores, [2.5, 97.5])
    canary_rows = []
    for name, observations in canary_observations.items():
        aucs = [float(row["auc"]) for row in observations]
        max_auc = max(aucs) if aucs else None
        canary_rows.append(
            {
                "feature": name,
                "auc": max_auc,
                "mean_auc": float(np.mean(aucs)) if aucs else None,
                "max_auc": max_auc,
                "leakage_flag": bool(max_auc is not None and max_auc > 0.90),
                "fold_draw_count": len(aucs),
            }
        )
    leakage_passed = bool(canary_rows) and all(not row["leakage_flag"] for row in canary_rows)

    return {
        "schema_version": "gemsdoe74-holdout-v1",
        "label": LABEL,
        "evaluator_version": EVALUATOR_VERSION,
        "candidate_id": candidate_id,
        "status": "COMPUTED",
        "point_estimate": float(scores.mean()),
        "point_estimate_method": "mean pooled DTI over repeated segment-holdout draws",
        "confidence_interval_95_percent": [float(ci[0]), float(ci[1])],
        "confidence_interval_method": "empirical 2.5th–97.5th percentiles across repeated draws",
        "withheld_positive_count": int(draw_results[0]["withheld_positive_count"]),
        "primary_draw": 0,
        "withheld_positive_count_per_draw": [int(row["withheld_positive_count"]) for row in draw_results],
        "withheld_segment_count_per_draw": [int(row["withheld_segment_count"]) for row in draw_results],
        "draws": draws,
        "seed": seed,
        "protocol": {
            "folds": 4,
            "fold_definition": "NW, NE, SW, SE using median valid row and column",
            "withheld_unit": "whole_fault_segments",
            "component_connectivity": "8-connected",
            "hide_fraction_of_segments_per_fold": hide_fraction,
            "buffer_meters": float(buffer_meters),
            "buffer_pixels": int(buffer_pixels),
            "buffer_applies_to": "catalogue supplied to fold-specific feature and prediction builders",
            "scoring_domain": "disjoint quadrant cores",
            "visible_faults_pixel_mask_exact": True,
            "catalogue_features_visible_only": bool(not catalogue_dependent or prediction_builder is not None),
            "pooling": "pooled",
            "alpha": ALPHA,
            "beta": BETA,
            "kernel_meters": KERNEL_METERS,
            "kernel_radius_pixels": RADIUS_PX,
        },
        "leakage_canary": {
            "passed": leakage_passed,
            "features": canary_rows,
            "threshold": 0.90,
            "rule": "AUC > 0.90 is flagged as leakage until explained",
            "note": "No features supplied" if not canary_rows else None,
        },
        "draw_results": draw_results,
        "beats_current_holdout_best": None,
        "comparison": None,
    }


def compare_candidate_to_baseline(candidate_result: dict, baseline_result: dict) -> dict:
    """Paired comparison on identical deterministic segment draws."""
    candidate_draws = candidate_result.get("draw_results", [])
    baseline_draws = baseline_result.get("draw_results", [])
    if len(candidate_draws) != len(baseline_draws) or not candidate_draws:
        raise ValueError("candidate and baseline must use the same nonempty number of draws")
    if [x["draw"] for x in candidate_draws] != [x["draw"] for x in baseline_draws]:
        raise ValueError("candidate and baseline holdout draws are not aligned")
    if [x["withheld_positive_count"] for x in candidate_draws] != [x["withheld_positive_count"] for x in baseline_draws]:
        raise ValueError("candidate and baseline holdout truth counts differ")
    deltas = np.asarray(
        [c["pooled_dti"] - b["pooled_dti"] for c, b in zip(candidate_draws, baseline_draws)],
        dtype=np.float64,
    )
    ci = np.percentile(deltas, [2.5, 97.5])
    beats = bool(float(deltas.mean()) > 0.0 and float(ci[0]) > 0.0)
    return {
        "baseline_candidate_id": baseline_result.get("candidate_id"),
        "baseline_point_estimate": float(baseline_result["point_estimate"]),
        "paired_delta_mean": float(deltas.mean()),
        "paired_delta_confidence_interval_95_percent": [float(ci[0]), float(ci[1])],
        "method": "paired repeated-draw difference; empirical percentile interval",
        "beats_current_holdout_best": beats,
    }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _grid_signature(path: Path) -> dict:
    with rasterio.open(path) as src:
        if src.count < 1:
            raise ValueError(f"raster has no bands: {path}")
        return {
            "shape": (src.height, src.width),
            "crs": src.crs,
            "transform": src.transform,
            "resolution_x_m": math.hypot(src.transform.a, src.transform.d),
            "resolution_y_m": math.hypot(src.transform.b, src.transform.e),
        }


def _read_aligned(path: Path, reference: dict, *, band: int = 1) -> np.ndarray:
    with rasterio.open(path) as src:
        if src.count < band:
            raise ValueError(f"{path} has no band {band}")
        if (src.height, src.width) != reference["shape"]:
            raise ValueError(f"raster shape mismatch for {path}")
        if src.crs != reference["crs"] or src.transform != reference["transform"]:
            raise ValueError(f"raster CRS/transform mismatch for {path}")
        return src.read(band)


def _load_grid(data_dir: Path) -> tuple[np.ndarray, np.ndarray, dict]:
    sample_path = data_dir / "sample_submission.tif"
    labels_path = data_dir / "labels.tif"
    if not sample_path.is_file() or not labels_path.is_file():
        missing = [str(p) for p in (sample_path, labels_path) if not p.is_file()]
        raise FileNotFoundError("missing required input(s): " + ", ".join(missing))
    signature = _grid_signature(sample_path)
    if not math.isclose(signature["resolution_x_m"], DEFAULT_PIXEL_SIZE_METERS, abs_tol=1e-6) or not math.isclose(
        signature["resolution_y_m"], DEFAULT_PIXEL_SIZE_METERS, abs_tol=1e-6
    ):
        raise ValueError("shared DTI implementation requires a 100 m sample grid for the 300 m (3 px) kernel")
    sample = _read_aligned(sample_path, signature)
    labels = _read_aligned(labels_path, signature)
    footprint = np.isfinite(sample)
    catalogue = np.isfinite(labels) & (labels > 0) & footprint
    if not footprint.any() or not catalogue.any():
        raise ValueError("sample grid footprint or catalogue labels are empty")
    return footprint, catalogue, signature


def _read_candidate(path: Path, reference: dict) -> np.ndarray:
    return _read_aligned(path, reference).astype(np.float64, copy=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True, help="Candidate GeoTIFF; no default artifact is used.")
    parser.add_argument("--baseline", type=Path, help="Current valid holdout-best GeoTIFF for a paired comparison.")
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("GEMS74_DATA_DIR", ROOT / "data")))
    parser.add_argument("--evidence", type=Path, help="Evidence JSON path (default: evidence/holdout_<candidate>.json).")
    parser.add_argument("--candidate-independent", action="store_true", help="Assert the fixed candidate uses no catalogue-derived predictive feature.")
    parser.add_argument("--baseline-independent", action="store_true", help="Assert the fixed baseline uses no catalogue-derived predictive feature.")
    parser.add_argument("--buffer-m", type=float, default=DEFAULT_BUFFER_METERS)
    parser.add_argument("--hide-fraction", type=float, default=DEFAULT_HIDE_FRACTION)
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--canary-independent", action="append", default=[], metavar="NAME=PATH", help="Aligned catalogue-independent feature raster; repeat once per feature. Catalogue-derived features require a fold-aware API builder.")
    args = parser.parse_args()

    if not args.candidate_independent:
        parser.error("a prebuilt raster is accepted only with --candidate-independent; catalogue-dependent methods must use a fold-aware builder")
    if args.baseline and not args.baseline_independent:
        parser.error("a prebuilt baseline is accepted only with --baseline-independent")
    if args.buffer_m < 0 or not math.isfinite(args.buffer_m):
        parser.error("--buffer-m must be finite and nonnegative")
    if args.hide_fraction <= 0 or args.hide_fraction > 1:
        parser.error("--hide-fraction must be in (0, 1]")
    if args.draws < 2:
        parser.error("--draws must be at least 2")

    candidate_path = args.candidate.resolve()
    public_downloads = (ROOT / "docs" / "downloads").resolve()
    if candidate_path == public_downloads or public_downloads in candidate_path.parents:
        parser.error("evaluate an unapproved candidate outside docs/downloads; publish only after every gate passes")
    try:
        footprint, catalogue, grid = _load_grid(args.data_dir.resolve())
        candidate_surface = _read_candidate(candidate_path, grid)
        canary_builders: dict[str, FeatureBuilder] = {}
        for item in args.canary_independent:
            if "=" not in item:
                parser.error("--canary-independent must use NAME=PATH")
            name, filename = item.split("=", 1)
            if not name.strip() or not filename.strip() or name in canary_builders:
                parser.error("canary names and paths must be nonempty and names unique")
            layer = _read_candidate(Path(filename).resolve(), grid)
            canary_builders[name] = lambda _visible, _fold, _draw, arr=layer: arr

        candidate_result = evaluate_holdout(
            footprint,
            catalogue,
            prediction=candidate_surface,
            catalogue_dependent=False,
            canary_builders=canary_builders,
            buffer_pixels=int(math.ceil(args.buffer_m / DEFAULT_PIXEL_SIZE_METERS)),
            buffer_meters=args.buffer_m,
            hide_fraction=args.hide_fraction,
            draws=args.draws,
            seed=args.seed,
            candidate_id=candidate_path.name,
        )
        candidate_result["candidate"] = {
            "path": candidate_path.relative_to(ROOT).as_posix() if candidate_path.is_relative_to(ROOT) else str(candidate_path),
            "sha256": _sha256(candidate_path),
        }
        candidate_result["protocol"]["candidate_catalogue_independent_assertion"] = True

        if args.baseline:
            baseline_path = args.baseline.resolve()
            if baseline_path == public_downloads or public_downloads in baseline_path.parents:
                parser.error("the current baseline must be evaluated from a private/local path, not docs/downloads")
            baseline_surface = _read_candidate(baseline_path, grid)
            baseline_result = evaluate_holdout(
                footprint,
                catalogue,
                prediction=baseline_surface,
                catalogue_dependent=False,
                buffer_pixels=int(math.ceil(args.buffer_m / DEFAULT_PIXEL_SIZE_METERS)),
                buffer_meters=args.buffer_m,
                hide_fraction=args.hide_fraction,
                draws=args.draws,
                seed=args.seed,
                candidate_id=baseline_path.name,
            )
            comparison = compare_candidate_to_baseline(candidate_result, baseline_result)
            candidate_result["comparison"] = comparison
            candidate_result["beats_current_holdout_best"] = comparison["beats_current_holdout_best"]
            candidate_result["baseline"] = {
                "path": baseline_path.relative_to(ROOT).as_posix() if baseline_path.is_relative_to(ROOT) else str(baseline_path),
                "sha256": _sha256(baseline_path),
                "evaluator_version": baseline_result["evaluator_version"],
            }
        else:
            candidate_result["comparison"] = {"status": "NOT_RUN", "reason": "no current valid holdout-best baseline supplied"}

        candidate_result["generated_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        evidence_path = args.evidence or (ROOT / "evidence" / f"holdout_{candidate_path.stem}.json")
        if not evidence_path.is_absolute():
            evidence_path = ROOT / evidence_path
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(candidate_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({k: candidate_result[k] for k in (
            "label", "evaluator_version", "point_estimate", "confidence_interval_95_percent",
            "withheld_positive_count", "withheld_positive_count_per_draw", "beats_current_holdout_best",
            "leakage_canary", "candidate",
        )}, indent=2))
        print(f"Evidence: {evidence_path.relative_to(ROOT) if evidence_path.is_relative_to(ROOT) else evidence_path}")
        return 0
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
