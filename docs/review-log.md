# GEMSDOE74 review log

Review date: 2026-10-21. This log records implementation/reconciliation passes and synthetic tests. It does not record a real-data experiment, a valid competition holdout score, or an organizer receipt.

## Pass 1 — establish the safe project foundation

- Confirmed the branch's starting revision contained only `README.md` and no data/model code.
- Added the durable project brief, fail-closed static site, executive upload guide, source and irregularity ledgers, run card, readiness audit, and tests.
- Kept local competition rasters/caches out of Git and enabled a public download only behind the readiness manifest.

## Pass 2 — reconcile upstream main and inspect the H74-A lane

- Fetched and merged the then-current `origin/main` into the active branch after PR #3 reported conflicts. Resolved `.gitignore`, `README.md`, `docs/index.html`, and `docs/executive-summary.html` to preserve the H74-A context while keeping the status blocked.
- Read the merged project brief. It selects H74-A (hydrothermal spring chains plus potassic K/Th alteration halos) as the one lane for this project session. Replaced the incoming alternate-lane backlog with four qualitative H74-A ablations; no numeric improvement is forecast.
- Reviewed the incoming artifact, format receipt, build metadata, and both holdout evidence files. The strongest stored result is **HOLDOUT-DTI v0.2-segment-proxy: candidate 0.001619 versus random-control 0.031034; 12,088 withheld positives; 95% CI unavailable**. It has no buffer and no fold-specific reconstruction of catalogue-derived features, so it is negative/noncompliant and not a valid baseline. The v0.1 pixel proxy also lacks compliant reporting. No organizer-confirmed receipt exists.
- Moved the unchanged prior TIFF, NaN twin, ZIP, and format receipt from public `docs/downloads/` to `archive/h74-a/`. Updated evidence/build paths and marked the archive not approved; no raster was created during this branch session.
- Refactored the shared `evaluate_holdout.py` entry point to use one buffered whole-segment engine. The engine uses 8-connected components, four spatial folds, a 1.5 km feature-construction collar, exact visible-fault scoring masks, pooled DTI, repeated draws/percentile CI, fold-aware callbacks, and a strict AUC leakage canary. Fixed-raster CLI evaluation requires an explicit catalogue-independence assertion.
- Hardened the shared H74-A builder to write only into ignored `outputs/unapproved/`, derive output geometry from the sample raster, emit only one local zero-mode TIFF when explicitly opted in, and mark its own output unapproved. Its full-catalogue spring-distance field remains noncompliant for holdout work; no command was run to generate a TIFF.
- Replaced the hardcoded submission validator with an explicit candidate/sample-grid validator and updated readiness to check the actual shared tool names. Added reproducible dependency manifests for the raster tools and test runner.
- Did not fetch competition data, run the mirror, access external portals, or claim verified source coverage; this environment has no competition login and its egress restrictions exclude those sources.

## Pass 3 — verify code, site, and fail-closed state

- Python compilation passed for the readiness checker, shared evaluator/entry point, generator, validator, metric, and tests.
- `python -m unittest discover -s tests -v`: 19 tests passed. This standard-library runner executes the `unittest` classes; the project-wide pytest run below also includes the function-style metric tests.
- `python -m pytest -q`: **23 passed**. Tests cover synthetic holdout mechanics, exact visible-mask behavior, AUC threshold handling, sample-grid validation, the generator's default safety guard, readiness, site links/fragments, and absence of public raster/ZIP downloads. They do not validate real competition data.
- `scripts/check_readiness.py --write docs/data/readiness.json` reports **BLOCKED**, with all required inputs absent, no feature-cache or scientific receipts, and all download fields disabled. `--strict` returned the expected exit code `2`.
- The site-link/fragment test passed, including `irregularities.html#holdout`. The site contains no `.tif`, `.tiff`, or `.zip` under `docs/`; the archived files are outside the public site.
- No real-data holdout, feature-alone canary, registry comparison, official-grid validator run, new candidate raster, submission slot, or organizer-page receipt was produced.

## Final verdict

**BLOCKED / NOT RUN.** The selected H74-A lane is documented, but there are no official inputs/cache, no fold-visible-only spring builder, no valid current holdout-best baseline, no complete registry, and no real-data validator receipt. The archived H74-A proxy is negative and noncompliant; it is not a submission. No new GeoTIFF was generated, and the public download gate remains disabled.
