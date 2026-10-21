# GEMSDOE74 — DOE GEMS Prize research and submission tooling

> **Core Values:** Maximize P(Win); Own the Outcome. Evidence and release readiness are separate: a technically well-formed GeoTIFF is not evidence of a good geological prediction.

## Current release decision: **HOLD — DO NOT SUBMIT**

This repository currently contains **no scientifically validated competition prediction**. The GeoTIFFs under `docs/downloads/` are historical **format/research fixtures only**. H74-1 and H74-1v2 were generated from synthetic prediction fields/targets; H74-A used sibling-mirror inputs of unverified provenance/rights and an invalid proxy holdout. None is validated against authorized official training features and labels. Format checks do **not** validate prediction quality, exact footprint agreement with DrivenData's template, catalogue exclusion, uniqueness against the full registry, or expected leaderboard score. No organizer submission receipt exists for any artifact.

- The landing page and [submission guide](docs/executive-summary.html) explicitly say **DO NOT SUBMIT**.
- H74-1 fixture: [zeros TIFF](docs/downloads/gemsdoe74-h74-1-basement-step-35641-20261021T000000Z-100b4b19-zeros.tif) — synthetic output; format inspection only; not cleared.
- H74-A fixture: [zeros TIFF](docs/downloads/gems74-h74-alt-spring-39500-20261021T000000Z-52f76038-zeros.tif) — provenance unverified; format inspection only; not cleared.
- H74-1v2 fixture: [zeros TIFF](docs/downloads/gemsdoe74-h74-1v2-basement-step-36270-20261021T000000Z-5a03072f-zeros.tif) — synthetic output; format inspection only; not cleared.
- Auditable findings: [repository review](docs/review/repo-audit-2026-10-21.html), [irregularities](docs/irregularities.html), [run card](docs/data/run-card.json).

Legacy H74-1/H74-1v2 reported holdout scores, confidence intervals, AUCs, uniqueness values, and `promote` verdicts are **not valid evidence**: scripts construct synthetic prediction fields/hidden positives, and one legacy path hard-coded canary/registry values. Do not cite them as valid HOLDOUT-DTI results. Raw historical evidence is retained only where explicitly marked invalid; the active run card reports null for unavailable results. H74-A's proxy holdout files also do not meet the required real-data protocol.

A prior `MEASURED-FILE-AUDIT` used a hash-pinned **owner mirror, not organizer-authenticated**: it reported 20,013 H74-1 positive cells outside that mirror's footprint. The mirror data are absent here, so this finding is not independently reproduced and cannot establish the official footprint. This discrepancy reinforces that the H74-1 file is not cleared.

## The most important code-review finding

The former `scripts/generate_submission.py` and `scripts/generate_h74v2.py` were not real-data model pipelines. They synthesize prediction fields and hidden labels; the evaluation does not implement buffered whole-segment withholding or visible-only catalogue-feature rebuilding. The first path hard-coded leakage/registry fields. Both commands now fail closed and cannot write a candidate or evaluation report. The old `scripts/evaluate_holdout*.py` entry points also fail closed.

The local TIFF metadata was inspected with rasterio. The zeros fixture is single-band float32, shape 3730×3292, EPSG:32611, transform `(100, 0, 243350, 0, -100, 4508550)`, `nodata=None`, and stored values are finite within [0,1]. These are **MEASURED-LOCAL** file facts only, checked against pinned repository constants. The official problem page says cells outside training bounds must be null/NaN; with the official sample template absent, this review cannot determine which cells are out of bounds, so zero-filled output is not confirmed competition-format compliant. No organizer receipt exists. The updated validator marks template/label checks unavailable when those inputs are absent. See the audit and [source register](docs/sources.html).

## Required work before a competition-ready TIF can be generated

1. Obtain authorized official files from the [DrivenData data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/): `training_features.tif`, `labels.tif`, `sample_submission.tif`, and the official fault-segment/catalogue information needed for buffered hide-and-recover. Data are login-gated; no credentials are available to this agent. Do not substitute a mirror until licensing and provenance are documented.
2. Inspect metadata and valid footprint from `sample_submission.tif`; assert every input grid matches it. Do not assume a synthetic footprint is equivalent.
3. Replace the disabled synthesis-only path with a model consuming real bands. Derive catalogue-based features from visible fault segments only; withhold complete segments plus the prescribed buffer, mask visible faults pixel-exactly, and evaluate pooled DTI with α=0.2, β=0.8, and the 300 m triangular kernel.
4. Run each feature alone as a leakage canary. Report a feature AUC above 0.90 as leakage until independently explained.
5. Compare the candidate to the incumbent and appropriate random/baseline controls on the same spatially blocked folds; report the evaluator version, withheld-positive count, and defensible 95% CI. Do not use a projected score as a result.
6. Compare final dots/raster against the full registry before any weekly slot selection. Log a duplicate and stop if Spearman rank correlation exceeds 0.90 or over 70% of dots are within 3 px of a registry raster.
7. Generate a unique note ≤140 characters, reopen and validate the written file against the official template, and write null/NaN outside its valid bounds as required by the official problem page. Only then may the separate selector decide whether it should consume a weekly submission slot.

## Repository contents

- `docs/` — GitHub Pages research, audit, sources, hypotheses and historical fixtures.
- `src/gemsdoe74/` — feature experiments, emission, metric, grid and writer code; not all modules implement the required competition protocol.
- `scripts/generate_submission.py` — intentionally fails closed; current synthetic implementation must not be used for competition predictions.
- `scripts/validate_submission.py` — local format checks. It uses optional `data/sample_submission.tif` and `data/labels.tif` when present; absent inputs are reported as unavailable. A pass is not an official receipt.
- `data/` — ignored placeholder. Place authorized official files here; never commit competition labels or private data.
- `PROMPT.md` — standing project brief. Read this and the current audit before each project session.

## Reproduce local checks

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt pytest
.venv/bin/pytest -q
.venv/bin/python scripts/validate_submission.py docs/downloads/gemsdoe74-h74-1v2-basement-step-36270-20261021T000000Z-5a03072f-zeros.tif
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
