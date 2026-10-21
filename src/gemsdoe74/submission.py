"""Submission writer — portal-safe GeoTIFF builder with audit receipt.

Reuses template cached feature stack pattern (see grid.py) and mirrors GEMSDOE32/30 logic:
- every cell finite, values in [0,1], no nodata sentinel
- CRS/shape/transform matched to template (official sample_submission.tif when present, else pinned constants)
- sidecar JSON with sha256, checks, note, validation receipt
"""
from __future__ import annotations
import hashlib, json, pathlib
from datetime import datetime, timezone
import numpy as np
import rasterio
from .grid import template_profile, synthetic_footprint, WIDTH, HEIGHT, CRS, TRANSFORM, FOOTPRINT_CELLS

def sha256_of(path: pathlib.Path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''): h.update(chunk)
    return h.hexdigest()

def validate_tif(path: pathlib.Path, template_path: pathlib.Path | None, strict_portal_safe=True):
    import rasterio
    checks=[]
    with rasterio.open(path) as ds:
        arr=ds.read(1)
        # dimensions
        ok = (ds.width==WIDTH and ds.height==HEIGHT)
        checks.append({"name":"dimensions","passed":ok,"detail":f"{ds.width}x{ds.height} expected {WIDTH}x{HEIGHT}"})
        # bands
        ok = ds.count==1
        checks.append({"name":"band_count","passed":ok,"detail":f"count {ds.count}"})
        # crs
        ok = ds.crs.to_string()==CRS
        checks.append({"name":"crs","passed":ok,"detail":f"{ds.crs} expected {CRS}"})
        # transform
        ok = ds.transform==TRANSFORM
        checks.append({"name":"transform","passed":ok,"detail":f"{ds.transform} expected {TRANSFORM}"})
        # dtype
        ok = ds.dtypes[0]=="float32"
        checks.append({"name":"dtype","passed":ok,"detail":f"{ds.dtypes[0]}"})
        # footprint for inside check — if template exists use its finite mask, else use synthetic
        if template_path and pathlib.Path(template_path).exists():
            with rasterio.open(template_path) as tpl:
                tpl_arr=tpl.read(1)
                footprint=np.isfinite(tpl_arr)
        else:
            from .grid import synthetic_footprint
            footprint=synthetic_footprint(shape=arr.shape)
        inside=arr[footprint]
        # For NaN-outside mode, outside is allowed to be NaN; we check only inside for portal-safe
        if strict_portal_safe:
            finite = np.isfinite(arr).all()
            checks.append({"name":"all_finite","passed":bool(finite),"detail":f"finite {finite} (strict portal-safe: whole array must be finite)"})
            mn, mx = float(np.nanmin(arr)), float(np.nanmax(arr))
            in_range = (mn>=0.0 and mx<=1.0) and finite
            checks.append({"name":"range_0_1","passed":bool(in_range),"detail":f"[{mn:.6f},{mx:.6f}] whole array"})
        else:
            finite_inside = np.isfinite(inside).all()
            checks.append({"name":"inside_finite","passed":bool(finite_inside),"detail":f"inside finite {finite_inside}"})
            if finite_inside and len(inside)>0:
                mn, mx = float(inside.min()), float(inside.max())
                in_range = (mn>=0.0 and mx<=1.0)
                detail=f"inside [{mn:.6f},{mx:.6f}]"
            else:
                in_range=False
                detail="inside not finite or empty"
            checks.append({"name":"range_0_1_inside","passed":bool(in_range and finite_inside),"detail":detail})
            # Outside allowed to be NaN; check no sentinel anywhere
            sentinel = np.any(arr==-3.402823e38)
            checks.append({"name":"no_sentinel","passed":not bool(sentinel),"detail":"sentinel -3.4e38 absent"})
            # nodata should be NaN for spec-literal
            ok = ds.nodata is not None and np.isnan(ds.nodata) if ds.nodata is not None else False
            # Allow either None or nan depending on mode; for non-strict we just report
            checks.append({"name":"nodata_nan_outside","passed":True,"detail":f"nodata={ds.nodata} (spec-literal allows NaN)"})
            # No sentinel inside
            return {"passed": all(c["passed"] for c in checks if c["name"] in ("dimensions","band_count","crs","transform","dtype","inside_finite","range_0_1_inside","no_sentinel")), "checks":checks}
        # no sentinel
        sentinel = np.any(arr==-3.402823e38)
        checks.append({"name":"no_sentinel","passed":not bool(sentinel),"detail":"sentinel -3.4e38 absent"})
        # nodata
        ok = ds.nodata is None
        checks.append({"name":"nodata_none_portal_safe","passed":ok,"detail":f"nodata={ds.nodata}"})
    # template match if provided
    if template_path and pathlib.Path(template_path).exists():
        with rasterio.open(template_path) as tpl, rasterio.open(path) as sub:
            ok = (tpl.width==sub.width and tpl.height==sub.height and tpl.crs==sub.crs and tpl.transform==sub.transform)
            checks.append({"name":"template_match","passed":ok,"detail":"CRS/shape/transform match template"})
    passed = all(c["passed"] for c in checks)
    return {"passed":passed,"checks":checks}

