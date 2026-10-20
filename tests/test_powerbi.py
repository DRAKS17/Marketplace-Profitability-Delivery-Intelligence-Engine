"""
Unit and regression tests for Power BI Data Layer and Architecture Specification.
"""

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

from src.marketplace_intelligence.database import get_postgres_engine
from src.marketplace_intelligence.powerbi_export import PowerBIExporter

POWERBI_DIR = Path("data/power_bi")
PROCESSED_DIR = Path("data/processed")
DOCS_DIR = Path("docs")
SQL_DIR = Path("sql")

pytestmark = pytest.mark.skipif(
    not (POWERBI_DIR / "fact_order_intelligence.csv").exists(),
    reason="Power BI extract CSVs not present in environment",
)


@pytest.fixture(scope="module")
def exporter():
    return PowerBIExporter(
        processed_dir=PROCESSED_DIR,
        powerbi_dir=POWERBI_DIR,
        docs_dir=DOCS_DIR,
        sql_dir=SQL_DIR,
    )


def test_powerbi_csv_files_exist_and_populated():
    """Validates existence and row counts of all 5 Power BI import CSVs."""
    expected_files = [
        ("fact_order_intelligence.csv", 99441),
        ("dim_date.csv", 700),
        ("dim_geography.csv", 27),
        ("dim_seller_summary.csv", 3000),
        ("dim_category_summary.csv", 70),
    ]

    for filename, min_expected_rows in expected_files:
        file_path = POWERBI_DIR / filename
        assert file_path.exists(), f"Missing required Power BI CSV: {filename}"
        df = pd.read_csv(file_path)
        assert len(df) >= min_expected_rows, (
            f"{filename} row count {len(df)} < expected {min_expected_rows}"
        )


def test_fact_order_intelligence_schema():
    """Validates schema and data completeness of fact_order_intelligence.csv."""
    fact_path = POWERBI_DIR / "fact_order_intelligence.csv"
    df = pd.read_csv(fact_path)

    required_cols = [
        "order_id",
        "customer_id",
        "seller_id",
        "primary_product_category",
        "customer_state",
        "customer_macro_region",
        "order_total_item_value",
        "order_total_freight_value",
        "operational_vulnerability_index",
        "strategic_quadrant",
        "gross_platform_revenue_brl",
        "expected_net_contribution_brl",
        "review_score",
        "csat_category",
    ]
    for col in required_cols:
        assert col in df.columns, (
            f"Missing required column '{col}' in fact_order_intelligence.csv"
        )

    # Macro regions must be 100% mapped without nulls
    assert df["customer_macro_region"].notna().all()
    valid_regions = {
        "Southeast",
        "South",
        "Northeast",
        "Central-West",
        "North",
        "Other",
    }
    assert set(df["customer_macro_region"].unique()).issubset(valid_regions)


def test_postgres_powerbi_views():
    """Verifies that all 3 PostgreSQL views in mart schema query successfully."""
    db_engine = get_postgres_engine()
    with db_engine.connect() as conn:
        # 1. Orders view
        v1_count = conn.execute(
            text("SELECT COUNT(*) FROM mart.view_powerbi_orders;")
        ).scalar()
        assert v1_count == 99441

        # 2. Monthly trend view
        v2_rows = conn.execute(
            text(
                "SELECT year_month, total_orders, total_gmv_brl FROM mart.view_powerbi_monthly_trend;"
            )
        ).fetchall()
        assert len(v2_rows) >= 20

        # 3. Regional logistics view
        v3_rows = conn.execute(
            text(
                "SELECT customer_state, total_orders, avg_ovi FROM mart.view_powerbi_regional_logistics;"
            )
        ).fetchall()
        assert len(v3_rows) == 27


def test_powerbi_architecture_doc():
    """Verifies existence and section headers of docs/power_bi_architecture.md."""
    doc_path = DOCS_DIR / "power_bi_architecture.md"
    assert doc_path.exists()
    content = doc_path.read_text(encoding="utf-8")

    assert "## 1. Executive Overview & Data Model Architecture" in content
    assert "## 2. Enterprise DAX Measures Library" in content
    assert "## 3. Four-Page Dashboard Blueprints & Visual Layout" in content
    assert "## 4. Visual Design System & Color Palette" in content
    assert "Total GMV = SUM(" in content
    assert "Net Contribution Margin = SUM(" in content
    assert "Late Delivery Rate Pct =" in content
