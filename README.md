# GEMSDOE74 — auditable GEMS discovery and submission workflow

> **Current status: BLOCKED — there is no validated submission GeoTIFF in this repository. Do not download or submit a file from this project yet.** The repository started with only this README. It has no competition rasters, cached feature stack, holdout evaluator, submission writer, registry rasters, or candidate GeoTIFF. No synthetic or copied submission has been created.

## Read this file at the start of every session

This is the persistent operating brief for GEMSDOE74. Read it before changing code, researching data, running experiments, or recommending a submission. Keep the project focused on a reproducible, scientifically defensible GEMS competition workflow—not a score-looking website or an unverified raster.

## Mission and project brief

Build a clean, useful, auditable research system for the DOE GEMS Prize Challenge that can develop **a unique** prediction GeoTIFF, evaluate it before any competition slot is used, and make the final file easy to identify and download **only after it is validated**. The landing page must make the submission state obvious. A separate executive-summary page must give exact upload steps, a unique submission name, and a concise note. Keep a source ledger, hypotheses, irregularities, evaluation evidence, and a current-status feed; distinguish official facts, repository claims, model projections, and unverified user reports.

The long historical score list in the initiating request is a set of user-provided claims, not a substitute for organizer receipts. Do not silently convert it into an official leaderboard, a holdout result, or proof of causation. The original request also asks for research into geothermal vents, public official data, a GitHub Pages site, a submission process that prevents the `[0, 1]` validation error, repeated review passes, and an autonomous workflow that reports its limitations. This README is the durable, auditable version of that brief; the linked site pages hold the current source ledger, submission instructions, hypotheses, and irregularities.

### Core values

- **Maximize P(Win):** prefer evidence and expected value over novelty for its own sake; do not spend a live submission slot on an idea that has not beaten the current holdout best.
- **Own the outcome:** record failures and blockers, fix shared tooling in its authoritative template rather than forking it, and never report a projection as a score.

## Non-negotiable experiment and submission protocol

1. **One lane only.** Do not generate competing surfaces in parallel. The initiating request refers to a single method paragraph/lane, but no such paragraph is present in the text available to this repository. Until a specific lane is documented and cleared against the registry, treat proposed methods as a research shortlist, not as eligible experiments.
2. **Reuse shared tools.** Use the template's cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`. Do not build a private replacement evaluator/writer. If shared tooling is wrong, fix it in the shared template and document the change. None of these tools or the cache was present in this checkout at review time.
3. **Holdout protocol.** Hide whole fault segments with a buffer; derive every catalogue-based feature from visible faults only; mask visible faults pixel-exactly; evaluate pooled DTI with alpha `0.2`, beta `0.8`, and a `300 m` triangular kernel. Test each feature alone first. An AUC above `0.90` is a leakage canary until explained. These are protocol parameters, not measured results.
4. **Duplicate guard.** Before placement and on final dots, compare against every registry raster. If rank-correlation exceeds `0.90`, or more than `70%` of dots fall within `3 px` of one registry raster's dots, log a duplicate and stop. Registry rasters are not present here, so uniqueness has not been established.
5. **Evidence labels.** Every reported score must be either `HOLDOUT-DTI` with evaluator version, withheld-positive count, and `95% CI`, or `ORGANIZER-CONFIRMED` copied from a submission-page receipt. Label projections as projections and never present them as scores. Keep negative results as deliverables.
6. **Budget and slots.** Stop after at most three experiments or two hours for the parallel-run lane. Promotion to a real competition slot is a separate selector decision and must respect the current weekly cap shown on the submission page. A holdout result is required before selection; no slot was touched in this review.
7. **Unique artifact.** Never reuse or copy a prior submission raster except for explicitly educational inspection. Do not produce a random, zero-filled, or placeholder GeoTIFF and call it a submission. Make the download control say **not available / do not submit** until the real candidate, geometry, value range, duplicate check, validator receipt, and provenance are all verified.

## Current repository review — 2026-10-21

- The starting Git tree contained only `README.md` (`# GEMSDOE74`). There was no `data/` directory or code to reuse.
- The official organizer reference repository is [drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution). Its README was inspected through the GitHub API. It instructs users to download competition data from DrivenData into `data/`; it offers CPU-only and GPU environment choices and says a GPU trains faster. This supports that missing data—not merely a missing GPU—is the immediate blocker. The competition data itself was not downloaded here.
- The public [GEMSDOE32 README](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/README.md), [site index](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/index.html), and [machine-readable feed](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/data/feed.json) were inspected for learning only. That owner-authored archive describes the H33-2-B2 file as a two-cell catalogue-flank prune of an earlier emission, labels its live value as a **projection**, and says no organizer score exists for artifacts in that repository. This does **not** establish that the H33 file received an organizer-confirmed score. It also does not establish that its method caused the score claimed in the initiating request. No earlier GeoTIFF was copied into this repository.
- The initiating request gives conflicting leaderboard-high claims and a separate score for the H33 artifact. Neither an organizer receipt nor a current leaderboard snapshot was available in this checkout. The values are therefore not repeated here as verified scores. Treat this inconsistency as an open irregularity; check the official leaderboard and the original submission receipt before making score comparisons.
- The official competition pages, the cited GDR/USGS pages, and the submission PDF could not be fetched in this environment. The outbound-access allowlist permits GitHub and package hosts, not those domains; the DrivenData data page is also reported in the initiating brief to require authentication. Links are preserved for manual review, but no facts from inaccessible pages are represented as freshly verified.
- No spatial holdout, leakage canary, registry-raster correlation/overlap check, TIFF validator, or submission was run. **No new TIF exists. It is not OK to download or submit a GEMSDOE74 file.**

