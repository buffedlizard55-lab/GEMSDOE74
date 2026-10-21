# Task requirements — read every session

See README.md for the condensed version. This file is a condensed requirements record, NOT a verbatim transcript. The original user message is the authority.

- Generate a **unique TIF submission** (not a copy) with obvious download, executive summary, and portal-safe validation (values in [0,1], no sentinel, no NaN inside footprint, CRS/shape/transform match).
- Fix `Predicted values must be in range [0, 1]` by engineering out both failure modes: float32 sentinel `-3.402823e38` and NaN/nodata handling; verify by re-reading bytes.
- Provide unique submission name + short note (≤140 chars) for the DrivenData form.
- Create a clean GitHub Pages site (docs/) that is user-friendly, organized, with verified official links, no hallucinations, line-by-line verification.
- Answer why `h33-h33-2-b2` (0.2778) scored highest and whether we can beat it, with PhD-level judgement.
- Generate 3–5 candidate geological hypotheses we haven’t tried, each naming: specific layer(s), physical signature (edge/curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented; rank by expected DTI improvement and implementation cost; validate top on spatially-blocked holdout before spending a weekly slot.
- PARALLEL-RUN PROTOCOL: lane, reuse (cached feature stack, evaluate_holdout.py, submission_writer.py; hide-and-recover with buffer, pooled DTI α0.2 β0.8 300m kernel), label every number as HOLDOUT-DTI or ORGANIZER-CONFIRMED, leakage canary (AUC>0.90 flagged), run card (hypothesis, mechanism, non-fault mimic, holdout DTI+CI, correlation/overlap vs registry, raster sha256, validator output, submission name+note ≤140 chars, verdict promote/negative), budget 3 experiments / 2 h, no private fork, promotion is separate selector step.
- Core Values: Maximize P(Win), Own the Outcome.
- Understand the problem via problem description, about page, data page, reference solution, metric, and submission format; list limitations and needed access; use only free, official, shareable external data.
- Run 3 passes: implement, review/fix, re-check against request; verify line by line, provide links, flag irregularities.
- The site must be able to generate the TIF required for submission and provide an easy download in the executive summary/first fold; it must be obvious whether it is OK to download and submit.
- No DrivenData auth available in sandbox → cannot auto-download training_features.tif, labels.tif, sample_submission.tif, 1m_DEM_links.csv; `scripts/download_competition_data.sh` must be run on an unrestricted machine into data/ then `scripts/prepare_data.py`.

Trust date: 2026-10-21 UTC. Verify all live numbers against the official leaderboard snapshot (human-read, not scraped per Terms of Use).

## Continuing-session requirements (2026-10-21)
Read README and this record first. Work on the existing Arena branch only. Three passes:
implementation, bug/edge-case review, full request recheck. Open a PR and merge when tests pass.
Keep Core Values (Maximize P(Win), Own the Outcome) central; do not spend a competition slot.
Use the existing H74-1 basement-step/quiescence lane unless the missing method paragraph is supplied.
Do not claim the user's inconsistent leaderboard figures are organizer-confirmed without receipts.
Do not replace unavailable measured geology with synthetic fields or invented canaries.
Do not claim a summarized prompt is verbatim. Preserve historical evidence but label retractions.
