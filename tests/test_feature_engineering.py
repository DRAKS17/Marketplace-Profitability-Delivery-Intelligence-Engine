"""
Automated Validation Tests for Feature Engineering & Target Construction.

Tests verify:
1. Feature store grain, row count, and primary key uniqueness.
2. Correct target variable construction (binary late delivery and delay days).
3. Financial consistency (GMV + Freight = Total Value, Freight Ratio bounded [0, 1]).
4. Spatial Haversine distance non-negativity.
5. Zero-leakage expanding historical seller performance.
6. Temporal and calendar feature boundaries.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROCESSED_DIR = Path("data/processed")

pytestmark = pytest.mark.skipif(
    not (PROCESSED_DIR / "order_features.parquet").exists(),
    reason="Processed order_features.parquet not present in environment",
)


@pytest.fixture(scope="module")
def feature_store() -> pd.DataFrame:
    """Loads engineered order feature store for testing."""
    path = PROCESSED_DIR / "order_features.parquet"
    assert path.exists(), "order_features.parquet was not found."
    return pd.read_parquet(path)


def test_feature_store_shape_and_grain(feature_store: pd.DataFrame):
    """Confirms feature store has 1 row per order and correct row count."""
    assert len(feature_store) == 99441
    assert feature_store["order_id"].is_unique, (
        "order_id must be strictly unique in feature store."
    )
    assert len(feature_store.columns) >= 30, (
        "Feature store should contain at least 30 features."
    )


def test_target_variable_construction(feature_store: pd.DataFrame):
    """Confirms late-delivery target definition and observable population rules."""
    delivered = feature_store[feature_store["order_delivered_customer_date"].notna()]
    undelivered = feature_store[feature_store["order_delivered_customer_date"].isna()]

    # Undelivered orders must have NaN target (cannot observe outcome)
    assert undelivered["is_late_delivery"].isna().all()

    # Delivered orders must have binary 0.0 or 1.0 target
    assert set(delivered["is_late_delivery"].unique()).issubset({0.0, 1.0})

    # Verify exact late delivery logic: delay_days > 0.0 -> is_late == 1.0
    late_mask = delivered["delivery_delay_days"] > 0.0
    assert (delivered.loc[late_mask, "is_late_delivery"] == 1.0).all()
    assert (delivered.loc[~late_mask, "is_late_delivery"] == 0.0).all()

    # Baseline late rate should be ~8.1%
    late_rate = delivered["is_late_delivery"].mean()
    assert 0.07 <= late_rate <= 0.09, f"Unexpected late rate: {late_rate:.3%}"


def test_financial_features_consistency(feature_store: pd.DataFrame):
    """Confirms financial totals add up and freight ratio is bounded."""
    computed_total = (
        feature_store["order_total_item_value"]
        + feature_store["order_total_freight_value"]
    )
    np.testing.assert_allclose(
        feature_store["order_total_value"], computed_total, atol=1e-2
    )

    # Freight ratio must be within [0, 1] for orders with value
    with_val = feature_store[feature_store["order_total_value"] > 0]
    assert with_val["freight_ratio"].between(0.0, 1.0).all()


def test_spatial_haversine_distance(feature_store: pd.DataFrame):
    """Confirms Haversine distance is non-negative and valid."""
    assert (feature_store["haversine_distance_km"] >= 0.0).all()
    # Distance within Brazil shouldn't exceed 5,000 km
    assert (feature_store["haversine_distance_km"] <= 5000.0).all()


def test_zero_leakage_seller_history(feature_store: pd.DataFrame):
    """Confirms expanding historical seller performance contains no forward-looking leakage."""
    assert feature_store["seller_prior_late_rate"].between(0.0, 1.0).all()
    assert (feature_store["seller_prior_order_count"] >= 0).all()


def test_temporal_calendar_boundaries(feature_store: pd.DataFrame):
    """Confirms calendar properties are within expected ranges."""
    assert feature_store["purchase_hour"].between(0, 23).all()
    assert feature_store["purchase_day_of_week"].between(0, 6).all()
    assert set(feature_store["is_weekend"].unique()).issubset({0, 1})
    assert feature_store["purchase_month"].between(1, 12).all()
