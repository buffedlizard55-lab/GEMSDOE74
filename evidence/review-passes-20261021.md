# Three-pass review, 2026-10-21

## Pass 1 — implementation / integrity triage
Read README, task record, generation code, both evaluator families, writers and tests.
Found synthetic geology/truth and fabricated canary/registry metrics. Disabled the generator,
retracted its run card, preserved the owner-mirror evidence with provenance caveats, and
published clear HOLD downloads. No experiment or competition submission was performed.

## Pass 2 — bugs and edge cases
A historical owner-mirror audit reported 20,013 H74-1 positive cells outside that mirror's footprint; the mirror is not organizer-authenticated and is absent from this checkout, so this was not a verified official-template check. Replaced false-success preparation, guarded canary inputs, and corrected soft-probability binarization. Added regression tests and reduced the note limit to project protocol. Historical holdout results remain invalid for promotion; no replacement score was invented.

## Pass 3 — request compliance and reproducibility
Found the earlier validator could assert outside-footprint compliance without an authenticated template. Replaced it with template-aware checks that report footprint/alignment as unavailable when the official template is absent. The candidate writers now require an actual template and emit NaN outside its finite footprint, as the official problem page specifies. Disabled both noncompliant evaluation CLIs, marked synthetic band mapping as unverified, and installed CI. Site rebuild is deterministic; historical pages carry a retraction notice.

Initial review-pass test counts are superseded by the post-merge verification below. The current full local suite is 113 passed, 4 third-party Rasterio deprecation warnings. These are software test counts, NOT HOLDOUT-DTI or organizer performance scores.

Incomplete requirements: new genuine TIFF; shared cache restoration; complete registry
checks; compliant buffered evaluation; current official leaderboard and cap; external-data
rights; full cross-repository analysis; verbatim prompt archival. The site and README state
these explicitly. The negative run card is the scientific deliverable, not a promotion.

## Post-merge follow-up — H74-1v2 receipt/sidecar correction
The main-branch H74-1v2 addition carried a local `READY` receipt and HOLDOUT-DTI/AUC/registry values derived from a synthetic prediction field, synthetic hidden truth and noncompliant quadrant folds. The local receipt and run card are now explicitly negative; unavailable scores, confidence intervals, withheld-positive counts, leakage, and uniqueness fields are null. The two TIFF sidecars now distinguish measured local file-format metadata from unverified owner-mirror footprint/catalogue claims. The zeros TIFF passes only basic local checks against pinned constants; the NaN TIFF has finite [0,1] values where present but its exact outside-bounds alignment is unknown. An earlier whole-array-finite validator assumption has been superseded after checking the organizer's null/NaN outside-bounds requirement. No organizer format acceptance is asserted. `generate_h74v2.py` now fails closed, and regression tests cover the status and generator guard.
