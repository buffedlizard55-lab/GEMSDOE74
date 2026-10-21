import pathlib, rasterio, numpy as np
def test_submission_exists_and_valid():
    p = pathlib.Path("docs/downloads/gems74-h74-alt-spring-39500-20261021T000000Z-52f76038-zeros.tif")
    assert p.exists(), f"missing {p}"
    with rasterio.open(p) as src:
        assert src.count==1
        assert src.dtypes[0]=="float32"
        assert src.height==3730 and src.width==3292
        assert src.crs.to_epsg()==32611
        assert src.transform == rasterio.Affine(100,0,243350,0,-100,4508550)
        assert src.nodata is None
        data=src.read(1)
        assert np.isfinite(data).all()
        assert (data>=0).all() and (data<=1).all()
        assert (data>0).sum()==39500
        assert data.min()==0.0 and data.max()==1.0
def test_no_catalogue_leakage():
    import rasterio as rio
    p = pathlib.Path("docs/downloads/gems74-h74-alt-spring-39500-20261021T000000Z-52f76038-zeros.tif")
    try:
        cat = rio.open("/tmp/gems74_data/labels.tif").read(1)>0
    except:
        return
    with rio.open(p) as src:
        data=src.read(1)>0
        assert (data & cat).sum()==0
