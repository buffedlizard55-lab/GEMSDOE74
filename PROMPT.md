# Standing project brief — read before every session

This file records the operational requirements from the project owner's task. The full conversational prompt is preserved in the session history; this is an auditable, actionable brief, not a verbatim transcript.

## Objective and decision principles

- Build a useful, auditable DOE GEMS Prize research and submission workflow for the DrivenData #306 competition.
- Maximize P(Win) and Own the Outcome: prioritize evidence, reproducibility, and honest negative results over producing a superficially impressive file.
- The immediate aim is a unique GeoTIFF with an unambiguous submission name and a ≤140-character note. Do not call a file “OK to submit” until scientific and format gates both pass.
- A separate selector—not the model-building session—chooses whether to spend a weekly submission slot.

## Science and evidence protocol

- Before implementing, list 3–5 distinct geological hypotheses. For each, identify its actual input layer(s), physical signature, why it may detect an unlisted fault rather than reproduce the catalogue, difference from existing code/registry, expected direction of benefit (not a made-up numerical score), and implementation/data cost.
- If needed data are external, identify the specific free official source and confirm availability/provenance before treating it as viable.
- Respect the current session's single-lane assignment. Use the existing cached feature stack/evaluator/writer where available; fix shared tools in place, never make a private evaluator fork.
- The required hide-and-recover design withholds whole fault segments plus buffer; rebuild all catalogue-derived features only from visible segments; mask visible faults pixel-exactly; evaluate pooled distance-weighted Tversky (α=0.2, β=0.8, 300 m triangular kernel).
- Run every feature alone as a leakage canary. AUC >0.90 is leakage until proven otherwise.
- Label scores as `HOLDOUT-DTI` with evaluator version, withheld-positive count, and 95% CI, or `ORGANIZER-CONFIRMED` copied from a competition receipt. Never label a projection as a score.
- Before placement, compute raster rank-correlation and 3-pixel dot overlap against each registry raster. If correlation >0.90 or >70% of dots are within 3 px of a registry raster's dots, log a duplicate and stop.
- Budget: at most 3 experiments or 2 hours. Negative findings are valid deliverables.

## Submission engineering

- The official submission is one single-band GeoTIFF (or ZIP containing one) matching the official sample submission's CRS, shape and geotransform. Read requirements from the official competition materials and validate the actual written bytes against the actual template.
- Every prediction value must be in [0,1]. Avoid negative float32 nodata sentinels; verify NaN/nodata behavior. Don't claim a local format check is an organizer acceptance receipt.
- The site should make the release decision obvious at first view, link the downloadable artifact, and provide a short step-by-step submission guide. When no candidate is cleared, say DO NOT SUBMIT prominently and characterize any download as a review fixture.
- Include a unique submission identifier and short note (≤140 characters).

## Research, sources, and reporting

- Prefer official, free, publicly accessible data and literature. Provide source URLs and distinguish facts verified from the source, in-repo measurements, owner-provided claims, and unknowns.
- Store organized, auditable data provenance and research notes. Do not claim current feeds or live leaderboard status without a dated, reproducible source snapshot.
- Explain any claimed high score from the exact raster, evaluator, and organizer receipt. A leaderboard number is not evidence that a repository-generated file achieved that score.
- List access limitations and blockers explicitly; never ask for secrets in chat.

## Current baseline warning (2026-10-21)

`README.md` and `docs/review/repo-audit-2026-10-21.html` describe the current code review. In brief: competition data are absent; H74-1 is a synthetic research/format fixture; H74-A used sibling-mirror inputs of unverified provenance and an invalid proxy holdout. Neither is a validated competition prediction or cleared for submission. Do not reuse historical holdout score, AUC, or uniqueness values.

## Official starting links

- Problem and metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Rules: https://www.drivendata.org/competitions/306/competition-doe-gems/
- About: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- Competition data (login required): https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- Official reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- NLR report: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- USGS GeoDAWN: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- GDR/INGENIOUS: https://gdr.openei.org/submissions/1391
- CRS: https://epsg.io/32611
