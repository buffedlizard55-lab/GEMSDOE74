# GEMSDOE74 Pre-Registered Geological & Geostatistical Hypotheses

**Pre-registration timestamp:** `2026-10-21T02:35:00Z` (written **before** fitting any candidate model on `GEMSDOE74`).  
**Evaluation protocol:** Shared `vendor.gems57.evaluate_holdout` (`VERSION = "gems57-pooled-hide-v2"`), 4 spatially blocked quadrants (`seed=20`, `buffer_px=20` = 2 km, `mask_radius_px=2`, `11,321` withheld positive pixels), official Distance-Weighted Tversky Index ($\alpha = 0.2$, $\beta = 0.8$, $R = 300\text{ m} = 3\text{ px}$ triangular kernel $k(d) = \max(1 - d/R, 0)$), 1,000 paired physical 20 km spatial-cluster bootstrap draws.

---

## Forensic Summary: Why `h33` Scored `0.2778` (ORGANIZER-CONFIRMED) & Why Top Teams Score `0.3539–0.4413`

1. **Why `GEMSDOE32` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`) reached `0.2778` (`ORGANIZER-CONFIRMED`):**
   - `h33` applied multi-scale second-derivative Hessian ridge extraction across 7 physical channels plus **cross-strike directional non-maximum suppression (crest sharpening)** to emit a clean 1-pixel ridge network (`38,113` pixels). On the `gems57-pooled-hide-v2` holdout (`n_withheld = 11,321`), `h33` achieves **HOLDOUT-DTI = `0.3016` (`95% CI [0.2712, 0.3316]`)**, closely tracking its `ORGANIZER-CONFIRMED` score (`0.2778`).
   - In contrast, `GEMSDOE70` (`p8`, `ORGANIZER-CONFIRMED = 0.2478`, **HOLDOUT-DTI = `0.2896`, `95% CI [0.2587, 0.3193]`**) suffered from four concrete defects discovered line-by-line: (i) full-raster negative sampling poisoned trees with false negatives from unmapped GeoDAWN chunks and `100–300 m` QFault registration offsets; (ii) `binary_erosion(valid, iterations=12)` zeroed `177,792` valid pixels along footprint edges and internal `Band 2 (rtp)` NaN holes; (iii) `X[:, :38]` dropped fold-visible Coulomb relay features in columns `38..40`; and (iv) geometric rank fusion (`r_neo^0.55 * r_uns^0.20 * r_bed^0.25`) gave 25% weight to pre-Quaternary SGMC bedrock faults.
2. **Why top DrivenData entries (`0.3539–0.4413` `ORGANIZER-CONFIRMED`) beat pixel-wise ridges (`0.2778`):**
   - Both the official DrivenData U-Net benchmark (`unet-mc-cv-reference-solution.ipynb`, Lipor 2026) and the companion USGS/Stanford study on this exact dataset (`Hermant et al., 2025`, Stanford Geothermal Workshop SGP-TR-229) establish that **unmapped GeoDAWN chunks contain dense unlabelled Quaternary faults** (`operator mapping bias`). Filtering training tiles strictly to **mapped reference `128×128` tiles (`12.8 × 12.8 km`) containing $\ge 1$ visible fault pixel**, masking the `1..3 px` (`100–300 m`) registration collar around mapped traces, and training a **multi-scale 2D convolutional encoder-decoder directly under differentiable DW-Tversky loss ($\alpha=0.2, \beta=0.8$)** captures **multi-kilometer lateral continuity (`~6.8 km` receptive field)** while eliminating false-negative label poisoning.

---

## Five Pre-Registered Untried Geological Hypotheses (Ranked by Expected Holdout-DTI Gain / Compute Cost)

### Rank 1 — `H74-1` (**Committed Lane for `GEMSDOE74`**, `Exp 1 → Exp 2 → Exp 3`):
**Positive-Tile PU-Deconfounded Multi-Scale 2D Convolutional & Fluvial-Neotectonic Synthesis Directly Optimizing Differentiable 300 m DW-Tversky Loss (`PU-ResUNet-DiffDTI + CrestSubmod300`)**
- **Specific layers used:**
  1. Official 19-band `gems-geodawn-numerical-features.tif` (verified via embedded GDAL band descriptions: GeoDAWN `mag_anom`, `rtp`, `tmi`, `tmi_hg`, `tmi_vg`, magnetic `tc` tilt/curvature + INGENIOUS `iso_grav_anom`, `iso_grav_anom_hg`, `iso_grav_anom_vg`, `iso_grav_anom_slope`, GPS `geod_2ndinv` / `geod_shearrate` / `geod_dilaterate`, microseismic proximity/density `deq_n100a15` & `ieq_n100a15`, `depth_to_base_surf`, MT `cond_surf`, `det_elev`, `det_elev_slope`) — **zero `existing_faults` input channels (`0%` `d_vis` / `d_tip`) so holdout gains transfer directly to unmapped GeoDAWN chunks**.
  2. USGS 3DEP 10 m DEM (`dem10` 13 float32 layers: `dem10_piedmont`, `dem10_onesided`, `dem10_ridge_ multi`, `dem10_aniso`, `dem10_log_area`) **PLUS** native 10 m 3DEP drainage-divide / fluvial tectonic disequilibrium (`dem10_chi_100m_i16.tif`: `step_max`, `step_min`, `ksn_max` normalized channel steepness $m^{0.9}$, `log10_area_m2`, `zmean_m`).
  3. USGS 3DEP 1 m LiDAR scarp morphology (`lidar_scarp_features_u8.tif`: directional step height, scarp anisotropy, 1 m slope) + EarthMRI 1 m topographic openness/LRM (`dem1m_high_prior_openness_lrm.npz`).
  4. USGS GeoDAWN gamma-ray spectrometry (`geodawn_rad_u8.tif`: `K`, `Th`, `U`, `TC`) + `150 m` upward-continued magnetic extensions (`geodawn_extensions_u8.tif`).
  5. DOE GDR `#1391` hydrothermal upflow indicators (`gdr_wellspring_in_footprint.csv` thermal springs/wells — excluding `dist_known_fault_px` column — plus `derived_gdr_2m_probes_100m_u8.tif` 2 m temperature probes, `gdr_volcanic_vents_in_footprint.csv` vents, and `derived_gdr_paleo_100m_u8.tif` sinter/travertine/tufa) + US Census TIGER road distance (`tiger_road_distance_m.tif`). Strictly **zero `d_vis` / `d_tip` catalogue-continuation features** are fed to either learner so predictions generalize identically across partially mapped quadrangles and completely unmapped GeoDAWN chunks (e.g., Beowawe Geysers Malpais fault scarp at `dist_known_fault_px = 61.72`).
