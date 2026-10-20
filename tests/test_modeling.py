"""
Unit and regression tests for Late Delivery Decision Tree Prediction Engine.
"""

from pathlib import Path

import joblib
import numpy as np
import pytest

from src.marketplace_intelligence.modeling import LateDeliveryPredictor, ModelFeatures

PROCESSED_DIR = Path("data/processed")
DOCS_DIR = Path("docs")
MODELS_DIR = Path("models")

pytestmark = pytest.mark.skipif(
    not (PROCESSED_DIR / "order_features.parquet").exists(),
    reason="order_features.parquet not present in environment",
)


@pytest.fixture(scope="module")
def predictor():
    return LateDeliveryPredictor(
        processed_dir=PROCESSED_DIR,
        docs_dir=DOCS_DIR,
        models_dir=MODELS_DIR,
    )


@pytest.fixture(scope="module")
def split_data(predictor):
    return predictor.load_and_split_data(train_ratio=0.80)


def test_feature_registry_anti_leakage():
    """Verifies that post-dispatch variables are strictly banned from model inputs."""
    registry = ModelFeatures()
    all_feats = registry.all_features

    for banned in registry.banned_leakage_cols:
        assert banned not in all_feats, (
            f"CRITICAL LEAKAGE: '{banned}' found in model feature set!"
        )

    # Target must not be in features
    assert registry.target_col not in all_feats


def test_temporal_split_chronological_order(split_data):
    """Verifies that train and test sets strictly respect chronological time without leakage."""
    df_train, df_test, X_train, y_train, X_test, y_test = split_data

    # Chronological barrier
    train_max_date = df_train["order_purchase_timestamp"].max()
    test_min_date = df_test["order_purchase_timestamp"].min()
    assert train_max_date <= test_min_date, (
        f"Temporal leak: Train max {train_max_date} > Test min {test_min_date}"
    )

    # Split sizes
    total_len = len(df_train) + len(df_test)
    assert total_len > 90000
    assert abs(len(df_train) / total_len - 0.80) < 0.01
    assert len(X_train) == len(y_train)
    assert len(X_test) == len(y_test)


def test_model_pipeline_execution_and_metrics(predictor, split_data):
    """Tests pipeline fitting, probability calibration, and performance bounds."""
    _df_train, _df_test, X_train, y_train, X_test, y_test = split_data

    pipeline = predictor.build_pipeline(
        max_depth=6, min_samples_leaf=100, class_weight="balanced"
    )
    pipeline.fit(X_train, y_train)

    probs = pipeline.predict_proba(X_test)[:, 1]
    preds = pipeline.predict(X_test)

    assert len(probs) == len(y_test)
    assert (probs >= 0.0).all() and (probs <= 1.0).all()
    assert set(np.unique(preds)).issubset({0, 1})

    metrics = predictor.evaluate_models(X_train, y_train, X_test, y_test, pipeline)

    prod = metrics["Balanced Tree (Production)"]
    dummy = metrics["Dummy Baseline"]

    # Model must beat random chance significantly
    assert prod["roc_auc"] > 0.70
    assert prod["pr_auc"] > dummy["pr_auc"]
    assert prod["recall"] > 0.50  # Over 50% capture of late deliveries


def test_model_persistence(predictor, split_data):
    """Verifies serialization and deserialization reproducibility with joblib."""
    _df_train, _df_test, X_train, y_train, X_test, _y_test = split_data

    pipeline = predictor.build_pipeline(
        max_depth=4, min_samples_leaf=100, class_weight="balanced"
    )
    pipeline.fit(X_train, y_train)

    model_path = MODELS_DIR / "test_tree.joblib"
    joblib.dump(pipeline, model_path)
    assert model_path.exists()

    loaded_pipeline = joblib.load(model_path)
    orig_probs = pipeline.predict_proba(X_test.head(100))[:, 1]
    loaded_probs = loaded_pipeline.predict_proba(X_test.head(100))[:, 1]

    np.testing.assert_allclose(orig_probs, loaded_probs, rtol=1e-5)
    model_path.unlink()  # Clean up test artifact


def test_feature_importances_structure(predictor, split_data):
    """Verifies that feature importances are valid and top drivers align with logistics reality."""
    _df_train, _df_test, X_train, y_train, _X_test, _y_test = split_data

    pipeline = predictor.build_pipeline(
        max_depth=6, min_samples_leaf=100, class_weight="balanced"
    )
    pipeline.fit(X_train, y_train)

    importances = predictor.extract_feature_importances(pipeline)
    assert len(importances) > 0
    assert pytest.approx(importances.sum(), rel=1e-4) == 1.0

    top_features = list(importances.head(5).index)
    assert any(
        "seller" in feat or "state" in feat or "duration" in feat
        for feat in top_features
    )


def test_threshold_table_and_rules(predictor, split_data):
    """Tests threshold sensitivity grid and plain-text rule extraction."""
    _df_train, _df_test, X_train, y_train, X_test, y_test = split_data

    pipeline = predictor.build_pipeline(
        max_depth=4, min_samples_leaf=100, class_weight="balanced"
    )
    pipeline.fit(X_train, y_train)

    table = predictor.compute_threshold_table(pipeline, X_test, y_test)
    assert len(table) == 7
    assert "Estimated Risk Cost (BRL)" in table.columns

    rules = predictor.extract_tree_rules(pipeline, max_depth=3)
    assert isinstance(rules, str)
    assert len(rules) > 50
    assert "is_seller_late_dispatch" in rules
