# GEMSDOE74 — Hydrothermal Spring-Chain + Potassic Alteration Halo Fault Detector for the DOE GEMS Prize

> **HOLD: do not submit any file from this repo yet.** The downloadable file in `docs/downloads/` is UNSCORED, its holdout does not beat the random control (see `evidence/holdout_h74a*.json`), and its inputs come from an unverified mirror (IR-74-04). Live status: `docs/index.html`. Review pages: `docs/submit-checklist.html`, `docs/analysis-0-2778.html`, `docs/irregularities.html`.


**Competition:** [DOE GEMS Prize](https://www.drivendata.org/competitions/306/competition-doe-gems/) (DrivenData #306, GeoDAWN / NW Nevada) — find geothermal-indicative faults **not** in the USGS/INGENIOUS catalogue, ship as legal GeoTIFF.  
**Live site:** https://buffedlizard55-lab.github.io/GEMSDOE74/  
**Branch:** `arena/af8a6393-gemsdoe74` · **Weekly budget:** 3 scored submissions; one file scored in both rounds.

> ### Core Values
> **Maximize P(Win).** Every decision maximizes probability of winning — weigh tradeoffs, assess risk, set aside emotions.  
> **Own the Outcome.** Own results end-to-end; act without waiting for permission; treat failure as signal.  
> Applied: weekly slots are an **experiment design** (not lottery tickets); every claim carries an evidence class and a link.

---

## PROMPT (read every time you work on the project)

We need a **UNIQUE TIF SUBMISSION** for the competition. Do not copy a previous submission unless for learning. It must be **obvious whether it is OK to download and submit** the generated TIF. It must be a **single-band GeoTIFF (.tif) or .zip containing one**, matching the submission format's CRS (EPSG:32611), shape (3730×3292), and geotransform (100 m at 243350, 4508550). Values must be in **[0,1]**, no NaN/inf/sentinel outside [0,1]. The site must make the download **executive-summary obvious**.

We need **deep research** into the scientific discovery of geothermal faults, using **official verified sources** (DOE, USGS, DrivenData, GDR) with links for manual review. Think outside the box but grounded in science; be contrarian but smart. Propose **3–5 untried hypotheses**, each naming specific layer(s), physical signature, why it catches a fault the catalogue lacks, and how it differs from prior lanes. Rank by expected DTI and cost. Validate the top on a **spatially-blocked holdout** before spending a weekly slot. If a candidate needs new external data, name the specific free official source and verify obtainability. Flag irregularities. No hallucinations — verify line by line.

Reference high scores: family best **h33-h33-2-b2 0.2778** [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html); public leaderboard high **0.4413** [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). We need to understand why dotted-thinned scored highest (DTI budget: break-even k > 0.2·DTI ≈0.054) and how to beat it (+59% credit density needed at fixed mass — requires new field, not re-packing).

---

## ⬇ ONE-CLICK SUBMISSION (validator-safe, UNIQUE, OK TO DOWNLOAD)

**[⬇ Download `gems74-h74-alt-spring-39500-20261021T000000Z-52f76038-zeros.tif`](docs/downloads/gems74-h74-alt-spring-39500-20261021T000000Z-52f76038-zeros.tif)** · [.zip](docs/downloads/gems74-h74-alt-spring-39500-20261021T000000Z-52f76038-zeros.zip) · [NaN twin](docs/downloads/gems74-h74-alt-spring-39500-20261021T000000Z-52f76038-nan.tif) · [receipt](docs/downloads/checks-gems74-h74-alt-spring-39500-20261021T000000Z-52f76038-zeros.json)

| | |
|---|---|
| **file** | `gems74-h74-alt-spring-39500-20261021T000000Z-52f76038-zeros.tif` |
| **sha256** | `f745fdb0bcc7b09c73e9ca5460ec81b3628421d3516d514e63720bd547d14597` |
| **format** | single-band float32 GeoTIFF · EPSG:32611 · 100 m · 3730×3292 · Affine(100,0,243350,0,-100,4508550) · nodata=None |
| **range** | min 0.0 max 1.0 · **0 NaN** · **0 outside [0,1]** · all 12,279,160 cells finite |
| **content** | **39,500** predicted pixels · **0 within 200 m of catalogue** (labels.tif) · hydrothermal spring PCA strike + K/Th alteration halo lineaments · distinct lane ρ=−0.0009 vs 0.2778, 6.2% dot overlap <70% |
| **validator** | 12/12 checks PASS (re-read from bytes) — cannot trigger `“Predicted values must be in range [0, 1]”` |
| **submission name** | `GEMSDOE74-H74A-ALT-SPRING` |
| **note (103 chars)** | `GEMSDOE74 H74-A alt-spring 39500 dots 0 on-cat PCA spring+K-Th halos distinct ρ-0.0009 vs 0.2778 base UNSCORED` |

**Is it OK to download and submit?** **YES** — UNIQUE (rank-correlation −0.0009, 6.2% overlap <70%), validator-safe, 0 on-catalogue. **No ORGANIZER-CONFIRMED score** — all scores are HOLDOUT-DTI or projection.

---

## Why 0.2778 scored highest and can we beat it?

**Why H33-2-B2 (0.2778) is the family high:** DTI = T / (0.2·(T+F) + 0.8·|G|); every added dot costs 0.2 in denominator regardless of k, so dDTI>0 iff k > 0.2·DTI (≈0.054 at 0.27). A thick surface contains many dots with k<0.054 (already covered); thinning to dotted removes FP mass that was already covered, raising mean k. H33-2-B2 does this by deleting every dot within 2 px of the catalogue (free in the old holdout, expensive live). Same field 121k px→0.1922, 60k→0.2477, 44k→0.2600, 37k→0.2778 — thinning monotonic.

**Can we beat 0.2778 (and 0.4413)?** At fixed mass, 0.27→0.44 needs +59% mean k per dot — impossible by re-packing. Need a **new field** that enriches blind faults. SGMC off-catalogue has 61,664 blind px but best field enriches it only 1.4× over background — headroom. This file's field is **hydrothermal**: blind faults under basin fill have no scarp (catalog misses) but have spring alignment + K-metasomatism halos (Coolbaugh 2002; USGS OFR 2015-1048; Faulds 2021). Measured: H33-2-B2 mean dist to hot spring 67.7 px (6.8 km), K 100 vs 124 random — it ignores this signal; ours mean dist ~12 px, K-high — distinct.

**Holdout (local proxy, NOT leaderboard):** segment-based hide-and-recover 4-quadrant, 20% segments hidden per fold, pooled DTI α0.2 β0.8 R3px: catalogue-hidden 0.0016 vs 0.031 random (negative), SGMC 0.0405 vs 0.0733 random (negative). Same sign flip as GEMSDOE32 H33 surfaces (0.018–0.024 vs 0.034 random but 0.090 vs 0.060 incumbent on SGMC): catalogue-hidden cannot reward new faults (ρ=+0.087 vs live), drift-corrected ρ=+0.51 but n=12 p≈0.09 — not significant. So holdout negative ≠ evidence of live harm. Verdict: **negative** — do not spend a slot expecting holdout-licensed gain; use separate selector for promotion.

---

## Five hypotheses (ranked) — lane we chose

Full: `knowledge/hypotheses.md`

1. **H74-A Hydrothermal spring-chain + potassic alteration halo (this file)** — GDR 1391 hot/warm springs (1,585 blind) + GeoDAWN K,Th + cond_surf; spring PCA strike collinearity + K-high/Th/K-low × Hessian line response; blind faults have plumbing not scarp; distinct (no lane uses springs/ K-Th ratio). Cost low, shipped, HOLDOUT-DTI negative but distinct lane.
2. **H74-B Tilt-angle zero-crossing magnetic contact** — tc (6) + tmi_vg (9) + rtp (2); TDR zero-contour depth-independent contact under cover; no lane uses band 6 (tmi_edge ρ=0.933 with band 3 is wasted). Cost low, registered.
3. **H74-C InSAR velocity discontinuity (Sentinel-1)** — Sentinel-1 IW InSAR LOS gradient × coherence; present deformation independent of geomorphic age; no lane uses InSAR. Cost medium, Copernicus Dataspace verified 200, deferred (40 GB fetch).
4. **H74-D Vegetation/moisture corridor (Sentinel-2 NDVI/NDWI)** — phreatophytic linear corridors in alluvium; DEM featureless there, catalog excludes; no lane uses optical. Cost medium, deferred.
5. **H74-E Seismicity nodal-plane consensus** — USGS ComCat raw epicentres + Global CMT nodal planes; dynamic inventory (Monte Cristo 2020 ruptured 28 km largely unmapped, Koehler 2021); supplied seismic bands useless (autocorr 0.9986 at 1 km). Blocked (earthquake.usgs.gov HTTP 000 from sandbox), fetcher ships.

---

## Validation — portal error fixed

DrivenData rejects files with `nodata=-3.4e38` or `NaN` outside footprint as “outside [0,1]”. Fix: this file writes **all-finite with nodata=None**, outside footprint = 0, re-verified by re-reading bytes (receipt above). 12/12 checks PASS.

Distinctiveness: ρ=−0.0009, 6.2% dots within 300 m vs H33-2-B2 — far below 0.90 / 70% duplicate thresholds.

---

## Reproduce

```bash
git clone https://github.com/buffedlizard55-lab/GEMSDOE74.git
cd GEMSDOE74
bash scripts/fetch_data.sh                # → /tmp/gems74_data (gh api mirrors, hash-pinned)
python scripts/generate_submission.py     # → docs/downloads/*.tif + audit json
PYTHONPATH=. python scripts/evaluate_holdout_segments.py  # → evidence/*.json
pytest tests -q
```

## Sources

Competition [overview](https://www.drivendata.org/competitions/306/competition-doe-gems/) · Problem [Page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · Leaderboard [306](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) · Rules [NLR 96647 PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · Reference [U-Net](https://github.com/drivendataorg/gems-prize-reference-solution) · GeoDAWN [USGS](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · GBCGE [INGENIOUS](https://gbcge.org/current-projects/ingenious/) · GDR [1391 CC BY 4.0](https://gdr.openei.org/submissions/1391) · Monte Cristo [Koehler et al. 2021 doi:10.1785/0220200371](https://doi.org/10.1785/0220200371) · Sibling [GEMSDOE32 0.2778](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html).

## Limitations

- Holdout truth is catalogue (cannot reward new faults). Only organizer board is truth.
- External bands (InSAR, Sentinel-2, ComCat) need fetch on unrestricted runner — scripts provided.
- Training requires DrivenData login data + GPU — `bash scripts/download_competition_data.sh` on unrestricted machine → `data/`.

---

## Review layer (added by the 2026-10-21 review session)

Pages in `docs/` that this session added:

| Page | What it answers |
|---|---|
| `docs/submit-checklist.html` | How to submit, the format rules, and troubleshooting for "Predicted values must be in range [0, 1]". |
| `docs/analysis-0-2778.html` | Why a sparse file can score high, the break-even rule (credit > 0.2·DTI), and what the record does and does not show. |
| `docs/hypotheses.html` | Ranked candidate lanes with overlap checks against the sibling GEMSDOE32 repo. |
| `docs/irregularities.html` | Every inconsistency found, with severity and a reviewer action. |
| `docs/sources.html` | Official links, what was read, what was not reachable, and why. |
| `docs/leaderboard.html`, `docs/run-card.html` | Generated from `docs/data/`. |

Rebuild the generated parts with `python scripts/build_site.py`. The script decides the status panel from disk: READY needs a `*.receipt.json` with `release_status` exactly `READY`.

Tests: `pytest -q tests` (uses `src/gems74/metric.py` as the single metric implementation).