- **Physical signature & transform:**
  - Active geothermal-hosting Basin-and-Range / Walker Lane normal and transtensional faults juxtapose uplifted footwall blocks (steep channel steepness $k_{sn}$, low upstream drainage area $\log_{10} A$ across triangular facets, high one-sided step height `dem10_onesided`) against subsiding hanging-wall basins (gravity horizontal-gradient maximum `iso_grav_anom_hg`, shallow magnetic vertical/horizontal gradient ridge `tmi_hg`/`tmi_vg`, MT conductive clay cap `cond_surf`, K/Th hydrothermal alteration, and thermal springs/sinter).
  - By training on **mapped reference `128×128` tiles only** with a **`1..3 px` registration-collar ignore zone** around `fold['visible']` and **exact differentiable `300 m` kernel `DifferentiableDTILoss(alpha=0.2, beta=0.8)`** + $D_4$ dihedral test-time equivariance, a 2D multi-scale ResUNet learns multi-kilometer linear scarp-and-geophysical continuity rather than isolated pixel amplitudes, which is then fused in calibrated log-odds space with a de-regionalized PU multi-physics gradient booster, sharpened across local structure-tensor strike, and emitted via exact unblurred `300 m` lazy-greedy submodular coverage.
- **Why it catches unmapped faults:** Unmapped GeoDAWN chunks in `existing_faults.tif` were skipped because of quad-by-quad human mapping scope rather than absence of scarps (`Hermant et al., 2025`). Positive-tile PU training learns the true physical posterior $P(\text{fault} \mid X_{\text{2D patch}}, \text{mapped}=1)$ and applies it uniformly to unmapped basins, full footprint edges, and `rtp`-gap zones without SGMC bedrock bias.
- **Specific non-fault mimics countered:**
  1. *Lake Lahontan / Pleistocene pluvial paleo-shorelines & beach bars (`~1,330 m` Sehoo highstand):* form closed constant-elevation contours (`|\nabla zmean_m| -> 0` along trace) with zero cross-divide channel steepness jump (`ksn_max` flat) and zero gravity/magnetic basement offset; 2D `128×128` context + elevation-contour alignment explicitly separates closed lacustrine contours from range-bounding scarps.
  2. *Incised fluvial gorges & alluvial fan channels:* have high upstream drainage area (`log10_area_m2` high) and V-shaped symmetric valley walls (`dem10_onesided` low vs `slope` high), whereas tectonic piedmont scarps cut across low-drainage interfluves (`tect_vs_fluvial = piedmont - 0.5 * log10_area`).
  3. *Interstate/railroad embankments (`I-80`, `US-50`, `US-95`) & canal berms:* de-confounded via `tiger_road_distance_m.tif` without zeroing genuine range-front highways where deep gravity/magnetic basement steps confirm real tectonic structure.
