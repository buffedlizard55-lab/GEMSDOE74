# GEMSDOE74 — DOE GEMS Prize review and submission pipeline

> **Read `PROMPT.md` before every project session.** Core values: **Maximize P(Win)** by preserving experimental slots for evidence-backed candidates; **Own the Outcome** by publishing defects and refusing unsupported release claims.

## Status: HOLD — no submission is cleared

There is currently **no scientifically validated, competition-ready TIF in this repository**. Do **not** submit any downloadable file from this site. The GeoTIFFs under `docs/downloads/` are inherited review artifacts, not an approved candidate: the feature inputs and footprint were synthesized or mirrored without verified provenance, and the available holdouts do not establish discovery of faults absent from the catalogue. Format validity is not scientific validation.

The current session's only allowed method lane is **C1: flight-line-artifact-suppressed magnetic edge detection**. It has **not** been run. The official competition feature stack, sample submission, labels and cached feature stack are not present under `data/`; this environment has no DrivenData login. Therefore no legitimate new raster can be built, no holdout score or confidence interval can be reported, and no submission slot should be spent. Details, ranked variants, source links, and irregularities are in [the session review](docs/review/session-review-2026-10-21.html) and [run card](docs/review/run-card.html).

### Existing files are review-only

The TIFs in [`docs/downloads/`](docs/downloads/) were generated in earlier parallel work. They are retained for audit and reproducibility, **not as submissions**. Their sidecars assert format properties; they do not prove inputs, provenance, geospatial footprint, official acceptance, or a valid novelty holdout. The review page links to them only as historical artifacts.

## Why the reported 0.2778 is not explained by available evidence

The public leaderboard page reports public DW-Tversky scores; a leaderboard row does not identify a GeoTIFF by filename or hash. The public leaderboard row 0.2778 (**PUBLIC-LEADERBOARD**) is associated with participant `extradr19`, not verifiably with the GEMSDOE32 artifact. GEMSDOE32's own page describes its H33-2-B2 as a 0.2708 base pruned of dots within 2 pixels of known faults, leaving 37,654 dots; it reports an internal live-mirror uplift of 0.00487 and projected 0.2747, while explicitly saying there is no organizer score. Treat those as **SIBLING-REPO CLAIM / PROJECTION**, not an organizer result. The repository contains no organizer receipt that ties that file hash to the public leaderboard's 0.2778. Accordingly, **why that exact file scored 0.2778 cannot be established here**.

The official metric makes sparse, well-located predictions a plausible strategy: the distance-weighted Tversky index uses α=0.2, β=0.8 and a 300 m triangular kernel. Pruning low expected-credit predictions may reduce false-positive mass, but this is a mechanism-based hypothesis, not a causal explanation or a measured score for the named file. The current official public page fetched on 2026-10-21 shows 0.4413 at rank 1 (**PUBLIC-LEADERBOARD**); this differs from the user's cited 0.3195 and should be rechecked later because the board changes. That leaderboard number is not evidence that this project can beat it.

Official references: [problem description, metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/rules/), [official GeoDAWN data page](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [INGENIOUS](https://gbcge.org/current-projects/ingenious/), [EPSG:32611](https://epsg.io/32611).

## Safe workflow

1. Read `PROMPT.md` and the session review. Do not spend a slot on an unvalidated idea.
2. On an authorized machine, download the official competition files from the [DrivenData data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) into `data/`. Respect competition rules and input-license terms; do not use an unverified mirror.
3. Run `python scripts/prepare_data.py`, then build and cache the verified feature stack. The current generation command intentionally fails closed: its synthetic feature code is not a competition model.
4. Implement and test C1 using only the cached stack; withhold whole fault segments plus buffer, derive catalogue-based features only from visible faults, pixel-mask visible faults, run per-feature leakage canaries, and compare candidate with incumbent and controls under the same evaluator.
5. Record pooled HOLDOUT-DTI, evaluator version, withheld-positive count, and confidence interval. Stop on duplicate thresholds or leakage. Promotion to a real slot is a separate selector decision.
6. Only after all scientific, provenance, uniqueness and byte-level format gates pass, write a submission with `src/gemsdoe74/submission.py`, re-open/validate it, hash it, and publish a receipt. The site must say plainly **OK to submit** or **DO NOT SUBMIT**.

The official submission format is one float32 GeoTIFF in EPSG:32611, 100 m, same bounds/shape/transform as the competition data, one band, and values in [0,1]; the official problem description says values outside bounds should be null or NaN. Use the official sample submission for geometry and null mask. Do not infer the official footprint from a synthetic mask. A zeros-outside raster may satisfy a portal range validator but can violate the stated outside-bounds requirement; verify the organizer's validator behavior rather than assuming.

## Repository map

- `PROMPT.md` — session operating contract, including the parallel-run protocol.
- `docs/` — GitHub Pages, review, evidence, and legacy downloads.
- `docs/review/session-review-2026-10-21.html` — current, evidence-based status and research slate.
- `docs/review/data/run-card.json` — current negative run card; no score is fabricated.
- `src/gemsdoe74/submission.py` — GeoTIFF writer/validator helper; its pinned constants are not a substitute for the official template.
- `scripts/generate_submission.py` — fails closed until official input data and a real model are implemented.
- `scripts/evaluate_holdout.py` — fails closed rather than reporting the old random-pixel proxy as segment holdout.
- `data/` — intentionally empty in this checkout (except README and `.gitkeep`).

## Verification

Run `pytest -q`. Tests that require competition inputs must be reported as **skipped**, not silently passed. No organizer-confirmed result exists for any artifact here. Report public leaderboard values as **PUBLIC-LEADERBOARD**, local holdout values as **HOLDOUT-DTI (evaluator version, withheld positives, 95% CI)**, and copied submission receipts as **ORGANIZER-CONFIRMED**. Never present a projection as a score.
