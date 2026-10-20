"""
Automated Validation Tests for Data Cleaning.

Tests verify:
1. Immutability of raw source files.
2. Spatial deduplication and coordinate bounding for geolocation.
3. Preservation of structural nulls in orders (no false deliveries).
4. Category translation mapping and imputation.
5. Financial and installment data quality assertions.
6. Review score boundaries and comment indicators.
"""

from pathlib import Path

import pandas as pd
import pytest

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

pytestmark = pytest.mark.skipif(
    not (RAW_DIR / "olist_orders_dataset.csv").exists()
    or not (PROCESSED_DIR / "geolocation_cleaned.parquet").exists(),
    reason="Raw or cleaned datasets not present in environment",
)


def test_raw_data_remains_intact():
    """Confirms raw source files were not modified or overwritten."""
    raw_files = list(RAW_DIR.glob("*.csv"))
    assert len(raw_files) == 9, "Expected 9 raw source CSV files in data/raw"

    # Check key files exist and are non-empty
    orders_raw = RAW_DIR / "olist_orders_dataset.csv"
    assert orders_raw.exists()
    assert orders_raw.stat().st_size > 15 * 1024 * 1024, (
        "Raw orders file was unexpectedly modified or truncated."
    )


def test_geolocation_cleaning():
    """Confirms geolocation is deduplicated to unique postal centroids within Brazil bounds."""
    df = pd.read_parquet(PROCESSED_DIR / "geolocation_cleaned.parquet")

    # 1. Zip code prefix must be strictly unique
    assert df["geolocation_zip_code_prefix"].is_unique, (
        "Cleaned geolocation must have 1 row per zip prefix."
    )

    # 2. Coordinates must reside within valid Brazilian territory
    assert (df["geolocation_lat"] >= -34.0).all() and (
        df["geolocation_lat"] <= 6.0
    ).all()
    assert (df["geolocation_lng"] >= -74.0).all() and (
        df["geolocation_lng"] <= -34.0
    ).all()


def test_orders_cleaning_and_structural_nulls():
    """Confirms delivery timestamps are proper datetimes and structural nulls are preserved."""
    df = pd.read_parquet(PROCESSED_DIR / "orders_cleaned.parquet")
    assert len(df) == 99441
    assert df["order_id"].is_unique

    # Verify datetime dtype
    assert pd.api.types.is_datetime64_any_dtype(df["order_purchase_timestamp"])
    assert pd.api.types.is_datetime64_any_dtype(df["order_delivered_customer_date"])

    # Crucial test: 2,965 undelivered/canceled orders MUST remain null (not zero or median filled)
    null_deliveries = df["order_delivered_customer_date"].isna().sum()
    assert null_deliveries == 2965, (
        f"Expected exactly 2,965 structural delivery nulls, found {null_deliveries}."
    )
    assert "is_chronologically_valid" in df.columns


def test_products_cleaning_and_translation():
    """Confirms category translation mapping and imputation of unknown categories."""
    df = pd.read_parquet(PROCESSED_DIR / "products_cleaned.parquet")
    assert len(df) == 32951
    assert df["product_id"].is_unique

    # Verify no null category translations remain
    assert df["product_category_name_english"].isna().sum() == 0
    assert "others" in df["product_category_name_english"].values
    assert (
        "small_appliances_food_preparation"
        in df["product_category_name_english"].values
    )
    assert "pc_gamer" in df["product_category_name_english"].values


def test_order_items_cleaning():
    """Confirms order item pricing, freight values, and promotional shipping flags."""
    df = pd.read_parquet(PROCESSED_DIR / "order_items_cleaned.parquet")
    assert len(df) == 112650
    assert (df["price"] > 0).all(), "Found items with non-positive prices."
    assert (df["freight_value"] >= 0).all(), "Found negative freight values."
    assert "is_free_shipping" in df.columns
    assert (df["is_free_shipping"] == (df["freight_value"] == 0.0)).all()


def test_order_payments_cleaning():
    """Confirms installment corrections and voided payment transaction flags."""
    df = pd.read_parquet(PROCESSED_DIR / "order_payments_cleaned.parquet")
    assert len(df) == 103886

    # Zero installments should be resolved
    assert (df["payment_installments"] > 0).all(), (
        "Found payment records with 0 installments."
    )
    assert "is_voided_payment" in df.columns


def test_order_reviews_cleaning():
    """Confirms review scores are bounded [1, 5] and comment indicators exist."""
    df = pd.read_parquet(PROCESSED_DIR / "order_reviews_cleaned.parquet")
    assert df["review_score"].between(1, 5).all(), (
        "Review scores outside valid 1-5 range."
    )
    assert "has_comment_title" in df.columns
    assert "has_comment_message" in df.columns
