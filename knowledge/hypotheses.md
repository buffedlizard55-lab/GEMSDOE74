# GEMSDOE74 research backlog — H74-A only

**Reconciled:** 2026-10-21 after merging current `origin/main` into the active Arena branch.
**Status:** BLOCKED — no new candidate, compliant holdout, or organizer-confirmed score.
**Selected lane from upstream project context:** H74-A, hydrothermal spring chains plus potassic K/Th alteration halos.

This file replaces an incoming owner-generated shortlist whose headline claims were not supported by the checked-in evidence on this merge. The incoming note claimed a positive drift-corrected H74-A result and a leaderboard high, while the current evidence files record negative H74-A proxy results and no organizer receipt. Those claims are not carried forward as facts. No external competition, USGS, NLR, NASA, or GDR page was fetched in this session; the trusted links at the end are for manual review.

## Existing H74-A artifact: archive only

The upstream mainline contains an experimental zero-mode raster, its NaN twin, ZIP, format receipt, and build metadata. They were moved unchanged from `docs/downloads/` to `archive/h74-a/` so the static site no longer exposes them as submission downloads. The current build record is `registry/submission_build.json`; historical evidence is in `evidence/holdout_h74a.json` and `evidence/holdout_h74a_segments.json`.

The strongest available proxy record is **HOLDOUT-DTI v0.2-segment-proxy**: candidate `0.0016193636` versus random control `0.0310343546`, with **12,088 withheld positives** and **no 95% CI**. It has no buffer and did not rebuild catalogue-derived features from each fold's visible faults. It is negative, noncompliant, and not a valid current holdout best. The earlier v0.1 pixel proxy is also invalid. The format receipt only concerns GeoTIFF checks. There is no organizer-confirmed submission-page receipt or score.

The historical H74-A generator reads `dist_known_fault_px` from its spring table, which is catalogue-derived. It is not fold-visible-only and must not be used as a compliant holdout builder until this feature is recomputed from each fold's visible fault mask. This branch generated no TIF.

## Ranked H74-A hypotheses (qualitative, not score projections)

All four items below remain within the selected lane. They rank expected potential and implementation cost; none is a numerical DTI claim.

| Rank | Hypothesis | Expected DTI potential | Cost | Main risk / gate |
|---|---|---|---|---|
| 1 | **Fold-visible spring-chain geometry.** Recompute spring-to-fault distance and chain/orientation from the visible catalogue for each spatial fold; do not use the historical full-catalogue distance column. | Highest of these tests, very uncertain. | High: refactor the shared generator, verify GDR fields, preregister parameters, run repeated buffered folds. | Sampling density, roads, survey bias, non-fault geothermal discharge, regional hydrology. Test against a valid current holdout best first. |
| 2 | **Spring–K/Th consensus rather than a union.** Require an independently defined spring-chain response to coincide with documented K/Th alteration lineaments under a preregistered scale rule. | Medium-high if rank 1 contributes signal. | Medium. | Lithologic contacts, radiometric artifacts, chance coincidence. Run one-feature canaries and paired holdout ablations. |
| 3 | **K/Th alteration lineaments alone.** Verify GeoDawn band identity/units and test an alteration-contrast edge independently of spring locations. | Medium-low. | Medium. | Lithology, cover, flight-line artifacts, quantized/stretched values. Do not imply calibrated chemistry from undocumented bands. |
| 4 | **Hot-only or quality-weighted spring chains.** Compare a preregistered thermal-class/temperature subset with the existing hot-plus-warm idea. | Low-to-medium. | Low after rank 1's builder; otherwise medium. | Season, instrument, field definition, and survey practice. Do not tune thresholds on the holdout. |

## Required next steps

1. Obtain the authorized competition inputs and cached feature stack; verify source, licence, hashes, and alignment to the official sample grid. The pinned mirror is partial, not official provenance, and was not run.
2. Repair the shared H74-A builder so every catalogue-derived feature uses only the fold-visible fault mask. No private fork or second submission writer.
3. Establish a valid current holdout-best baseline. The archived H74-A proxy is not that baseline.
4. Evaluate rank 1 first with whole-segment four-quadrant folds, a 1.5 km feature-construction collar, exact visible-fault masking, pooled DTI (`alpha=0.2`, `beta=0.8`, triangular `300 m` kernel), repeated draws, and an empirical 95% interval. Run every feature alone; AUC above 0.90 is leakage until explained.
5. Compare the surface before placement and final dots against all registry rasters. Stop at rank correlation `>0.90` or dot overlap `>70%` within `3 px`.
6. Stop after at most three experiments or two hours. Only a candidate that beats the valid holdout best can reach the separate weekly-slot selector. This session selected/promoted nothing.

## Trusted manual-review links

- [USGS GeoDawn magnetic and radiometric survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [GDR submission 1391](https://gdr.openei.org/submissions/1391)
- [Official GEMS competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)

The official sites above were not accessible to this session and their coverage/availability is unverified. A projection is never a score. Report only `HOLDOUT-DTI` with evaluator version, withheld-positive count, and 95% CI, or `ORGANIZER-CONFIRMED` with the actual submission-page receipt.
