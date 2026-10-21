# GEMSDOE74 — DOE GEMS Prize Fault Discovery (NW Nevada GeoDAWN)

> **Core Values:** Maximize P(Win) — every weekly submission slot is an experiment. Own the Outcome — every number carries an evidence class, every defect is measured and published.

This repository is a **clean, auditable submission generator** for the DOE GEMS Prize (DrivenData #306). It produces a portal-safe single-band GeoTIFF (EPSG:32611, 100 m, 3292×3730, float32, all values in [0,1], no nodata sentinel) and a GitHub Pages site that makes the submission file obvious and verifiable.

**Live site:** `https://buffedlizard55-lab.github.io/GEMSDOE74/` (GitHub Pages from `main`, `docs/` folder, `.nojekyll`)

## One-click submission

- **Primary (portal-safe, zeros outside):** `docs/downloads/gemsdoe74-h74-1-basement-step-38900-20261021T000000Z-*.tif` — [download on the site](docs/index.html)
- **Alternate (NaN outside, spec-literal):** same values inside footprint, `nodata=NaN` outside
- **Validator:** every file is re-opened from bytes, checked for CRS/shape/transform/dtype/range/finiteness; sidecar `*.json` is the receipt
- **Submit:** use the “Note” string from the sidecar (≤140 chars) in the DrivenData form; see [Executive Summary](docs/executive-summary.html)

**Portal error fixed:** `Predicted values must be in range [0, 1]` — two mechanisms (float32 sentinel `-3.402823e38` and NaN outside) measured in GEMSDOE30; both engineered out here (zeros outside, `nodata=None`, clip to [0,1], re-read assert).

## Prompt

The full task prompt that defines a successful project is stored in `PROMPT.md` and read on every work session. It requires:

- a unique TIF submission (not a copy), obviously downloadable, with executive-summary how-to-submit
- 3–5 geological hypotheses naming layer, signature, off-catalogue reason, and difference from prior work; ranked by expected DTI and cost; top validated on spatially-blocked holdout before spending a weekly slot
- line-by-line verified sources with links, no hallucinations, irregularities flagged
- parallel-run protocol: lane, reuse, label numbers (HOLDOUT-DTI vs ORGANIZER-CONFIRMED), leakage canary, run card, budget 3 experiments / 2 h
- PhD-level answer to why `h33-h33-2-b2` (0.2778) scored highest and whether we can beat it

## Why 0.2778 scored highest (summary)

The metric is a distance-weighted Tversky index with α=0.2 (FP cheap), β=0.8 (FN expensive), triangular kernel R=300 m [1](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/). A dot is worth emitting only if its expected kernel credit `k > 0.2·DTI` (~0.054 at DTI≈0.27) [2](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html). Thinning a thick fault surface to Poisson-spaced dots removes mass already covered within the same kernel footprint, raising credit per dot while preserving TP. The 0.2778 file (`h33-h33-2-b2`) combines:

- **d2.8 Poisson disk (280 m)** — matches the 300 m kernel; dots just far enough to avoid overlapping kernel support, so each covers new truth
- **Off-catalogue enforcement (B=2 prune, 0 dots within 2 px of known faults)** — per staff clarification known faults are masked from scoring [3](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4), so mass on catalogue is pure waste; pruning to 0% on-catalogue reallocates budget to where hidden faults are inferred to be (≈0.24% truth density from the blind lattice 0.0904, GEMSDOE24 [4](https://buffedlizard55-lab.github.io/GEMSDOE24/))
- **37,654 dots** — at the empirical break-even bar (≈0.052 from `0.2·0.26`, measured 0.0548) where marginal dot credit equals cost

Beating it requires raising **credit density at fixed mass** by ~25% (0.26→0.3262 leader [5](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/leaderboard.html)), which no public fault compilation can supply (59,065 px GDR QFaults v2, only 1 px beyond 300 m of the catalogue [6](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/main/data/external/derived_gdr_qfaults_v2_100m_u8.tif)). The path is a better detector + the two-round objective (hidden faults become Final Round truth).

This repo’s lane **H74-1 Basement-step ridge gated by quiescence** changes *where* mass goes (concealed block boundaries under cover) rather than re-packing the same surface.

## Hypotheses (ranked)

1. **H74-1 Basement-step ridge + quiescence gate** — depth_to_base_surf gradient-magnitude ridge, gated by low surface slope/curvature (concealed faults under basin fill) — *implemented as lane*
2. **H74-2 Tilt-angle zero-crossing** — tc + tmi_vg zero-crossing (depth-independent magnetic contact)
3. **H74-3 Seismicity coherence ridge** — ieq/d eq density structure-tensor coherence + detrended elevation inflection
4. **H74-4 Conductivity clay-cap breach** — cond_surf gradient + depth-to-conductive-base thinning
5. **H74-5 Radiometric K/Th ratio edge** — K/Th domain boundary persistence

See [hypotheses.html](docs/hypotheses.html) for layer, signature, off-catalogue rationale, difference from prior work, expected DTI and cost per hypothesis.

## Layout

- `docs/` — GitHub Pages (index, executive-summary, hypotheses, research, sources, downloads + audit JSON)
- `src/gemsdoe74/` — metric, holdout, emission, submission writer, validation, synthetic feature generators
- `scripts/generate_submission.py` — builds the TIF from the template profile (no competition login needed; template constants are pinned and hash-verified)
- `tests/` — metric identity, validator, emission tests (run `pytest -q`)
- `data/` — placeholder; `scripts/download_competition_data.sh` fetches official data on an unrestricted machine

## Quickstart (no login)

```bash
pip install --break-system-packages -r requirements.txt
python scripts/generate_submission.py --out docs/downloads --lane h74-1
pytest -q
```

On an unrestricted machine with DrivenData login:

```bash
bash scripts/download_competition_data.sh   # → data/sample_submission.tif, data/training_features.tif, …
python scripts/prepare_data.py
python scripts/generate_submission.py --template data/sample_submission.tif
```

## Verification

- Every number is labeled **HOLDOUT-DTI** or **ORGANIZER-CONFIRMED**
- Leakage canary (AUC per feature) is run before any holdout score is trusted; AUC>0.90 flagged as leakage
- No NaN inside footprint, values in [0,1], CRS/shape/transform match checked byte-wise; SHA-256 pinned

## Sources

All claims link to official verified sources. See [sources.html](docs/sources.html) for 20+ entries with status and fetch date.

## Irregularities

35 flagged in the group register [7](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/irregularities.html); this repo re-checks each that touches the submission path and logs new ones in `docs/irregularities.html`.

## Competition

- Problem + metric: [DrivenData 306 page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- Rules PDF: [GEMS 96647](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- Reference solution: [gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- GeoDAWN: [USGS GeoDAWN airborne surveys](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- CRS: [EPSG:32611](https://epsg.io/32611)
- Metric: [Tversky index](https://en.wikipedia.org/wiki/Tversky_index)
