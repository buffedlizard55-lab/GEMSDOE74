import pathlib, numpy as np, rasterio, tempfile, os
from gemsdoe74.grid import synthetic_footprint, WIDTH, HEIGHT, CRS, TRANSFORM, write_submission
from gemsdoe74.submission import validate_tif

def test_write_and_validate():
    shape=(HEIGHT,WIDTH)
    fp=synthetic_footprint(shape=shape, seed=0)
    arr=np.zeros(shape,dtype=np.float32)
    arr[HEIGHT//2, WIDTH//2]=1.0
    arr[HEIGHT//2+5, WIDTH//2+5]=0.5
    with tempfile.TemporaryDirectory() as td:
        tpl=pathlib.Path(td)/"tpl.tif"
        # create fake template
        meta=dict(driver="GTiff", dtype="float32", count=1, crs=CRS, transform=TRANSFORM, width=WIDTH, height=HEIGHT, nodata=None)
        with rasterio.open(tpl,"w",**meta) as dst:
            dst.write(np.where(fp,0.0,0.0).astype(np.float32),1)
        out=pathlib.Path(td)/"out.tif"
        # use write_submission from grid
        write_submission(arr, str(tpl), str(out), footprint=fp, outside="zero")
        v=validate_tif(out, tpl)
        assert v["passed"], v["checks"]
        with rasterio.open(out) as ds:
            got=ds.read(1)
            assert got.shape==shape
            assert ds.crs.to_string()==CRS
            assert ds.transform==TRANSFORM
            assert got.min()>=0 and got.max()<=1
            assert np.isfinite(got).all()

def test_range_guard():
    shape=(HEIGHT,WIDTH)
    fp=synthetic_footprint(shape=shape)
    bad=np.zeros(shape,dtype=np.float32)
    bad[100,100]=1.5
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        tpl=pathlib.Path(td)/"tpl.tif"
        meta=dict(driver="GTiff", dtype="float32", count=1, crs=CRS, transform=TRANSFORM, width=WIDTH, height=HEIGHT, nodata=None)
        with rasterio.open(tpl,"w",**meta) as dst:
            dst.write(np.zeros(shape,dtype=np.float32),1)
        try:
            write_submission(bad, str(tpl), str(pathlib.Path(td)/"bad.tif"), footprint=fp, outside="zero")
            assert False, "should have raised"
        except AssertionError:
            pass