### What can—and cannot—be concluded about the H33 claim

The H33 archive makes a *method* claim: remove predicted pixels near the known-fault catalogue from a prior surface. This is spatial post-processing of an existing emission, not an independent geological observation. If a comparable official score improvement were verified, plausible explanations would include lower credit spent on catalogue-adjacent false positives or a change in precision/recall balance. The operation also removes any true target faults in the same belt, so its sign depends on which withheld segments the removed pixels would have matched under the kernel—not on the fact that the pixel count fell. Under the prescribed HOLDOUT-DTI protocol (alpha `0.2`, beta `0.8`, `300 m` triangular kernel), that tradeoff must be measured with the exact evaluator; Tversky conventions can differ over which error receives each coefficient. This is only a mechanism-level hypothesis. Without the exact organizer receipt, original baseline and candidate rasters, scorer implementation, holdout outputs, and registry-comparison evidence, it is not possible to say why the H33 artifact obtained the reported value, prove that it was the highest-scoring file, or infer that a different unique surface would score higher. The archive itself distinguishes its projection from an organizer score. Do not treat a projection as evidence of a leaderboard result.

The [organizer reference notebook](https://github.com/drivendataorg/gems-prize-reference-solution/blob/main/unet-mc-cv-reference-solution.ipynb) is a baseline, not an explanation of H33. Its code describes a U-Net trained on patches across repeated random splits, uses a Tversky loss with false-negative weight larger than false-positive weight, and applies sigmoid to predictions. Its example writer copies CRS/transform from the fault-label raster and does not re-read the written output to validate its range or compare it with the official sample-submission grid. Random patch splits may leave spatial dependence between train and test patches; the required whole-segment spatial holdout is therefore the more appropriate decision gate. The notebook's loss parameters do not establish the competition scorer's exact implementation, nor do they prove that any historical file achieved a score.

## Candidate hypotheses and gating

The initial research shortlist is on [Research & hypotheses](docs/hypotheses.html). It ranks three not-yet-cleared approaches, names the layers and physical signatures, explains the off-catalogue rationale and likely non-fault mimics, and gives the exact official data portals needed. The current checkout cannot verify availability or run the top candidate: data, the shared feature cache/evaluator/writer, and registry rasters are absent. Accordingly, the shortlist is **not** a permission to run or submit an experiment. It is not possible to claim that these methods are unique across every GEMSDOE site until their raster registry is checked.

## Submission status and instructions

The landing page is [GEMSDOE74](docs/index.html); the [executive summary](docs/executive-summary.html) explains the complete submission workflow and the prior “Predicted values must be in range `[0, 1]`” error. The site deliberately has no active download button while status is blocked. Once a candidate has a valid shared-writer receipt and passes the holdout, duplicate, geometry, range, and provenance gates, the actual GeoTIFF and its short name/note can be added.

For current readiness, run:

```bash
python3 scripts/check_readiness.py --write docs/data/readiness.json
python3 -m unittest discover -s tests -v
```

The readiness audit reports missing prerequisites; it does **not** train a model, evaluate DTI, validate a GeoTIFF, or produce a submission.

## Official sources and review links

- [Competition home and rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [About page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [Competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Organizer reference solution on GitHub](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDawn data page](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [GDR submission 1391](https://gdr.openei.org/submissions/1391)
- [Submission guidance PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [EPSG:32611 reference supplied in the brief](https://epsg.io/32611)

The source register on the site marks each link as accessed, not accessed, official, or owner-generated. A source link is not itself proof that a claim has been verified. The three required implementation/review passes are recorded in [`docs/review-log.md`](docs/review-log.md).

## Session review checklist

- [ ] Read this README and review the current branch/status before work.
- [ ] Confirm the project brief, protocol, and single lane; do not assume a missing method paragraph.
- [ ] Confirm official-source access and data provenance; preserve hashes and licences.
- [ ] Reuse the shared stack, evaluator, and writer; run each feature's leakage canary.
- [ ] Run the preregistered spatial hide-and-recover holdout and compare with the current holdout best.
- [ ] Check candidate/final correlation and three-pixel registry overlap before placement.
- [ ] Validate one-band GeoTIFF geometry and numeric values; store a receipt and SHA-256.
- [ ] Only then show a download link, unique submission name, and concise comment; record the organizer receipt separately.
- [ ] Review once for bugs, again for assumptions/edge cases, and a final time against this brief.
