# Local competition data (not committed)

Keep raw rasters and derived caches here only when obtained through authorized sources; Git ignores everything under `data/` except this file. The project brief identifies these required official inputs:

- `training_features.tif`
- `labels.tif`
- `sample_submission.tif`
- `1m_DEM_links.csv`

None is currently present in this checkout. Competition access is reported to require a DrivenData login; do not store credentials or bypass that access control. Obtain files through the official competition data page and record provenance, licence, grid metadata, and hashes.

`scripts/fetch_data.sh` is a partial, hash-pinned mirror from another owner repository, not an official download and not the full competition dataset. It was not run. It does not fetch `training_features.tif`, `1m_DEM_links.csv`, or the shared cached feature stack. Do not treat mirror files as official provenance or invent a feature-cache layout in place of the shared template.
