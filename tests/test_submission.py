import json
import pathlib
import sys
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gemsdoe74.submission import write_submission_geotiff, validate_tif
from gemsdoe74.grid import synthetic_footprint, WIDTH, HEIGHT
from scripts.validate_submission import validate_submission_file


def test_submission_writer(tmp_path):
    fp = synthetic_footprint()
    pred = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    ys, xs = np.where(fp)
    pred[ys[:100], xs[:100]] = 1.0
    zpath = tmp_path / "test-sub-100-zeros.tif"
    npath = tmp_path / "test-sub-100-nan.tif"
    rz = write_submission_geotiff(pred, None, zpath, outside_mode="zeros", note="test note")
    rn = write_submission_geotiff(pred, None, npath, outside_mode="nan", note="test note")
    assert rz["all_checks_passed"]
    assert rn["all_checks_passed"]
    assert rz["emitted_positive_pixels"] == 100
    assert zpath.exists()
    v = validate_tif(zpath, None, strict_portal_safe=True)
    assert v["passed"]


def test_promoted_h74_r1_submission_and_run_card():
    zeros_p = ROOT / "docs/downloads/gemsdoe74-h74-r1-transtensional-submod-37654-20261021T000000Z-zeros.tif"
    nan_p = ROOT / "docs/downloads/gemsdoe74-h74-r1-transtensional-submod-37654-20261021T000000Z-nan.tif"
    zip_p = ROOT / "docs/downloads/gemsdoe74-h74-r1-transtensional-submod-37654-20261021T000000Z.zip"
    assert zeros_p.is_file()
    assert nan_p.is_file()
    assert zip_p.is_file()

    vz = validate_submission_file(zeros_p, require_all_finite=True)
    vn = validate_submission_file(nan_p, require_all_finite=False)
    assert vz["all_checks_passed"] is True
    assert vn["all_checks_passed"] is True
    assert vz["emitted_positive_pixels"] == 37654
    assert vz["outside_footprint_positive_pixels"] == 0
    assert vz["on_catalogue_positive_pixels"] == 0
    assert vz["full_grid_finite_pixels"] == 12279160
    assert vn["full_grid_finite_pixels"] == 5167373

    rc = json.loads((ROOT / "evidence/run_card.json").read_text())
    assert rc["verdict"] == "promote"
    assert rc["ok_to_submit"] is True
    assert rc["submission"]["short_note_length"] <= 140
    assert rc["leakage_canary"]["all_passed"] is True
    assert rc["registry_uniqueness"]["all_gates_passed"] is True
    assert rc["registry_uniqueness"]["max_mutual_3px_overlap"] <= 0.70
    assert rc["registry_uniqueness"]["max_abs_spearman_dots"] <= 0.90
    assert rc["registry_uniqueness"]["max_abs_spearman_surface"] <= 0.90

    build_meta = json.loads((ROOT / "registry/submission_build.json").read_text())
    assert build_meta["verdict"] == "promote"
    assert not str(build_meta).count("/home/user/")


def test_real_lane_operators_and_submodular_spacing():
    from gemsdoe74.real_lane import (
        _destripe_ew_flightline,
        _hessian_ridge_multiscale,
        compute_fold_safe_mechanics,
        peak_nms_emit,
        submodular_spaced_dti_emit,
    )
    rng = np.random.default_rng(74)
    arr = rng.normal(size=(48, 48)).astype(np.float32)
    # Inject synthetic E-W row striping
    arr[::2, :] += 2.5
    clean = _destripe_ew_flightline(arr)
    assert np.isfinite(clean).all()
    assert float(np.std(clean[:, 24])) < float(np.std(arr[:, 24]))

    ridge = _hessian_ridge_multiscale(clean, sigmas=(1.0, 2.0))
    assert ridge.shape == arr.shape
    assert (ridge >= 0.0).all()

    vis = np.zeros((48, 48), dtype=bool)
    vis[10:30, 20] = True
    tip, rel = compute_fold_safe_mechanics(vis)
    assert tip.shape == (48, 48) and rel.shape == (48, 48)
    assert tip[20, 20] == 0.0  # suppressed on visible trace

    prob = rng.uniform(0.05, 0.95, size=(48, 48)).astype(np.float32)
    allowed = np.ones((48, 48), dtype=bool)
    dots_nms = peak_nms_emit(prob, allowed, n_dots=25)
    assert int((dots_nms > 0.5).sum()) == 25
    dots_sub = submodular_spaced_dti_emit(prob, allowed, n_dots=25, min_spacing_px=2.5)
    assert int((dots_sub > 0.5).sum()) == 25


def test_all_docs_html_links_and_synchronized_manifests():
    import re
    html_files = list((ROOT / "docs").glob("*.html")) + list((ROOT / "docs/review").glob("*.html"))
    assert len(html_files) >= 15
    for hp in html_files:
        txt = hp.read_text()
        assert "GEMSDOE74" in txt
        if hp.name in ("index.html", "executive-summary.html", "submit-checklist.html"):
            assert "VERDICT: PROMOTE" in txt
            assert "OK TO DOWNLOAD AND SUBMIT" in txt
        for m in re.finditer(r'href="([^"#]+)"', txt):
            href = m.group(1)
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            target = (hp.parent / href).resolve()
            assert target.exists(), f"Broken link {href} in {hp} -> {target}"

