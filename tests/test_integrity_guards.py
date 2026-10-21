"""Regression tests for the integrity issues discovered in the review."""
import importlib.util
import json
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

@pytest.mark.parametrize('script', ['generate_submission.py', 'generate_h74v2.py'])
def test_synthetic_generators_cannot_publish_submission(script, tmp_path):
    p = subprocess.run([sys.executable, str(ROOT/'scripts'/script),
                        '--out', str(tmp_path)], capture_output=True, text=True)
    assert p.returncode == 2
    assert 'BLOCKED' in p.stderr
    assert not list(tmp_path.iterdir())


def test_h74v2_sidecars_withdraw_ready_and_invalid_scores():
    prefix = 'gemsdoe74-h74-1v2-basement-step-36270-20261021T000000Z-5a03072f'
    d = json.loads((ROOT/'docs/downloads'/f'{prefix}-zeros.receipt.json').read_text())
    assert d['release_status'] == 'HOLD — DO NOT SUBMIT'
    assert d['organizer_confirmed'] is False
    assert d['holdout_metric']['value'] is None
    assert d['holdout_metric']['ci95'] is None
    assert d['holdout_metric']['withheld_positive_count'] is None
    assert d['holdout_metric']['status'].startswith('NOT COMPUTED')
    assert d['registry_spearman'] is None
    assert d['registry_overlap_within_3px_percent'] is None

    sidecar = json.loads((ROOT/'docs/downloads'/f'{prefix}-zeros.json').read_text())
    assert sidecar['release_status'].startswith('HOLD')
    assert sidecar['official_template_match'] is None
    assert sidecar['official_catalogue_match'] is None
    assert 'NOT ESTABLISHED' in sidecar['scientific_validation']

    card = json.loads((ROOT/'docs/downloads'/f'{prefix}-run-card.json').read_text())
    assert card['verdict'] == 'negative'
    assert card['holdout_dti']['value'] is None
    assert card['organizer_confirmed'] is False

def test_leakage_canary_rejects_nonfinite_feature():
    labels = np.array([[0, 1], [0, 1]], dtype=bool)
    feature = np.array([[0., np.nan], [0., 1.]])
    with pytest.raises(ValueError, match='non-finite'):
        leakage_canary({'toy': feature}, labels, np.ones_like(labels))


def test_leakage_canary_flags_auc_above_threshold():
    labels = np.array([[0, 1], [0, 1]], dtype=bool)
    feature = labels.astype(float)
    result = leakage_canary({'toy': feature}, labels, np.ones_like(labels))
    assert result[0]['auc'] == pytest.approx(1.0)
    assert result[0]['flag_leakage'] is True


def test_leakage_canary_needs_both_classes():
    labels = np.ones((2, 2), dtype=bool)
    with pytest.raises(ValueError, match='both classes'):
        leakage_canary({'toy': labels.astype(float)}, labels, np.ones_like(labels))


def test_noncompliant_hide_and_recover_is_disabled():
    with pytest.raises(NotImplementedError, match='No compliant holdout evaluator'):
        hide_and_recover_scores(None, None, None, None, None)

def test_soft_prediction_not_binarized():
    p = np.zeros((7, 7)); g = np.zeros_like(p, bool)
    p[3, 3] = .2; g[3, 3] = True
    r = compute_dti_components(p, g)
    assert r['tp'] == pytest.approx(dti_exact(p, g)['tp'])
    assert r['tp'] == pytest.approx(.2)

def test_missing_data_removes_stale_success(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('prepare', ROOT/'scripts/prepare_data.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, 'DATA', tmp_path)
    manifest = tmp_path/'prepared_manifest.json'
    manifest.write_text('{"checked":true}')
    assert mod.main() == 2
    assert not manifest.exists()

def test_note_limit_matches_protocol():
    assert NOTE_MAX_CHARS == 140

@pytest.mark.parametrize('name', ['evaluate_holdout.py', 'evaluate_holdout_segments.py'])
def test_noncompliant_evaluators_blocked(name):
    p = subprocess.run([sys.executable, str(ROOT/'scripts'/name)], capture_output=True, text=True)
    assert p.returncode != 0 and 'BLOCKED' in p.stderr

def test_public_status_cannot_be_ready_from_untrusted_receipt():
    overview = (ROOT/'docs/index.html').read_text()
    receipt = json.loads(next((ROOT/'docs/downloads').glob('*h74-1v2*zeros.receipt.json')).read_text())
    assert 'DO NOT SUBMIT' in overview
    assert 'NOT OK to submit' in overview
    assert receipt['organizer_confirmed'] is False
    assert receipt['release_status'] == 'HOLD — DO NOT SUBMIT'
