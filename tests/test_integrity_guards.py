"""Regression tests for the integrity issues discovered in the review."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest
from gemsdoe74.holdout import leakage_canary, hide_and_recover_scores
from gemsdoe74.metric import compute_dti_components
from gems74.metric import dti_exact
from gems74.submission import NOTE_MAX_CHARS

ROOT = Path(__file__).resolve().parents[1]

def test_generator_cannot_publish_synthetic_submission(tmp_path):
    p = subprocess.run([sys.executable, str(ROOT/'scripts/generate_submission.py'),
                        '--out', str(tmp_path)], capture_output=True, text=True)
    assert p.returncode == 2
    assert 'BLOCKED' in p.stderr
    assert not list(tmp_path.iterdir())

@pytest.mark.parametrize('feature,labels', [
    ([0., float('nan')], [0, 1]), ([0., 1.], [1, 1]),
    ([0., 1.], [0, 1]), ([1., 0.], [0, 1])])
def test_invalid_or_perfect_canary_fails_closed(feature, labels):
    r = leakage_canary({'test': np.array(feature)}, np.array(labels), np.ones(2, bool))
    assert r[0]['flag_leakage']

def test_visible_catalogue_is_pixel_exactly_masked():
    pred = np.zeros((7, 7)); truth = np.zeros_like(pred, bool)
    pred[3, 3] = 1; truth[3, 3] = True
    valid = np.ones_like(truth)
    score = hide_and_recover_scores(pred, truth, truth, valid, [{'val': valid}])
    # With the historical empty-domain convention, no mass remains in scoring.
    assert score == [1.0]

def test_soft_prediction_not_binarized():
    p = np.zeros((7, 7)); g = np.zeros_like(p, bool)
    p[3, 3] = .2; g[3, 3] = True
    r = compute_dti_components(p, g)
    assert r['tp'] == pytest.approx(dti_exact(p, g)['tp'])
    assert r['tp'] == pytest.approx(.2)

def test_missing_data_removes_stale_success(tmp_path):
    spec = importlib.util.spec_from_file_location('prepare', ROOT/'scripts/prepare_data.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    m = tmp_path/'prepared_manifest.json'; m.write_text('{"checked":true}')
    with pytest.raises(ValueError, match='Missing required real inputs'):
        mod.prepare(tmp_path)
    assert not m.exists()

def test_note_limit_matches_protocol():
    assert NOTE_MAX_CHARS == 140

@pytest.mark.parametrize('name', ['evaluate_holdout.py', 'evaluate_holdout_segments.py'])
def test_noncompliant_evaluators_blocked(name):
    p = subprocess.run([sys.executable, str(ROOT/'scripts'/name)], capture_output=True, text=True)
    assert p.returncode != 0 and 'BLOCKED' in p.stderr

def test_public_status_cannot_be_ready_from_untrusted_receipt():
    spec = importlib.util.spec_from_file_location('site', ROOT/'scripts/build_site.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    assert 'DO NOT SUBMIT' in mod.page('Test', '')
