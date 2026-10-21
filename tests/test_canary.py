"""Leakage canary: single feature alone must lie strictly in [0.10, 0.90] (resolves IR-74-23 & IR-74-28)."""
import json
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def test_canary():
    rad_p = Path("/tmp/gems74_data/external/geodawn_rad_u8.tif")
    cat_p = Path("/tmp/gems74_data/labels.tif")
    foot_p = Path("/tmp/gems74_data/sample_submission.tif")
    if rad_p.is_file() and cat_p.is_file() and foot_p.is_file():
        K = rasterio.open(rad_p).read(1).astype(float)
        cat = rasterio.open(cat_p).read(1) > 0
        foot = np.isfinite(rasterio.open(foot_p).read(1))
        rng = np.random.default_rng(0)
        pos_idx = np.argwhere(cat & foot)
        neg_idx = np.argwhere(foot & ~cat)
        n_pos = min(2000, len(pos_idx))
        n_neg = 2000
        pos_sample = pos_idx[rng.choice(len(pos_idx), n_pos, replace=False)]
        neg_sample = neg_idx[rng.choice(len(neg_idx), n_neg, replace=False)]
        y = np.concatenate([np.ones(n_pos), np.zeros(n_neg)])
        X = np.concatenate([K[pos_sample[:, 0], pos_sample[:, 1]], K[neg_sample[:, 0], neg_sample[:, 1]]])
        auc = float(roc_auc_score(y, X))
        assert 0.10 <= auc <= 0.90, f"Leakage suspected: AUC {auc} outside [0.10, 0.90]"


def test_real_data_87_feature_canaries():
    canary_path = ROOT / "evidence" / "canaries.json"
    assert canary_path.is_file(), "evidence/canaries.json must exist"
    canaries = json.loads(canary_path.read_text())
    assert len(canaries) == 87, f"Expected 87 features in evidence/canaries.json, got {len(canaries)}"
    for fname, entry in canaries.items():
        auc = entry["auc"]
        eff = entry["effective_auc"]
        assert 0.10 <= auc <= 0.90, f"Feature {fname} AUC={auc} outside [0.10, 0.90]"
        assert eff <= 0.90, f"Feature {fname} effective_auc={eff} > 0.90"
        assert entry["suspected_leakage"] is False
