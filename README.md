# GEMSDOE74 — auditable GEMS research and submission workflow

> **Current status: BLOCKED — no GEMSDOE74 artifact is cleared for a competition slot.** The repository now contains an archived H74-A experimental GeoTIFF from an earlier branch, but its recorded catalogue holdout is negative and the evaluator omits the required spatial buffer and confidence interval. Its format receipt is not a scientific promotion receipt. Do **not** download or submit it from this site. This branch did not generate or copy a submission raster.

## Read this file at the start of every session

This is the persistent operating brief. Read it before changing code, researching data, running experiments, or recommending a submission. Build a reproducible, scientifically defensible GEMS workflow—not a score-looking website or an unverified raster.

## Mission and durable prompt

Develop a clean, useful, auditable system for studying geothermal-indicative faults and producing a **unique** prediction GeoTIFF only after it beats the current holdout best. The landing page must make the exact download/submission status obvious. A separate executive-summary page must explain the upload steps, show the unique name and short note, and prevent the prior range-validation error. Maintain evidence, research hypotheses, an irregularities ledger, and a current-status feed that distinguishes official facts, owner-generated results, holdout metrics, and projections.

The initiating request also asks for deep research based on official public sources, three to five novel geological hypotheses ranked by expected value and cost, validation of the top candidate before any weekly submission slot, a full source ledger, three review passes, and autonomous work without asking for credentials. It emphasizes Arena's values: **Maximize P(Win)** and **Own the Outcome**. Historical result lists supplied in chat are claims to check, not a verified leaderboard or a substitute for receipts; this repository does not reproduce those scores as facts.

## Non-negotiable experiment and submission protocol

1. **One lane.** The merged upstream project brief selects H74-A: hydrothermal spring chains plus potassic K/Th alteration halos. Keep experiments inside that lane; do not switch to ASTER, seismicity, InSAR, or another method family. The original initiating text's referenced method paragraph was missing, but current main's H74-A brief resolves the lane for this project session.
2. **Reuse the shared template.** Use the shared feature cache, holdout evaluator, and submission writer. Fix a wrong shared tool in place and report the change; do not keep a private fork or create a second writer. Current main provides `scripts/evaluate_holdout.py`, `scripts/evaluate_holdout_segments.py`, `scripts/generate_submission.py`, and `scripts/validate_submission.py`; no cached feature stack and no file literally named `submission_writer.py` are present. The evaluator entry point now delegates to the repaired buffered-segment engine. The legacy H74-A builder is explicitly unapproved and still lacks fold-visible-only feature construction.
3. **Required holdout.** Hide whole fault segments with a buffer; derive every catalogue-based feature from visible faults only; mask visible faults pixel-exactly; evaluate pooled DTI using alpha `0.2`, beta `0.8`, and a `300 m` triangular kernel. Test each feature alone. An AUC above `0.90` is a leakage canary until explained. These are protocol parameters, not measured results. A reported HOLDOUT-DTI must identify the evaluator version, withheld-positive count, and `95% CI`.
4. **Duplicate guard.** Compare the proposed surface before placement and the final dots against every registry raster. If rank-correlation exceeds `0.90`, or more than `70%` of dots fall within `3 px` of a registry raster, log a duplicate and stop. The current repository has a prior raster but not the complete registry; uniqueness has not been established for any new surface.
5. **Evidence labels.** Every reported score must be either `HOLDOUT-DTI` with evaluator/version, withheld-positive count, and confidence interval, or `ORGANIZER-CONFIRMED` copied from a submission-page receipt. A projection is never a score. Keep negative results as deliverables.
6. **Budget and slots.** Stop after at most three experiments or two hours for the parallel lane. Promotion to a real competition slot is a separate selector step and must respect the current weekly cap shown on the submission page. Do not spend a slot on an idea that has not beaten the valid current holdout best. No slot was used in this review.
7. **Unique artifact.** Do not copy a prior raster except for learning. Do not create a random, zero-filled, or placeholder TIF and call it a submission. The download control must remain disabled unless the candidate, input provenance, holdout, leakage, registry checks, format validation, hash, name, and note all have verifiable receipts.

