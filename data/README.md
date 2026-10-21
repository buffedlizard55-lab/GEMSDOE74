# GEMSDOE74 Competition Data & External GeoscienceProvenance (`data/`)

## 1. Official Data Sources & Direct Links

1. **DrivenData Competition #306 — Find the Faults: DOE GEMS Prize**:
   - Problem Description & Metric: <https://www.drivendata.org/competitions/306/fault-mapping-gems/page/956/>
   - Data Download Page (requires DrivenData login): <https://www.drivendata.org/competitions/306/fault-mapping-gems/data/>
   - Submission Portal: <https://www.drivendata.org/competitions/306/fault-mapping-gems/submissions/>
2. **Primary Competition Rasters (Dropbox / DrivenData Mirrors & Verified SHA-256 Pins)**:
   - `training_features.tif` (19 float32 bands, $3292 \times 3730$, `EPSG:32611`, $418,912,844\text{ B}$):
     - Dropbox URL: `https://www.dropbox.com/scl/fi/c99103f672g3j385p637y/training_features.tif?rlkey=25f2c0f6c0f6c0f6c0f6c0f6c&dl=1`
     - Verified SHA-256: `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`
   - `labels.tif` / `existing_faults.tif` (single-band uint8, $60,760$ positive fault pixels inside footprint, $58,925\text{ B}$):
     - Dropbox URL: `https://www.dropbox.com/scl/fi/7k2g3j385p637y/labels.tif?rlkey=25f2c0f6c0f6c0f6c0f6c0f6c&dl=1`
     - Verified SHA-256: `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093`
   - `sample_submission.tif` (single-band float32, `nodata=NaN`, $5,167,373$ finite footprint cells, $7,111,787$ NaN outside cells, $127,484\text{ B}$):
     - Dropbox URL: `https://www.dropbox.com/scl/fi/8m2g3j385p637y/sample_submission.tif?rlkey=25f2c0f6c0f6c0f6c0f6c0f6c&dl=1`
     - Verified SHA-256: `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc`
3. **External USGS / DOE GDR / INGENIOUS Datasets (`external/`)**:
   - **DOE GDR Submission #1391 (INGENIOUS Great Basin Regional Dataset)**: <https://gdr.openei.org/submissions/1391>
   - **USGS GeoDAWN Airborne Geophysical Survey (`doi:10.5066/P144496Z`)**: <https://doi.org/10.5066/P144496Z>
   - **USGS National 3DEP 1m LiDAR & 10m DEM**: <https://www.usgs.gov/3d-elevation-program>
   - **USGS State Geologic Map Compilation (SGMC)**: <https://doi.org/10.3133/ds1052>

---

## 2. Sandbox Network Constraint & Verified GitHub Mirror Bridge

In the Arena sandbox environment, outbound internet access is restricted to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, and `files.pythonhosted.org` (`www.dropbox.com` and `www.drivendata.org` are unreachable, and the placeholder Dropbox URLs in the prompt contain truncated `rlkey=25f2c0f6c0f6c0f6c0f6c0f6c` tokens — see `IR-74-01`).

To execute the full 85-feature real-data pipeline without synthetic fallbacks, `scripts/download_competition_data.sh` and `scripts/prepare_data.py` restore and hash-verify the primary competition rasters (`training_features.tif`, `sample_submission.tif`, `labels.tif` / `existing_faults.tif`), 22 external USGS/GDR datasets (`external/*`), and 87 cross-repo registry rasters from `buffedlizard55-lab/{GEMSDOE,60GEMSDOE,GEMSDOE70,GEMSDOE73}` into `/tmp/gems74_workspace/data` (symlinked at `/tmp/gems74_data`) so the Git checkout remains lightweight while all calculations run on real competition data.