- **Differentiation from all `251` prior registry rasters (`GEMSDOE01..73`):** Zero prior runs trained a multi-scale 2D convolutional encoder-decoder on real competition rasters with positive-tile PU filtering + collar ignore mask + exact `300 m` `DifferentiableDTILoss` + native 10 m $k_{sn}$/drainage-area fluvial de-confounding.
- **Expected gain / cost:** **Rank #1** — highest expected HOLDOUT-DTI lift (`+0.05` to `+0.13` HOLDOUT-DTI over `h33 = 0.3016` and `p8 = 0.2896`), ~4–6 minutes total CPU wall time across all 4 blocked quadrants.

---

### Rank 2 — `H74-2` (Reserve Lane):
**Fluvial Channel-Steepness ($\Delta k_{sn}$) & Cross-Divide Knickpoint Alignment (`dem10_chi_100m_i16` Graph Lineament Linking)**
- **Layers & signature:** Pairs `ksn_max_m0.9` jumps across `log10_area_m2` trunk streams from `dem10_chi_100m_i16.tif` (`USGS 3DEP 1/3 arc-sec DEM`, `https://www.usgs.gov/3d-elevation-program`) with `iso_grav_anom_hg` to link aligned stream knickpoints along range fronts where Holocene alluvial fans buried surface scarps.
- **Non-fault mimic:** Lithologic knickpoints on resistant Cenozoic basalt/welded-tuff caps.
- **Status:** Core physical features (`step_max`, `step_min`, `ksn_max`, `log10_area`, `zmean_m`) integrated directly into `H74-1`; standalone graph-linking held in reserve per single-lane rule.

