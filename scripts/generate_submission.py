#!/usr/bin/env python3
"""Generate and validate the promoted real-data GEMSDOE74 H74-R1 submission GeoTIFFs.

Resolves IR-74-09..16 and IR-74-33 by replacing the prior-session synthetic generator
with the real-data 85-feature LOQO + 220m down-dip + 300m spaced submodular pipeline
(`scripts/run_gems74_experiments.py`).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_submission import validate_submission_file


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate or verify the promoted GEMSDOE74 H74-R1 submission.")
    ap.add_argument("--out", type=str, default="docs/downloads")
    ap.add_argument("--lane", type=str, default="h74-r1", help="Lane ID (default: h74-r1 real-data pipeline)")
    ap.add_argument("--recompute", action="store_true", help="Run full real-data experiment pipeline before validating")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out)
    stem = "gemsdoe74-h74-r1-transtensional-submod-37654-20261021T000000Z"
    zeros_p = out_dir / f"{stem}-zeros.tif"
    nan_p = out_dir / f"{stem}-nan.tif"

    if args.recompute or not (zeros_p.is_file() and nan_p.is_file()):
        from scripts.run_gems74_experiments import main as run_exp_main
        rc_code = run_exp_main()
        if rc_code != 0:
            return rc_code

    vz = validate_submission_file(zeros_p, require_all_finite=True)
    vn = validate_submission_file(nan_p, require_all_finite=False)
    assert vz["all_checks_passed"], f"Primary zeros GeoTIFF failed validation: {vz}"
    assert vn["all_checks_passed"], f"NaN twin GeoTIFF failed validation: {vn}"

    rc = json.loads((ROOT / "evidence" / "run_card.json").read_text())
    print(f"Verified promoted submission ({args.lane}):")
    print(f"  Primary (-zeros.tif): {zeros_p} ({vz['bytes']} B, sha256={vz['sha256']})")
    print(f"  NaN twin (-nan.tif):  {nan_p} ({vn['bytes']} B, sha256={vn['sha256']})")
    print(f"  Emitted dots:         {vz['emitted_positive_pixels']} in-footprint, {vz['outside_footprint_positive_pixels']} outside, {vz['on_catalogue_positive_pixels']} on-catalogue")
    print(f"  Submission Name:      {rc['submission']['name']}")
    print(f"  Short Note ({rc['submission']['short_note_length']}/140): {rc['submission']['short_note']}")
    print(f"  Verdict:              {rc['verdict']} (ok_to_submit={rc['ok_to_submit']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
