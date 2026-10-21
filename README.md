# GEMSDOE74

Workbench for DrivenData competition #306, **DOE GEMS Prize** (GeoDAWN study area). It contains the scoring metric, a strict submission validator and writer, a GitHub Pages site, and a run card.

Site: https://buffedlizard55-lab.github.io/GEMSDOE74/ (start at *How to submit*).

## Current status (2026-10-21)

**No submission file is ready. Do not submit anything from this repo yet.** The competition feature stack and labels are login-gated and are not in this environment. See the run card (`docs/data/run-card.json`) and `docs/irregularities.html` (IR-74-04).

## The task brief

> **Note on this record.** The original prompt is not stored verbatim in this workspace. The text below is a condensed record of it, kept so that the brief is re-read each session. If the full original text is available, replace this block with it.

**Goal.** Produce a unique GeoTIFF submission for DrivenData #306 that is easy to download from the site, carries a unique name and a note of at most 200 characters, and is not copied from any earlier GEMSDOE submission (learning from them is allowed). It must be obvious whether the file is OK to download and submit.

**Fix.** The portal error "Predicted values must be in range [0, 1]".

**Explain.** Why the GEMSDOE32 file `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (self-reported 0.2778) scored highest, and whether a higher score is reachable. The live top score on 2026-10-21 was 0.4413. Propose 3–5 ranked hypotheses and validate them on a spatially blocked holdout before any submission slot is spent.

**Site.** A GitHub Pages site with a clean UI. The top of the site has an executive summary on how to submit, plus a data and source table with official links.

**Protocol.** Stay in one method lane. Check rank correlation (> 0.90) and dot overlap (> 70 % within 3 px) against registry rasters. Label every number `HOLDOUT-DTI` or `ORGANIZER-CONFIRMED`. Run a leakage canary: a single feature with AUC > 0.90 means leakage. End with a JSON run card. Budget: 3 experiments or 2 hours.

**Process.** Three passes: implement, review, re-check. Flag irregularities. No hallucinations; verify against official sources. Give links for manual review. Open a PR and merge to `main`. List the remaining work and limitations.

**Constraints.**
- Work autonomously, with no manual input.
- Predictions: float32, one band, values in [0, 1], EPSG:32611, 100 m, the same bounds as the training data, NaN or null outside the bounds.
- Negative results are deliverables.
- Do not pick submission slots. Promotion is a separate selector step, within the weekly cap of 3.
- DrivenData data requires login and cannot be downloaded automatically.
- Core values: **Maximize P(Win)** and **Own the Outcome**.

## Ground rules for every session

1. Re-read the brief above at the start of each session.
2. Label every number as `HOLDOUT-DTI`, `ORGANIZER-CONFIRMED`, `PUBLIC-LEADERBOARD`, `PROJECTION`, or `CLAIM`. A projection is never written as a score.
3. Do not spend a submission slot without a holdout result that beats the incumbent.
4. Do not use third-party copies of login-gated competition data unless their rights are confirmed (see IR-74-04).
5. Keep notes under 140 characters (the 200-character limit used elsewhere is not confirmed on the form).

## Repository layout

| Path | What it is |
|---|---|
| `src/gems74/metric.py` | Distance-weighted Tversky (α = 0.2, β = 0.8, 300 m triangular kernel, 100 m grid). Returns TP, FP, FN and DTI. |
| `src/gems74/submission.py` | `validate_submission()` checks format and `write_submission()` writes a file with a `.receipt.json`. |
| `scripts/validate_submission.py` | CLI. Prints JSON. Exits 0 only if every check passes. |
| `scripts/build_site.py` | Builds the leaderboard and run-card pages, and injects the submission-status panel into `docs/index.html` and `docs/executive-summary.html`. |
| `tests/` | Unit tests: metric, marginal-dot rule, submission format. |
| `docs/` | The GitHub Pages site. |
| `docs/data/` | Leaderboard snapshot and run card (JSON). |
| `docs/downloads/` | Submission files that are OK to download (only when `release_status` is `READY`). |
| `data/` | Competition data goes here. Git-ignored. See `data/README.md`. |

## Quick start

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest -q tests
python scripts/build_site.py
python scripts/validate_submission.py path/to/file.tif --footprint path/to/footprint.npy
```

## Submission format

Single-band float32 GeoTIFF. CRS EPSG:32611. 100 m. Same bounds as training data. Values in [0, 1]. Null or NaN outside bounds. The validator checks the grid, the sentinel, and the value range.

## Limitations

- No competition data is in this repo. No holdout has been run. No candidate has been scored.
- The shape and origin of the grid come from a sibling repo and are not yet confirmed against the official header.
- Eligibility must be confirmed by a human (rules §1.3).

## Sources

See `docs/sources.html` for the official links and access log. Primary references: the DrivenData problem page and leaderboard, and the official NLR rules (https://docs.nlr.gov/docs/fy26osti/96647.pdf).