### Rank 3 — `H74-3` (Reserve Lane):
**Magnetite-Destruction Demagnetization Trough + Potassium Adularia-Sericite Halo (`GeoDAWN Upward-Continued Vertical Derivative Residual + Th/K Anomaly`)**
- **Layers & signature:** Contrasts shallow GeoDAWN `tmi_vg` (`100 m` flight height, `doi:10.5066/P93LGLVQ`) against `150 m` upward-continued magnetic field (`geodawn_extensions_u8.tif`) co-located with `K` enrichment / low `Th/K` (`geodawn_rad_u8.tif`) where hydrothermal fluids oxidize host-rock magnetite to hematite/pyrite along blind permeable fault conduits.
- **Non-fault mimic:** Hydrothermally barren felsic ash-flow tuffs and playa evaporite potassium pans.
- **Status:** Upward-continuation residual + `K, Th/K` channels included as de-regionalized features inside `H74-1`; standalone halo detector not pursued separately (`GEMSDOE69`/`72` tested pure halo variants with negative lift).

### Rank 4 — `H74-4` (Reserve Lane):
**3D Potential-Field Euler Deconvolution & Tilt-Derivative Contact Depth Continuity (`TDR = atan(VDR / THDR)`)**
- **Layers & signature:** Computes scale-invariant magnetic/gravity tilt angle $\theta = \arctan(\text{VG} / \sqrt{\text{HG}^2 + \epsilon})$ across `tmi` and `iso_grav_anom` so deeply buried intrabasin graben faults with attenuated amplitude receive equal edge sharpness to shallow volcanic dikes, gated by `depth_to_base_surf`.
- **Non-fault mimic:** Intrusive pluton margins and caldera ring fractures.
- **Status:** Scale-invariant `tilt_mag` and `tilt_grav` zero-crossing sharpness included inside `H74-1`'s multi-physics tensor.

### Rank 5 — `H74-5` (Reserve Lane):
**Transtensional Strain-Partitioned Riedel & Relay-Stepover Stress Tensor (`Geodetic Dilatation × Shear Strike Projection`)**
- **Layers & signature:** Projects GPS geodetic principal strain axes (`geod_shearrate`, `geod_dilaterate`, `geod_2ndinv` from INGENIOUS `doi:10.15121/1881483`) onto local scarp/magnetic strike orientation to upweight faults oriented near optimal Mohr-Coulomb normal-oblique slip in the Walker Lane vs Basin-and-Range extension.
- **Non-fault mimic:** Long-wavelength GPS interpolation gradients across un-faulted intrarange blocks.

---

## Pre-Registered 3-Experiment Budget inside Committed Lane `H74-1`

- **Pre-Check (Mandatory Rule 4 Gate):** Run single-feature holdout AUC leakage canary across EVERY candidate feature channel on the 4 blocked quadrants (`max(AUC, 1 - AUC) <= 0.90` required to pass before any model fit).
- **Experiment 1 (`E1-PUDeconfTabOOF`):** 4-quadrant out-of-fold multi-physics + 10 m fluvial ($k_{sn}$, step, drainage area, elevation) + 1 m LiDAR + GDR-1391 hydrothermal gradient-boosted tabular model trained strictly on **positive `128×128` tiles** with **`1..3 px` registration-collar exclusion**, full valid footprint (`5,167,373` pixels — zero erosion), `0%` SGMC weight, and fold-only visible fault features.
- **Experiment 2 (`E2-ResUNetDiffDTI`):** 4-quadrant out-of-fold **2D Multi-Scale Depthwise-Separable ResUNet (`128×128` spatial patches, `~6.8 km` receptive field, $D_4$ dihedral augmentation & TTA)** trained strictly on **mapped `128×128` reference tiles** directly minimizing **exact differentiable `300 m` triangular-kernel `DifferentiableDTILoss(alpha=0.2, beta=0.8)`** with collar masking.
- **Experiment 3 (`E3-HybridCrestSubmod300`):** Out-of-fold calibrated log-odds synthesis of `E2-ResUNetDiffDTI` + `E1-PUDeconfTabOOF` + explicit cultural/lacustrine mimic suppression + structure-tensor cross-strike crest sharpening + exact unblurred `300 m` lazy-greedy submodular max-cover (`d_cat > 2.0 px`).
