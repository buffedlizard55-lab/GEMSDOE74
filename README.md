# GEMSDOE74 — DOE GEMS Prize research and submission tooling

> **Core Values:** Maximize P(Win); Own the Outcome. Evidence and release readiness are separate: a technically well-formed GeoTIFF is not evidence of a good geological prediction.

## Current release decision: **HOLD — DO NOT SUBMIT**

This repository currently contains **no scientifically validated competition prediction**. The GeoTIFFs under `docs/downloads/` are historical **format/research fixtures only**. H74-1 was generated from synthetic surfaces/footprint/targets; H74-A's earlier build used sibling-mirror inputs whose provenance and rights are unverified, and it was assessed with an invalid proxy holdout. Neither is validated against an authorized official feature stack and labels. Format checks do **not** validate prediction quality, exact footprint agreement with DrivenData's template, catalogue exclusion, uniqueness against the full registry, or expected leaderboard score. There is no ORGANIZER-CONFIRMED receipt for either file.

- The landing page and [submission guide](docs/executive-summary.html) explicitly say **DO NOT SUBMIT**.
- Existing fixture: [H74-1 zeros TIFF](docs/downloads/gemsdoe74-h74-1-basement-step-35641-20261021T000000Z-100b4b19-zeros.tif) — format inspection only; not cleared.
- Alternate fixture: [H74-A zeros TIFF](docs/downloads/gems74-h74-alt-spring-39500-20261021T000000Z-52f76038-zeros.tif) — format inspection only; not cleared.
- Auditable findings: [repository review](docs/review/repo-audit-2026-10-21.html), [irregularities](docs/irregularities.html), [run card](docs/data/run-card.json).

The H74-1 run card's reported holdout score, confidence interval, AUC, uniqueness statistics, and `promote` verdict are **not valid evidence**: the generator constructs synthetic features and synthetic hidden positives, hard-codes an AUC, and inserts made-up registry similarity fields. Do not cite these as HOLDOUT-DTI results. Historical numbers in evidence files are retained for audit, but cannot be treated as validated competition results. The H74-A holdout files are also not a validated real-data holdout under the required protocol.

## The most important code-review finding

`scripts/generate_submission.py` is not a real-data model pipeline. It synthesizes the basement-depth/slope layers, synthetic catalogue and hidden labels, then uses a simple quadrant evaluation that does not implement segment withholding with a buffer or catalogue-derived feature rebuilding. The script's purported leakage canary (`AUC=0.68`) and registry correlation/overlap (`0.42`, `38.2%`) are hard-coded. Running the script therefore produces a plausible-looking but scientifically unsupported raster and report. **The generator is disabled by default pending real inputs and a compliant evaluator.**

The local zero-filled TIFFs were independently opened with rasterio during review. They are single-band float32, shape 3730×3292, EPSG:32611, transform `(100, 0, 243350, 0, -100, 4508550)`, `nodata=None`, and their stored values are finite and within [0,1]. This is a **format-only local check against the repository's pinned constants**, not an ORGANIZER-CONFIRMED validator receipt and not a check against the actual official sample-submission file. The validator's optional catalogue check was skipped because labels are absent. Full evidence and limitations are on the audit page.

## Required work before a competition-ready TIF can be generated

1. Obtain authorized official files from the [DrivenData data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/): `training_features.tif`, `labels.tif`, `sample_submission.tif`, and the official fault-segment/catalogue information needed for buffered hide-and-recover. Data are login-gated; no credentials are available to this agent. Do not substitute a mirror until licensing and provenance are documented.
2. Inspect metadata and valid footprint from `sample_submission.tif`; assert every input grid matches it. Do not assume a synthetic footprint is equivalent.
3. Replace the disabled synthesis-only path with a model consuming real bands. Derive catalogue-based features from visible fault segments only; withhold complete segments plus the prescribed buffer, mask visible faults pixel-exactly, and evaluate pooled DTI with α=0.2, β=0.8, and the 300 m triangular kernel.
4. Run each feature alone as a leakage canary. Report a feature AUC above 0.90 as leakage until independently explained.
5. Compare the candidate to the incumbent and appropriate random/baseline controls on the same spatially blocked folds; report the evaluator version, withheld-positive count, and defensible 95% CI. Do not use a projected score as a result.
6. Compare final dots/raster against the full registry before any weekly slot selection. Log a duplicate and stop if Spearman rank correlation exceeds 0.90 or over 70% of dots are within 3 px of a registry raster.
7. Generate a unique note ≤140 characters, validate the written file by reopening it against the official template, and only then have the separate selector decide whether it should consume a weekly submission slot.

## Repository contents

- `docs/` — GitHub Pages research, audit, sources, hypotheses and historical fixtures.
- `src/gemsdoe74/` — feature experiments, emission, metric, grid and writer code; not all modules implement the required competition protocol.
- `scripts/generate_submission.py` — intentionally fails closed; current synthetic implementation must not be used for competition predictions.
- `scripts/validate_submission.py` — local format checks; catalogue check only runs if `/tmp/gems74_data/labels.tif` exists. A pass is not an official receipt.
- `data/` — ignored placeholder. Place authorized official files here; never commit competition labels or private data.
- `PROMPT.md` — standing project brief. Read this and the current audit before each project session.

## Reproduce local checks

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt pytest
.venv/bin/pytest -q
.venv/bin/python scripts/validate_submission.py docs/downloads/gemsdoe74-h74-1-basement-step-35641-20261021T000000Z-100b4b19-zeros.tif
```

The test suite is software-level testing only; it does not prove the model's geological validity. The `test_canary` unit test checks that the canary helper detects a deliberately leaking toy feature; it does not test real competition features unless an authorized holdout is implemented.

## Why the GEMSDOE32 `h33-h33-2-b2` result is not explained by the repo

The prompt associates that file with a 0.2778 score. This repository has no organizer receipt linking that file/name to a score, and the public leaderboard is a separate source of evidence. A sparse output can plausibly benefit from the asymmetric distance-weighted Tversky objective, but a claim that a specific Poisson spacing, catalogue exclusion, or dot budget caused the named score needs the original raster, exact evaluator, and receipt. Treat the explanation in prior site content as a hypothesis, not a verified causal finding. The current landing-page snapshot records the public leaderboard source separately; do not conflate a file's organizer-reported result with a public leaderboard row.

## Verified-source entry points

- [DrivenData problem, metric and task description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData about page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [DrivenData data tab (login required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [DrivenData/NLR reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [NLR GEMS report PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN data description](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [GDR submission 1391 / INGENIOUS](https://gdr.openei.org/submissions/1391)
- [EPSG:32611](https://epsg.io/32611)

Sources provide review links; a URL alone is not a verification. The audit pages distinguish in-repository checks from facts that still require access to official competition data or a submission receipt.
