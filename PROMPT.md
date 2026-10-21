# Full Competition Mandate, Parallel-Run Protocol & Core Values (`GEMSDOE74`)

> **Verification Date:** `2026-10-21` UTC | **Repository:** `buffedlizard55-lab/GEMSDOE74` | **Session Branch:** `arena/ee4946f5-gemsdoe74`

---

## Core Values (Governing Every Technical & Scientific Decision)

1. **Maximize `P(Win)`** — Optimize the real probability of winning the `$300,000` DOE Geothermal Exploration with Machine Learning for Subsurface (GEMS) Prize (`$50,000` Initial Round + `$250,000` Final Round, DrivenData Competition #306). Every line of physics, holdout evaluation, cone spacing, and weekly slot selection exists to discover genuinely unmapped NW Nevada geothermal faults under the exact `DW-Tversky` (`α = 0.2, β = 0.8, R = 300 m`) objective—never to chase self-leaking local proxies or ship synthetic placeholders.
2. **Own the Outcome** — Work autonomously end-to-end with zero excuses: restore SHA-256-verified real competition and open federal datasets (`scripts/restore_data.py`), audit every equation and band index line by line against primary official documentation, purge inherited bugs and fabricated numbers (`IR-74-30`..`IR-74-37`), verify byte-for-byte portal compliance (`[0, 1]`, `0` NaN, `EPSG:32611`, `3730 × 3292`), execute three rigorous verification passes, and deliver a complete, self-contained GitHub Pages site and PR merged cleanly into `main`.

---

## Complete Task Specification & Acceptance Criteria

### 1. Urgent Competition Deliverable: Unique, Portal-Verified `.tif` Submission & Unmistakable GitHub Pages UX
- Generate a **genuinely unique, non-duplicate GeoTIFF submission** (`docs/downloads/gemsdoe74-triregime-radon-piedmont-37654-20261021T051000Z-zeros.tif` + `.zip` + `-nan.tif`) using real NW Nevada GeoDAWN + INGENIOUS + 10 m USGS 3DEP + 1 m LiDAR physical data—never copying any previous submission and never shipping synthetic Perlin arrays.
- Make it **unmistakable in the first fold of `docs/index.html` and in `docs/executive-summary.html`** whether the generated `.tif` is **APPROVED FOR DRIVENDATA SUBMISSION**, providing:
  - One-click `.tif` and `.zip` downloads,
  - Copyable unique **Submission Name** (`GEMSDOE74-TriRegime-Radon-37654`),
  - Copyable **Optional Note (`≤ 140` characters)**: `GEMSDOE74 H74 8-az Radon + PU Piedmont tri-regime: 37654 dots, HOLDOUT-DTI=0.1095, Cpied=0.1177, [0,1] verified` (`111 / 140` chars),
  - Step-by-step DrivenData portal upload instructions and weekly 3-submission budget guidance (`NREL/TP-5700-96647 §3.2`).
- Permanently prevent `"Predicted values must be in range [0, 1]"` by engineering out both root failure modes:
  1. Unmasked float32 `NoData` sentinels (`-3.4028235e+38`, present at `3,061–3,073` *interior* active-footprint pixels in Bands 1, 2, 3, 6, 9, 14 of `training_features.tif` and propagating through convolutions if uninpainted), and
  2. Unsanitized `NaN` / out-of-range values inside the active polygon (`5,167,373` pixels) or outside footprint (`zeros` policy `nodata=None`, exact `[0.0, 1.0]` `float32`, `EPSG:32611`, `3730 × 3292`, `Affine(100, 0, 243350, 0, -100, 4508550)`), re-verified by reading back the written GeoTIFF bytes from disk.

### 2. PhD-Level Forensic Analysis of `0.2778` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`)
- Explain rigorously why `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`0.2778` `ORGANIZER-CONFIRMED`, publicly visible at Rank `#47` on DrivenData as of `2026-10-21`) achieved the highest confirmed group score ahead of `GEMSDOE36` (`0.2750`), `GEMSDOE28` (`0.2710`), `D2.8` (`0.2600`), `GEMSDOE70` (`0.2478`), `GEMSDOE63` (`0.2303`), `GEMSDOE66` (`0.1152`), and `GEMSDOE69` (`0.0053`), while sitting `0.1635` below public `#1` (`0.4413`).
- Prove mathematically from the exact live pair `0.2708 -> 0.2778`:
  1. Why binary dot emission dominates soft continuous rasters (`Theorem 1`),
  2. Why `0..2.15 px` catalogue flanks yield `0.0038` hits/dot vs `0.1351` hits/dot beyond `2 px` (`35.6×` dead-zone efficiency gap),
  3. Why `d = 2.8 px` spacing wastes `22.2%` of kernel diameter (`Theorem 2`: non-cannibalizing cone spacing `d >= 3.8..4.7 px`), and
  4. Why `63-leaf` GBDTs trained naively on `labels.tif` suffer **Positive-Unlabeled (`PU`) negative contamination** against unmapped piedmont/basin faults (`Theorem 3`).

### 3. Five Pre-Registered Geological Hypotheses (`H74-1` through `H74-5`)
- Prior to implementation, formulate and rank 3–5 novel geological hypotheses (`docs/hypotheses.md`), each specifying:
  - Exact input bands / open public Federal layers,
  - Physical edge / lineament / geomorphic transform,
  - Tectonic mechanism explaining why it catches faults missing from pre-GeoDAWN USGS `QFaults` / `INGENIOUS` compilations,
  - Specific non-fault mimics in NW Nevada and quantitative suppression gates,
  - Exact mathematical and implementation differences from all prior runs (`G19`–`G73`).

### 4. Strict PARALLEL-RUN PROTOCOL Compliance
1. **Single Distinct Lane (`GEMSDOE74`):** Check both pre-placement surface Spearman correlation (`≤ 0.90`) and final 3-px dot overlap (`≤ 0.70`) against all `165` rasters across historical + parallel repositories before claiming promotion.
2. **Reuse Shared Tools:** Reuse `vendor/gems57/` (`holdout.py`, `evaluate_holdout.py` `gems57-pooled-hide-v2`, `uniqueness.py`, `submission_writer.py`) unmodified; fix inherited bugs in `src/gemsdoe74/metric.py` (`IR-74-30`) in place with full pytest verification.
3. **Strict Score Labeling:** Every number carries `HOLDOUT-DTI` (with evaluator version, withheld positive pixel count, and 1,000-draw 20-km spatial block bootstrap 95% CI) or `ORGANIZER-CONFIRMED` / `PUBLIC-LEADERBOARD`. Never state a projection as a score.
4. **Leakage Canary:** Compute symmetric single-feature ROC-AUC (`max(AUC, 1 - AUC)`) across every feature on withheld truth (`> 0.90` = leakage until proven otherwise).
5. **Strict Experiment Budget:** Execute exactly `3` nested experiments (`E1` Unsupervised Radon -> `E2` Inner-Hide Continuation `d=2.8` vs `d=3.8` -> `E3` Tri-Regime PU-Radon + Piedmont Calibration) well inside the `2-hour` ceiling (`284.0 s` actual runtime).
6. **Canonical JSON Run Card:** Conclude final report with one self-contained JSON Run Card recording all required fields and SHA-256 digests; keep live weekly slot consumption separate from technical `promote` readiness.

### 5. Three-Pass Audit, Verified Links & Merged GitHub PR
- Pass 1: Implement, execute on real NW Nevada data, verify metrics & GeoTIFF bytes.
- Pass 2: Review assumptions, purge legacy synthetic generators & fabricated scores (`IR-74-30`..`IR-74-37`), polish figures & full HTML site.
- Pass 3: Re-audit every requirement line-by-line, run full automated test suite (`pytest`), push `arena/ee4946f5-gemsdoe74`, open GitHub Pull Request to `main`, and merge cleanly into `main`.
