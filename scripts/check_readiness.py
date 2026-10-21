#!/usr/bin/env python3
"""Fail-closed preflight for the GEMSDOE74 download gate.

This script does not train, evaluate DTI, write a GeoTIFF, or validate raster
pixels. It only allows a static-site download link when the shared pipeline's
receipt manifest, required files, independent holdout/uniqueness/validator
receipts, and the artifact hash are all present and mutually consistent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_REL = Path("docs/data/submission-manifest.json")

REQUIRED_INPUTS = {
    "training_features": Path("data/training_features.tif"),
    "labels": Path("data/labels.tif"),
    "sample_submission": Path("data/sample_submission.tif"),
    "one_meter_dem_links": Path("data/1m_DEM_links.csv"),
}
REQUIRED_SHARED_TOOLS = {
    "holdout_evaluator": Path("scripts/evaluate_holdout.py"),
    "buffered_segment_engine": Path("scripts/evaluate_holdout_segments.py"),
    "submission_writer": Path("scripts/generate_submission.py"),
    "independent_validator": Path("scripts/validate_submission.py"),
    "metric_implementation": Path("src/gems74/metric.py"),
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _hash_matches(path: Path, expected: str) -> bool:
    try:
        return _sha256(path) == expected
    except OSError:
        return False


def _load_manifest(root: Path) -> tuple[dict[str, Any] | None, str | None]:
    path = root / MANIFEST_REL
    if not path.is_file():
        return None, f"Submission manifest is missing: {MANIFEST_REL.as_posix()}."
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"Submission manifest cannot be read as JSON: {exc}."
    if not isinstance(data, dict):
        return None, "Submission manifest must contain a JSON object."
    return data, None


def _artifact_file(root: Path, manifest: dict[str, Any]) -> tuple[Path | None, list[str]]:
    problems: list[str] = []
    artifact = manifest.get("artifact")
    if not isinstance(artifact, dict):
        return None, ["Manifest has no artifact receipt."]

    relative = artifact.get("path")
    expected_hash = artifact.get("sha256")
    if not _nonempty_string(relative):
        problems.append("Artifact path is missing.")
        return None, problems
    if not _nonempty_string(expected_hash) or not SHA256_RE.fullmatch(expected_hash):
        problems.append("Artifact SHA-256 must be a lowercase 64-character digest.")

    candidate = (root / relative).resolve()
    if not _within_root(candidate, root):
        problems.append("Artifact path must stay inside the repository.")
        return None, problems
    if candidate.suffix.lower() != ".tif":
        problems.append("Download artifact must be a GeoTIFF with a .tif extension.")
    if not candidate.is_file():
        problems.append("Artifact file does not exist on disk.")
        return None, problems
    if _nonempty_string(expected_hash) and SHA256_RE.fullmatch(expected_hash):
        if not _hash_matches(candidate, expected_hash):
            problems.append("Artifact bytes cannot be read or do not match the manifest SHA-256.")
    return candidate, problems


def _leakage_canary_ok(leakage: Any) -> bool:
    feature_rows = leakage.get("features") if isinstance(leakage, dict) else None
    return (
        isinstance(leakage, dict)
        and leakage.get("passed") is True
        and isinstance(feature_rows, list)
        and bool(feature_rows)
        and all(
            isinstance(row, dict)
            and _nonempty_string(row.get("feature"))
            and _is_number(row.get("auc"))
            and 0.0 <= row.get("auc") <= 0.90
            for row in feature_rows
        )
    )


def _evidence_receipt_ok(root: Path, receipt: Any, *, path_key: str = "evidence_path", hash_key: str = "evidence_sha256") -> bool:
    if not isinstance(receipt, dict):
        return False
    relative = receipt.get(path_key)
    expected_hash = receipt.get(hash_key)
    if not _nonempty_string(relative) or not _nonempty_string(expected_hash):
        return False
    if not SHA256_RE.fullmatch(expected_hash):
        return False
    path = (root / relative).resolve()
    if not _within_root(path, root) or not path.is_file():
        return False
    return _hash_matches(path, expected_hash)


def _receipt_checks(manifest: dict[str, Any], root: Path) -> tuple[dict[str, bool], list[str]]:
    checks: dict[str, bool] = {}
    problems: list[str] = []

    input_hashes = manifest.get("input_hashes")
    inputs_hashed = isinstance(input_hashes, dict)
    if inputs_hashed:
        for name, relative in REQUIRED_INPUTS.items():
            expected = input_hashes.get(name)
            path = root / relative
            if (
                not path.is_file()
                or not _nonempty_string(expected)
                or not SHA256_RE.fullmatch(expected)
                or not _hash_matches(path, expected)
            ):
                inputs_hashed = False
                break
    checks["competition_input_hashes"] = bool(inputs_hashed)
    if not checks["competition_input_hashes"]:
        problems.append("One or more official competition inputs are missing, unhashed, or differ from the manifest.")

    feature_stack = manifest.get("feature_stack")
    checks["shared_feature_stack_receipt"] = (
        isinstance(feature_stack, dict)
        and feature_stack.get("status") == "verified"
        and _nonempty_string(feature_stack.get("stack_sha256"))
        and bool(SHA256_RE.fullmatch(feature_stack.get("stack_sha256", "")))
        and _evidence_receipt_ok(root, feature_stack, path_key="manifest_path", hash_key="manifest_sha256")
    )
    if not checks["shared_feature_stack_receipt"]:
        problems.append("The shared cached feature stack has no verified hash receipt.")

    holdout = manifest.get("holdout")
    valid_holdout = (
        isinstance(holdout, dict)
        and holdout.get("passed") is True
        and holdout.get("label") == "HOLDOUT-DTI"
        and _nonempty_string(holdout.get("evaluator_version"))
        and type(holdout.get("withheld_positive_count")) is int
        and holdout.get("withheld_positive_count", 0) > 0
        and holdout.get("spatially_blocked") is True
        and holdout.get("withheld_unit") == "whole_fault_segments"
        and _is_number(holdout.get("buffer_meters"))
        and holdout.get("buffer_meters", 0) > 0
        and holdout.get("catalogue_features_visible_only") is True
        and holdout.get("visible_faults_pixel_mask_exact") is True
        and holdout.get("pooling") == "pooled"
        and holdout.get("alpha") == 0.2
        and holdout.get("beta") == 0.8
        and holdout.get("kernel_meters") == 300
        and _is_number(holdout.get("point_estimate"))
        and isinstance(holdout.get("confidence_interval_95_percent"), list)
        and len(holdout.get("confidence_interval_95_percent", [])) == 2
        and all(_is_number(x) for x in holdout.get("confidence_interval_95_percent", []))
        and holdout.get("beats_current_holdout_best") is True
        and _evidence_receipt_ok(root, holdout)
    )
    if valid_holdout:
        lo, hi = holdout["confidence_interval_95_percent"]
        valid_holdout = (
            0.0 <= lo <= holdout["point_estimate"] <= hi <= 1.0
            and 0.0 <= holdout["point_estimate"] <= 1.0
        )
    checks["spatial_holdout"] = bool(valid_holdout)
    if not checks["spatial_holdout"]:
        problems.append("A valid HOLDOUT-DTI receipt is missing: it must document whole-segment spatial withholding with a buffer, visible-only catalogue features, exact visible-fault masking, pooled DTI parameters, evaluator version, withheld-positive count, 95% CI, and a beat-best decision.")

    leakage = manifest.get("leakage_canary")
    checks["feature_leakage_canary"] = _leakage_canary_ok(leakage) and _evidence_receipt_ok(root, leakage)
    if not checks["feature_leakage_canary"]:
        problems.append("The per-feature leakage canary is missing, incomplete, failed, or above the allowed AUC threshold.")

    registry = manifest.get("registry_check")
    valid_registry = (
        isinstance(registry, dict)
        and registry.get("passed") is True
        and registry.get("surface_checked") is True
        and registry.get("final_dots_checked") is True
        and type(registry.get("registry_raster_count")) is int
        and registry.get("registry_raster_count", 0) > 0
        and _is_number(registry.get("max_rank_correlation"))
        and -1.0 <= registry.get("max_rank_correlation") <= 0.90
        and _is_number(registry.get("max_dot_overlap_within_3px"))
        and 0.0 <= registry.get("max_dot_overlap_within_3px") <= 0.70
        and _evidence_receipt_ok(root, registry)
    )
    checks["registry_uniqueness"] = bool(valid_registry)
    if not checks["registry_uniqueness"]:
        problems.append("Surface and final-dot registry comparisons are missing, failed, or exceed the duplicate thresholds.")

    validator = manifest.get("validator")
    valid_validator = (
        isinstance(validator, dict)
        and validator.get("passed") is True
        and _nonempty_string(validator.get("submission_writer_version"))
        and validator.get("single_band") is True
        and validator.get("reread_from_disk") is True
        and validator.get("no_nan_inside_footprint") is True
        and validator.get("all_values_in_allowed_range") is True
        and validator.get("no_nodata_value") is True
        and validator.get("crs_match") is True
        and validator.get("shape_match") is True
        and validator.get("transform_match") is True
        and _evidence_receipt_ok(root, validator)
    )
    checks["geotiff_validation"] = bool(valid_validator)
    if not checks["geotiff_validation"]:
        problems.append("A passing independent GeoTIFF validation receipt is missing or invalid.")

    return checks, problems


def audit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    input_checks = {name: (root / rel).is_file() for name, rel in REQUIRED_INPUTS.items()}
    tool_checks = {name: (root / rel).is_file() for name, rel in REQUIRED_SHARED_TOOLS.items()}
    blockers: list[str] = []
    for name, present in input_checks.items():
        if not present:
            blockers.append(f"Required competition input is missing: {REQUIRED_INPUTS[name].as_posix()}.")
    for name, present in tool_checks.items():
        if not present:
            blockers.append(f"Required shared tool is missing: {REQUIRED_SHARED_TOOLS[name].as_posix()}.")

    manifest, manifest_problem = _load_manifest(root)
    checks: dict[str, bool] = {}
    artifact_path: Path | None = None
    if manifest_problem:
        blockers.append(manifest_problem)
    if manifest is not None:
        if manifest.get("schema_version") != "gemsdoe74-submission-manifest-v1":
            blockers.append("Submission manifest schema version is missing or unsupported.")
        if manifest.get("status") != "READY" or manifest.get("download_enabled") is not True:
            blockers.append("Manifest does not explicitly mark a fully gated artifact READY for download.")

        artifact_path, artifact_problems = _artifact_file(root, manifest)
        blockers.extend(artifact_problems)
        receipt_checks, receipt_problems = _receipt_checks(manifest, root)
        checks.update(receipt_checks)
        blockers.extend(receipt_problems)

        name = manifest.get("submission_name")
        artifact_receipt = manifest.get("artifact")
        artifact_hash = artifact_receipt.get("sha256") if isinstance(artifact_receipt, dict) else None
        name_format = re.fullmatch(r"GEMSDOE74-[A-Za-z0-9][A-Za-z0-9._-]*-[0-9a-f]{8}", name) if isinstance(name, str) else None
        name_ok = (
            bool(name_format)
            and _nonempty_string(artifact_hash)
            and SHA256_RE.fullmatch(artifact_hash) is not None
            and name.endswith("-" + artifact_hash[:8])
        )
        note = manifest.get("submission_note")
        note_ok = _nonempty_string(note) and len(note.strip()) <= 140
        checks["unique_name_and_short_note"] = name_ok and note_ok
        if not checks["unique_name_and_short_note"]:
            blockers.append("A unique submission name and a note of at most 140 characters are required.")

    files_ok = all(input_checks.values()) and all(tool_checks.values())
    receipts_ok = bool(checks) and all(checks.values())
    ready = (
        manifest is not None
        and manifest.get("schema_version") == "gemsdoe74-submission-manifest-v1"
        and manifest.get("status") == "READY"
        and manifest.get("download_enabled") is True
        and files_ok
        and receipts_ok
        and artifact_path is not None
        and not blockers
    )
    if not ready and not blockers:
        blockers.append("One or more submission gates did not pass.")

    download_url: str | None = None
    if ready and artifact_path is not None:
        try:
            relative_to_docs = artifact_path.relative_to(root / "docs/downloads")
        except ValueError:
            blockers.append("Download artifact must be stored beneath docs/downloads/ for the static site.")
            ready = False
        else:
            download_url = "./downloads/" + relative_to_docs.as_posix()

    return {
        "schema_version": "gemsdoe74-readiness-v1",
        "checked_on_utc": datetime.now(timezone.utc).date().isoformat(),
        "status": "READY" if ready else "BLOCKED",
        "download_enabled": bool(ready and download_url),
        "download_url": download_url if ready else None,
        "submission_name": manifest.get("submission_name") if ready and manifest else None,
        "submission_note": manifest.get("submission_note") if ready and manifest else None,
        "input_files_present": input_checks,
        "shared_tools_present": tool_checks,
        "evidence_gates": checks,
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root (defaults to this checkout).")
    parser.add_argument("--write", type=Path, help="Also write the JSON report to this path, relative to --root if not absolute.")
    parser.add_argument("--strict", action="store_true", help="Exit with status 2 when a submission is blocked.")
    args = parser.parse_args()

    root = args.root.resolve()
    report = audit(root)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.write:
        output = args.write if args.write.is_absolute() else root / args.write
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    sys.stdout.write(encoded)
    if args.strict and report["status"] != "READY":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
