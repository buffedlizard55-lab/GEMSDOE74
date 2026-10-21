# `data/` — authorized official inputs only

This checkout intentionally contains no competition rasters. The [official DrivenData data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) redirected to login when checked on 2026-10-21; no automated download or third-party mirror was used.

On a machine where the competition participant is authorized to access the data, download the official files from <https://www.drivendata.org/competitions/306/competition-doe-gems/data/> and place these files here:

- `sample_submission.tif` — authoritative geometry and outside-bounds mask
- `training_features.tif` — organizer-provided feature layers
- `labels.tif` — provided training labels
- `1m_DEM_links.csv` — optional DEM links, if required by the method

Do not use a mirror unless both challenge eligibility and data rights are verified. Do not commit rasters or credentials. After placing inputs, run `python scripts/prepare_data.py`. It checks required files and grid metadata and writes a local hash manifest; it does not verify download provenance or cache features. The current C1 model and segment-buffered holdout are not implemented, so data placement alone does not clear any submission.
