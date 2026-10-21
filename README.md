# GEMSDOE74 — fault-discovery research, integrity hold

## Download status: review only — **DO NOT SUBMIT**

**No competition-ready new TIFF was generated in the 2026-10-21 audit.** The previous H74-1 generator used synthetic geological fields and synthetic truth, hard-coded its canary AUC, and invented registry comparisons. It has been disabled. A valid file format is not evidence of predictive skill or uniqueness.

[Open the download/status page](https://buffedlizard55-lab.github.io/GEMSDOE74/) · [Executive summary](docs/executive-summary.html) · [Audit](docs/audit-20261021.html) · [Machine-readable run card](docs/review/data/run-card.json)

The old TIFFs remain downloadable **for education/review only**, not as promoted submissions. No weekly slot was used. No organizer-confirmed score is available for this repository. The user's leaderboard figures conflict; none is treated as a current verified leaderboard reading.

## Start every session here

Read this README, [task requirements](PROMPT.md), and the audit before changing code. PROMPT.md is a condensed record, **not the full verbatim user prompt**. The complete original prompt remains in the conversation; verbatim archival is unfinished.

**Core Values — Maximize P(Win), Own the Outcome:** protect scarce submission slots, expose invalid evidence, test claims instead of inventing results, and own the download-to-validation path.

The latest user message refers to a “single method paragraph” but supplies none explicitly. We retain the existing **H74-1 basement-step ridge gated by surface quiescence** lane. No other lane has been trained.

## What this review verified

- Retrieved pinned sample-grid and catalogue mirrors using `scripts/fetch_data.sh data/mirror`. Their hashes match the existing receipts. These are **owner mirrors, not authenticated organizer downloads**.
- Retrieved the H33-2-B2 owner audit and reference TIFF for learning/comparison only. No prior raster was copied into a new submission.
- Reopened both historical all-finite TIFFs. File checks and measured comparison against this **one** reference are in [file audit](evidence/file-audit-20261021.json). This does not clear the full registry gate.
- Located the referenced feature-cache receipt in GEMSDOE32: `/tmp/gems32/work/feature_stack.npy`. The actual cache is not present in this checkout or that repository's inspected tree. A separate manifest identifies mirrored raw numerical features, but rebuilding is not equivalent to reusing the required cache.
- Confirmed that `scripts/download_competition_data.sh` was an instruction printer, not an automatic downloader. Preparation previously wrote success even when required files were absent; it now fails and removes stale success.
- The legacy segment evaluator explicitly disables the required buffer and scores a precomputed prediction. It is **not protocol-compliant**. Neither old holdout establishes promotion.

## Why the reported H33 result might be strong

The user-reported H33 result is **not ORGANIZER-CONFIRMED**: the retrieved owner audit calls the candidate UNSCORED and contains a projection. It documents pruning dots close to mapped faults from an existing sparse prediction. That is evidence of construction, not a submission-page receipt or proof of causality.

Under the implemented distance-weighted Tversky objective, pruning predictions that add little truth coverage can reduce false-positive cost. Sparse placement can preserve coverage while reducing redundant mass. But two kernel discs spaced less than twice their radius still overlap: the old claim that 280 m spacing prevents overlap of 300 m kernels was wrong. The exact marginal improvement condition is `(1 − alpha*S)*deltaTP > alpha*S*deltaFP` when alpha+beta=1 and truth is fixed. The shortcut `k > alpha*S` requires the special assumption deltaTP=k and deltaFP=1−k; it is not a general dot-placement theorem.

Better detection of concealed boundaries could improve credit per prediction. Nothing here proves a score above the supplied benchmarks. Fault mapping is a geothermal exploration proxy, not direct detection of vents or confirmation of a resource.

## Ranked, untested hypotheses within the existing lane

Ranking is qualitative scientific judgment, **not projected DTI**. Novelty is relative to the inspected local code, not a claim of novelty across every sibling repository. All require recovery of the genuine shared cache and verification of band descriptions; previous hard-coded band numbers are untrusted.

| Priority / cost | Layers and signature | Why potentially off-catalogue; distinction | Non-fault mimic |
|---|---|---|---|
| First / low | Depth-to-basement, detrended elevation slope: gradient ridge with stable location across smoothing scales, downweighted when unstable | Concealed block edge under low-relief cover; replace the synthetic lane's simple scale fusion with an explicit ridge-location stability test | Buried paleochannel margin |
| Second / medium | Same depth and relief: compare signed profiles across each ridge for a persistent step rather than symmetric valley | A buried offset may lack a surface trace; reject symmetric troughs instead of merely increasing gradient magnitude | Asymmetric sedimentary basin margin |
| Third / medium | Same layers: remove broad regional trend before gradient extraction; require residual ridge plus surface quiescence | Expose small concealed offsets masked by basin-scale thickness trends; not implemented as explicit trend-residual agreement locally | Interpolation seam in the basement model |
| Fourth / medium | Same layers: penalize ridges that migrate under nodata-edge perturbations and resampling | Prioritize buried structures robust to gridding, not catalogue proximity; adds an uncertainty gate absent locally | Survey-resolution boundary |

These are proposals, **not validated viable candidates**. No new external dataset is necessary in principle; the indispensable existing cache and its provenance are missing. If it cannot be restored, stop and revise the reuse protocol before rebuilding. Do not switch into magnetic, spring, or radiometric lanes.

## Reproducible checks

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q
bash scripts/fetch_data.sh data/mirror
# H33 comparison also needs the reference TIFF identified by evidence/h33-owner-audit.json
.venv/bin/python scripts/audit_existing.py
.venv/bin/python scripts/build_site.py
# Deliberately fails closed; never silently generates synthetic competition evidence:
.venv/bin/python scripts/generate_submission.py
```

`gems74.metric` is the canonical soft-prediction implementation. The legacy wrapper now delegates rather than silently binarizing probabilities. Canary evaluation fails on missing classes/nonfinite data and flags either direction of near-perfect separation. These unit checks do **not** validate a model.

## Sources and limitations

- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), read through GitHub API; preserved README: `evidence/reference-solution-readme.md`.
- [H33 owner audit](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json), read; secondary evidence only.
- [Cache receipt](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/registry/feature_receipt.json), read; receipt is not the cache.
- [Raw-data manifest](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/registry/data_manifest.json), read; pinned bytes do not authenticate rights or semantics.
- [Official problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [submission/data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [USGS survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and): manual-review links, **not reverified in this network-restricted session**.

No DrivenData browser session, submission receipts, current weekly-cap evidence, complete registry, or shared numerical cache is available. The network allowlist excludes Dropbox, DrivenData, and USGS. GitHub access works. Do not request credentials in chat. No GPU necessity has been established for this CPU-compatible lane.

## Next-session priority

1. Restore the shared cache with hashes, band names, footprint and input-rights provenance. Use the mirrored raw manifest only if rebuilding is explicitly approved.
2. Repair the shared evaluator once: whole-segment buffered hiding, fold-local catalogue features and placement, pixel-exact visible masking, pooled counts, block-bootstrap confidence interval, feature-wise canaries.
3. Load the full parallel-run registry and continuous surfaces. Stop before placement for rank correlation above the protocol threshold; stop after placement for excessive proximity overlap. Missing comparisons block promotion.
4. At most three experiments, compare against the incumbent on identical folds; save a unique TIFF through the existing writer only after these prerequisites. Independently select promotion within the verified weekly cap.

The website is a static audit/download site, not an automated live leaderboard or in-browser training service. Full cross-repository review, valid new TIFF generation, and compliant model evaluation remain unfinished. Historical pages carry a warning and must not override this audit.
