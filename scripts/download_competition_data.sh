#!/usr/bin/env bash
set -euo pipefail
# Download competition data from DrivenData (requires login).
# Run this on any unrestricted machine with a browser login, then copy data/ to the repo.
# See https://www.drivendata.org/competitions/306/competition-doe-gems/data/ for file list.

echo "This script requires a DrivenData login (Terms prohibit robots/automatic access)."
echo "Manual steps:"
echo "  1. Log in at https://www.drivendata.org/competitions/306/competition-doe-gems/data/"
echo "  2. Download: training_features.tif, labels.tif, sample_submission.tif, 1m_DEM_links.csv"
echo "  3. Place into data/ (and optionally existing_faults.tif from Dropbox mirror)"
echo "  4. Run: python scripts/prepare_data.py"
echo ""
echo "Official mirrors (no login) for template/shape verification only:"
echo "  - example_submission.tif (Dropbox): https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0"
echo "  - existing_faults.tif: https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0"
echo "  - training_features preview: https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0"
echo ""
echo "After placing files, validate:"
echo "  python -c \"import rasterio; print(rasterio.open('data/sample_submission.tif').shape, rasterio.open('data/sample_submission.tif').crs)\""
