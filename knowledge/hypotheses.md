# Current hypothesis register — 2026-10-21

> **HOLD.** The current repository lane is H74-1: basement-step ridges gated by surface quiescence. The old implementation used synthetic fields/truth and must not be used as evidence or as a competition predictor. No new candidate has been run or validated in this review.

## Ranked H74-1 research tests

1. **Ridge-location stability across scales** — depth-to-basement plus detrended-elevation slope; retain ridges whose position remains stable under smoothing. Qualitative highest priority, low cost. Mimic: buried paleochannel margin.
2. **Signed step-profile corroboration** — same layers; test for a persistent signed step instead of a symmetric valley. Medium cost. Mimic: asymmetric sedimentary basin margin.
3. **Regional-trend residual** — remove broad basement trend, then require residual ridge plus surface quiescence. Medium cost. Mimic: interpolation seam.
4. **Gridding/nodata perturbation stability** — downweight ridges that migrate under edge/resampling perturbations. Medium cost. Mimic: survey-resolution boundary.

These are qualitative hypotheses, not DTI forecasts. Layer names come from legacy local code and must be checked against official feature metadata before implementation. No external replacement data are proposed; the required official inputs/cache are absent. The official competition data page was checked and redirected to login.

See [`docs/review/session-review-2026-10-21.html`](../docs/review/session-review-2026-10-21.html), [`docs/audit-20261021.html`](../docs/audit-20261021.html), and the current [negative run card](../docs/review/data/run-card.json).

## Gate before any future candidate

- Authorized official `training_features.tif`, labels/fault raster, and `sample_submission.tif`; verified source, hashes, layer names, grid and data-rights provenance.
- Reuse the shared cached feature stack or record and approve any rebuild.
- Whole-segment holdout with spatial buffer, visible-only catalogue feature derivation, exact masking, pooled official DTI, confidence interval, and feature-alone leakage canaries.
- Candidate and incumbent run on identical folds; surface correlation and final-dot proximity checked against the actual complete registry.
- Byte-level validator receipt, exact official footprint/mask, and no unresolved provenance issues.

Until these conditions pass, the run-card verdict remains `negative`; do not spend a weekly submission slot.
