# Current hypothesis register — 2026-10-21

> **HOLD.** Only one method lane is authorized for this session: C1, flight-line-artifact-suppressed magnetic edge detection. The official competition feature stack is not present, so no candidate has been run or validated. The inherited hypotheses and their claimed scores in the previous version of this file were not supported by a valid current holdout and must not be used as evidence or submission guidance.

## C1 lane (qualitative research priorities, not score forecasts)

The ranked variants, specific layers, physical signatures, off-catalogue rationale, non-fault mimics, implementation costs, official sources, and validation gate are maintained in [`docs/review/session-review-2026-10-21.html`](../docs/review/session-review-2026-10-21.html). Do not split into parallel method families or generate submission files from synthetic feature fields.

## Gate before any future candidate

- Authorized official `training_features.tif`, `labels.tif`, and `sample_submission.tif` with hashes and grid metadata.
- Cached features with documented provenance.
- Whole-segment holdout with buffer, visible-only catalogue feature derivation, exact masking, pooled DTI, confidence interval, and feature-alone leakage canaries.
- Candidate and incumbent run on identical folds; duplicate correlation/3-pixel overlap checked against actual registry rasters.
- Byte-level validator receipt and no unresolved data-rights issues.

Until these conditions are met, the run-card verdict is `negative` and no weekly slot should be used.
