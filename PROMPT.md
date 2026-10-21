# GEMSDOE74 session operating contract — read before each session

This file is the durable project brief distilled from the user's long request. It is a requirements summary, **not a verbatim transcript**. The latest user request and any Arena parallel-run instructions remain authoritative.

## Objective and integrity

- Build an auditable project for the DOE GEMS Prize (DrivenData #306) that can generate a unique, correctly formatted GeoTIFF submission and make its status unmistakable at the top of the site.
- Maximize P(Win), own the outcome, and keep research grounded in official, free, licensed/shareable data. Link primary sources and flag uncertainty. Do not invent input data, scores, receipts, or scientific results.
- A file is **OK to download and submit** only when both scientific and format gates pass. A format-valid file can still be a bad or unproven prediction. Keep review-only artifacts distinct from candidates.
- Review the official problem/rules/data pages, organizer reference solution, relevant USGS/INGENIOUS data, metric, and submission format. Track access limitations and next steps.
- The user's target examples include `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` and score 0.2778; different parts of the request cite 0.3195 and 0.4413 as current leaderboard highs. Verify the live official board and label the capture date. Verify artifact attribution against primary receipts; do not infer a file-score link from a leaderboard row.

## Research and experiment requirements

- Before implementation, list 3–5 candidate hypotheses where the lane permits. Each must name input layer(s), physical signature/transform, why it may reveal faults absent from the USGS/INGENIOUS catalogue, difference from repository methods, expected value/rank and implementation cost. If official external data are needed, name the free official source and verify accessibility in this environment.
- The parallel-run protocol defines one method lane per session. Stay in that lane. Before placement, check rank-correlation and 3-pixel dot overlap against registry rasters; if ρ > 0.90 or >70% of dots are within 3 px of a registry raster, log a duplicate and stop. Repeat on final dots. Never claim a check that was not computed against the actual registry raster.
- Reuse the template's cached feature stack, shared `evaluate_holdout.py`, and shared submission writer. Holdout is hide-and-recover: withhold whole fault segments with a buffer; derive all catalogue-based features from visible faults only; pixel-mask visible faults exactly; score pooled DTI with α=0.2, β=0.8, 300 m triangular kernel. If a shared tool is wrong, fix it in the shared template rather than keeping a private fork.
- Test every feature alone on the holdout before trusting it. AUC >0.90 is a leakage warning until disproved. Missing inputs mean not run—not an assumed pass.
- Budget: at most 3 experiments or 2 hours. Do not spend a weekly submission slot on an idea that has not beaten the current holdout best. Promotion to a real slot is a separate selector decision within the then-current weekly cap.

## Evidence labels and run card

- Every reported score is labelled either **HOLDOUT-DTI** (include evaluator version, withheld-positive count and 95% CI) or **ORGANIZER-CONFIRMED** (copied from the submission-page receipt). Public board values must be separately labelled **PUBLIC-LEADERBOARD**. Projections are never scores.
- End each run with one JSON card containing: hypothesis; mechanism; named non-fault mimic; holdout DTI and CI; correlation/overlap vs registry; raster SHA-256; validator output (no NaN inside footprint, values in [0,1], CRS/shape/transform match); unique submission name and note ≤140 characters; verdict `promote` or `negative`.
- Negative results are deliverables. Never promote a file because it is merely format-valid or distinct.

## Data, site, and verification

- DrivenData competition files require authorized access. Do not use third-party mirrors unless rights are verified. When official files are absent, do not synthesize a GeoTIFF and represent it as a competition prediction. Ask for no credentials in chat.
- Use official sample submission for exact CRS, shape, transform, and outside-bounds mask. Submission must be a single-band float32 GeoTIFF in EPSG:32611, 100 m, matching bounds/shape/transform, values in [0,1]; official page says values outside bounds should be null or NaN. Re-read output bytes and validate.
- Site must put the download and unambiguous release status in the first view and include an executive-summary submission guide, unique short note, audit receipt, and official-source links.
- Keep this brief in README navigation and review it each work session. Run three passes: implement; review and fix; re-check against the complete request. Flag irregularities and state limitations.

## Current lane recorded on 2026-10-21

The current session lane is **C1: flight-line-artifact-suppressed magnetic edge detection** (see `docs/review/session-review-2026-10-21.html`). The official feature stack is absent in this checkout; C1 is therefore **not run**, no TIF is cleared, and no score/CI is available. Do not substitute the inherited synthetic artifacts or their proxy holdouts.
