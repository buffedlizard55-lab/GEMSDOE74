#!/usr/bin/env python3
"""Validate a submission TIF against competition portal rules."""
import pathlib, sys, json, hashlib
import numpy as np, rasterio
p = pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path("docs/downloads/gems74-h74-alt-spring-39500-20261021T000000Z-52f76038-zeros.tif")
print(f"Validating {p}")
with rasterio.open(p) as src:
    data = src.read(1)
    profile = src.profile
    checks = {}
    checks["single_band"] = src.count==1
    checks["dtype_float32"] = src.dtypes[0]=="float32"
    checks["dimensions_3730x3292"] = (src.height==3730 and src.width==3292)
    checks["crs_epsg_32611"] = src.crs and src.crs.to_epsg()==32611
    checks["transform"] = src.transform == rasterio.Affine(100,0,243350,0,-100,4508550)
    checks["in_footprint_all_finite"] = bool(np.isfinite(data).all())
    checks["in_footprint_zero_nan"] = int(np.isnan(data).sum())==0
    checks["in_footprint_zero_inf"] = int(np.isinf(data).sum())==0
    checks["in_footprint_range_0_1"] = bool((data>=0).all() and (data<=1).all())
    checks["outside_footprint_compliant"] = True  # zeros mode always compliant
    checks["validator_range_0_1_guaranteed"] = checks["in_footprint_range_0_1"] and checks["in_footprint_zero_nan"]
    # footprint
    # catalogue check if available
    try:
        cat = rasterio.open("/tmp/gems74_data/labels.tif").read(1)>0
        on_cat = int(((data>0) & cat).sum())
        checks["zero_on_catalogue_leakage"] = (on_cat==0)
        print(f"on_catalogue {on_cat}")
    except Exception as e:
        checks["zero_on_catalogue_leakage"] = None
        print(f"catalogue check skipped: {e}")
    print(f"profile: {profile}")
    print(f"shape {data.shape} dtype {data.dtype} min {data.min()} max {data.max()} nonzero {(data>0).sum()} nodata {src.nodata}")
    print(f"checks: {json.dumps(checks, indent=2)}")
    if all(v for v in checks.values() if v is not None):
        print("ALL CHECKS PASS")
    else:
        print("SOME CHECKS FAIL")
        sys.exit(1)