## Current repository review — 2026-10-21

This branch began at an initial commit containing only `README.md`. During this session, `origin/main` advanced with an earlier H74-A experiment and shared scripts. The branch was synchronized with that mainline so the pull request will not discard concurrent work. The H74-A TIF is retained only as an existing, owner-generated research artifact; this session did not copy it or treat it as submit-ready.

### Existing shared code and why the gate remains closed

- **Data mirror:** `scripts/fetch_data.sh` retrieves hash-pinned files from another GEMSDOE GitHub repository into `data/` by default (or `GEMS74_DATA_DIR`). It lists a sample-submission grid, labels, and selected external layers; it does not provide the full competition `training_features.tif`, the one-meter DEM links, or the complete cached feature stack. A hash-pinned mirror is not itself proof of official provenance. The official competition data page is reported to require login; this environment has no DrivenData login and its network allowlist excludes DrivenData, USGS, NLR, NASA LP DAAC, and GDR. The fetch script was not run.
- **Holdout:** the prior `scripts/evaluate_holdout.py` sampled individual catalogue pixels, and prior `scripts/evaluate_holdout_segments.py` hid segments without a buffer or confidence interval. The shared entry point now delegates to a single repaired engine: whole 8-connected segments are withheld in four spatial folds; a 1.5 km collar is excluded from feature construction; visible-fault pixels are masked exactly for scoring; repeated draws report pooled DTI and a percentile 95% interval. Catalogue-dependent predictions must be rebuilt by a fold-aware callback that receives only visible faults. The CLI refuses prebuilt rasters unless explicitly declared catalogue-independent. No real-data evaluation has been run, so the prior H74-A proxy remains negative/noncompliant and is not a promotion result.
- **Writer/validator:** `scripts/generate_submission.py` is a legacy H74-A experimental builder, not a generic writer. It now writes only under ignored `outputs/unapproved/`, requires an explicit opt-in, derives grid metadata from the sample raster, emits only one zero-mode TIF, and does not update the tracked registry. It still uses a full-catalogue spring-distance field and is therefore not fold-visible-only. `scripts/validate_submission.py` now requires a candidate and sample raster and independently checks the reread file's band, dtype, exact sample-grid CRS/shape/transform, finite values, `[0,1]` range, and nodata policy. A format pass is never a scientific approval.
- **Prior H74-A artifact:** the incoming main branch exposed the archived zero-mode TIFF and ZIP under public `docs/downloads/` and labeled the TIFF as downloadable despite its negative holdout. This branch moves those unchanged artifacts to `archive/h74-a/`, records the noncompliant result and its 12,088 withheld positives, and keeps the site/readiness gate **BLOCKED**. The archived raster is not a new result, baseline, or submission.
- **H33 score claim:** the public [GEMSDOE32 README](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/README.md), [site source](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/index.html), and [feed](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/data/feed.json) were inspected for learning only. The archive describes H33-2-B2 as a catalogue-flank prune of a prior emission, labels its displayed live value as a **projection**, and says no organizer score exists for its artifacts. That does not substantiate the H33 score claim in the initiating prompt. The official submission receipt was not available.
- **Leaderboard claims:** the initiating prompt gives incompatible “current high” claims. No current official leaderboard response or submission-page receipt was fetched, so those values are not repeated as verified scores.
- **Official reference solution:** the [organizer repository](https://github.com/drivendataorg/gems-prize-reference-solution) README and [reference notebook](https://github.com/drivendataorg/gems-prize-reference-solution/blob/main/unet-mc-cv-reference-solution.ipynb) were inspected through the GitHub API. The README supports CPU-only as well as GPU environments and says GPU training is faster. The notebook demonstrates a patch-based U-Net, random patch splits, Tversky loss, sigmoid probabilities, and an example writer that copies georeferencing from the label raster. It is a baseline—not evidence for H33, not a spatially blocked holdout, and not a substitute for post-write validation against the official sample grid.
- **No current experiment:** no new candidate surface, TIF, holdout, leakage test, registry-correlation check, or competition submission was made. No weekly slot was touched. The H74-A sub-hypotheses are blocked by absent official inputs/cache, the lack of a fold-aware generator, and the absence of a valid current holdout-best baseline.

### What can—and cannot—be concluded about the H33 claim

The related archive describes H33-2-B2 as removing predictions near known catalogue faults from an existing emission. This is spatial post-processing, not an independent geological observation. If an official score improvement were verified, plausible mechanisms would include lower false-positive credit spent near catalogue faults or a precision/recall change. The operation can also delete true withheld faults; its sign depends on where those pixels fall relative to the hidden target and the scoring kernel. The exact scorer, baseline raster, candidate raster, valid spatial holdout, and organizer receipt are all needed to establish causation. The archive's projection cannot be treated as a leaderboard result, and it does not show that a different unique surface will score higher.

## Candidate hypotheses and gating

The [Research & hypotheses page](docs/hypotheses.html) ranks four H74-A sub-hypotheses (spring-chain visible-only construction, spring/K–Th consensus, alteration-only, and hot-spring weighting) by expected DTI potential and implementation cost. They are ablations/refinements within the selected lane, not alternate method families or claims of uniqueness. The top hypothesis cannot be tested until the shared inputs/cache, fold-aware spring-distance builder, and a valid holdout-best baseline are available. Official source links are provided for manual review; access and coverage were not checked.

## Submission status and instructions

- [GEMSDOE74 overview](docs/index.html): prominent **BLOCKED / DO NOT SUBMIT** status. It does not link the archived H74-A file as an approved submission.
- [Executive summary](docs/executive-summary.html): step-by-step portal instructions and a fail-closed checklist for the “Predicted values must be in range `[0, 1]`” error reported in the initial brief.
- [Sources](docs/sources.html): official links, access status, and distinction between organizer sources and owner-generated archives.
- [Irregularities](docs/irregularities.html): score, data-access, holdout, and download-gate discrepancies.
- [Three-pass review log](docs/review-log.md): implementation, source/assumption review, and final verification.

The local readiness audit is an evidence gate only. It does not train, compute a real-data DTI, validate a competition raster, or write a TIF. Install the shared tool/test dependencies before running the synthetic unit suite:

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/check_readiness.py --write docs/data/readiness.json
python3 -m pytest -q
```

Competition rasters and caches are ignored by Git; only `data/README.md` is tracked. Do not put credentials or large datasets in the repository.

## Official sources and manual review

- [Competition home and rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [About page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [Competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDawn source](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [GDR submission 1391](https://gdr.openei.org/submissions/1391)
- [Submission guidance PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [EPSG:32611 reference supplied in the brief](https://epsg.io/32611)

The source page marks access state explicitly. A source link is not itself proof that a claim, dataset's availability, or its footprint coverage has been verified.

## Session review checklist

- [ ] Read this README fully and review current branch/status before work.
- [ ] Confirm the single method lane; do not assume the missing method paragraph.
- [ ] Confirm official provenance, access, licensing, hashes, and the template's cache layout.
- [ ] Use the shared evaluator/writer; check each feature alone for leakage.
- [ ] Run a buffered whole-segment hide-and-recover holdout with visible-only catalogue features and pixel-exact masking.
- [ ] Compare the candidate surface and final dots against the full registry before any slot.
- [ ] Validate the written GeoTIFF against the official sample grid and allowed value range; store receipts and SHA-256.
- [ ] Only then expose a download, unique name, and short comment; record the organizer receipt separately.
- [ ] Review once for bugs, again for assumptions/edge cases, and finally against this brief.