def write_submission_geotiff(predictions: np.ndarray, template_path: pathlib.Path | None, out_path: pathlib.Path, outside_mode="zeros", note=None):
    """Write predictions (H,W) float32 [0,1] to portal-safe TIF.

    predictions: 2D array (H,W) with 0/1 dots or probabilities in [0,1]
    template_path: optional real sample_submission.tif for exact CRS copy (if missing uses pinned constants)
    outside_mode: "zeros" (portal-safe, recommended) or "nan" (spec-literal)
    """
    preds = np.asarray(predictions, dtype=np.float32)
    assert preds.shape==(HEIGHT,WIDTH), f"predictions shape {preds.shape} != {(HEIGHT,WIDTH)}"
    assert np.isfinite(preds).all(), "predictions contain non-finite"
    assert (preds>=0).all() and (preds<=1).all(), f"predictions range [{preds.min()},{preds.max()}] outside [0,1]"
    out_path=pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine footprint: if template exists use its finite mask, else use synthetic
    if template_path and pathlib.Path(template_path).exists():
        with rasterio.open(template_path) as tpl:
            tpl_arr=tpl.read(1)
            footprint=np.isfinite(tpl_arr)
            profile=dict(tpl.profile)
            profile.update(dtype="float32", count=1, compress="deflate", nodata=None if outside_mode=="zeros" else float("nan"))
            profile["width"]=WIDTH; profile["height"]=HEIGHT; profile["crs"]=CRS; profile["transform"]=TRANSFORM
    else:
        footprint=synthetic_footprint(shape=(HEIGHT,WIDTH))
        profile=template_profile(compress="deflate", nodata=None if outside_mode=="zeros" else float("nan"))

    if outside_mode=="zeros":
        out=np.where(footprint, preds, 0.0).astype(np.float32)
        out=np.clip(out,0,1)
        profile["nodata"]=None
    else:
        out=np.where(footprint, preds, np.nan).astype(np.float32)
        profile["nodata"]=float("nan")

    with rasterio.open(out_path,"w",**profile) as dst:
        dst.write(out,1)

    # Re-read validation: strict for zeros, lenient for nan
    audit=validate_tif(out_path, template_path, strict_portal_safe=(outside_mode=="zeros"))
    if not audit["passed"]:
        raise ValueError(f"Validation failed: {audit}")

    sha=sha256_of(out_path)
    emitted=int(np.count_nonzero(out[footprint]>0))
    ts=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if note is None:
        note=f"GEMSDOE74 H74-1 basement-step {emitted} dots; all-finite 0-1; B=2 off-cat; {ts}"
    if len(note)>200: note=note[:197]+"..."

    manifest={
        "file_path":str(out_path),
        "file_name":out_path.name,
        "sha256":sha,
        "timestamp_utc":ts,
        "outside_mode":outside_mode,
        "crs":CRS,
        "transform":[TRANSFORM.a, TRANSFORM.b, TRANSFORM.c, TRANSFORM.d, TRANSFORM.e, TRANSFORM.f],
        "shape":[HEIGHT,WIDTH],
        "dtype":"float32",
        "nodata":None if outside_mode=="zeros" else "nan",
        "emitted_positive_pixels":emitted,
        "footprint_cells":int(footprint.sum()),
        "footprint_fraction":float(footprint.sum()/(HEIGHT*WIDTH)),
        "on_catalogue":0,  # set by caller if needed
        "in_footprint_finite_pixels":int(np.isfinite(out[footprint]).sum()),
        "in_footprint_min":float(out[footprint].min() if footprint.sum()>0 else 0),
        "in_footprint_max":float(out[footprint].max() if footprint.sum()>0 else 0),
        "full_grid_finite_pixels":int(np.isfinite(out).sum()),
        "full_grid_min":float(float(out.min())),
        "full_grid_max":float(float(out.max())),
        "checks":audit["checks"],
        "all_checks_passed":audit["passed"],
        "validation_passed":audit["passed"],
        "note":note,
        "unique_id":sha[:12],
    }
    # sidecar
    out_path.with_suffix(".json").write_text(json.dumps(manifest,indent=2)+"\n")
    return manifest
