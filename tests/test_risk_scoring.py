"""
Unit and regression tests for Business Risk Layer and Risk Scoring Engine.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from src.marketplace_intelligence.database import get_postgres_engine
from src.marketplace_intelligence.risk_scoring import RiskScoringEngine

PROCESSED_DIR = Path("data/processed")
DOCS_DIR = Path("docs")
MODELS_DIR = Path("models")
SQL_DIR = Path("sql")

pytestmark = pytest.mark.skipif(
    not (PROCESSED_DIR / "orders_risk_scored.parquet").exists(),
    reason="orders_risk_scored.parquet not present in environment",
)


@pytest.fixture(scope="module")
def engine():
    return RiskScoringEngine(
        processed_dir=PROCESSED_DIR,
        models_dir=MODELS_DIR,
        docs_dir=DOCS_DIR,
        sql_dir=SQL_DIR,
    )


@pytest.fixture(scope="module")
def scored_df():
    parquet_path = PROCESSED_DIR / "orders_risk_scored.parquet"
    assert parquet_path.exists(), (
        "orders_risk_scored.parquet not found. Run risk_scoring.py first."
    )
    return pd.read_parquet(parquet_path)


def test_risk_scoring_bounds(scored_df):
    """Verifies that OVI and its components stay strictly within mathematical theoretical bounds."""
    # OVI bounds
    assert (scored_df["operational_vulnerability_index"] >= 0.0).all()
    assert (scored_df["operational_vulnerability_index"] <= 100.0).all()

    # Component bounds
    assert (scored_df["delay_risk_score"] >= 0.0).all()
    assert (scored_df["delay_risk_score"] <= 40.001).all()

    assert (scored_df["freight_friction_score"] >= 0.0).all()
    assert (scored_df["freight_friction_score"] <= 25.001).all()

    assert (scored_df["merchant_unreliability_score"] >= 0.0).all()
    assert (scored_df["merchant_unreliability_score"] <= 20.001).all()

    assert (scored_df["route_complexity_score"] >= 0.0).all()
    assert (scored_df["route_complexity_score"] <= 15.001).all()

    # OVI component sum reconciliation
    comp_sum = (
        scored_df["delay_risk_score"]
        + scored_df["freight_friction_score"]
        + scored_df["merchant_unreliability_score"]
        + scored_df["route_complexity_score"]
    )
    np.testing.assert_allclose(
        scored_df["operational_vulnerability_index"], comp_sum, atol=0.05
    )


def test_expected_contribution_arithmetic(scored_df):
    """Verifies that expected contribution margin arithmetic holds exactly."""
    expected_calc = (
        scored_df["gross_platform_revenue_brl"]
        - scored_df["payment_processing_fee_brl"]
        - scored_df["expected_late_remedy_cost_brl"]
    )
    np.testing.assert_allclose(
        scored_df["expected_net_contribution_brl"], expected_calc, atol=0.02
    )


def test_strategic_quadrant_coverage(scored_df):
    """Asserts that all 4 strategic quadrants are populated without nulls."""
    assert scored_df["strategic_quadrant"].notna().all()

    quadrants = set(scored_df["strategic_quadrant"].unique())
    expected_quadrants = {
        "Q1: Crown Jewels (High Profit, Low Risk)",
        "Q2: Danger Zone (High Profit, High Risk)",
        "Q3: Value Drains (Low Profit, High Risk)",
        "Q4: Steady Workhorses (Low Profit, Low Risk)",
    }
    assert quadrants == expected_quadrants

    # Q1 Crown Jewels must represent the majority of GMV (> 50%)
    q1_gmv = scored_df[scored_df["strategic_quadrant"].str.startswith("Q1")][
        "order_total_item_value"
    ].sum()
    total_gmv = scored_df["order_total_item_value"].sum()
    assert (q1_gmv / total_gmv) > 0.50


def test_exported_parquet_and_csv_artifacts():
    """Verifies exported file artifacts existence and row counts."""
    parquet_path = PROCESSED_DIR / "orders_risk_scored.parquet"
    csv_path = PROCESSED_DIR / "orders_risk_scored.csv"

    assert parquet_path.exists()
    assert csv_path.exists()

    df_p = pd.read_parquet(parquet_path)
    assert len(df_p) == 99441
    assert "operational_vulnerability_index" in df_p.columns
    assert "strategic_quadrant" in df_p.columns


def test_database_mart_integration():
    """Verifies PostgreSQL mart.order_risk_profile and executive summary view."""
    db_engine = get_postgres_engine()
    with db_engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM mart.order_risk_profile;")
        ).scalar()
        assert count == 99441

        # Check executive summary view
        view_rows = conn.execute(
            text(
                "SELECT strategic_quadrant, total_orders, gmv_share_pct FROM mart.view_quadrant_executive_summary;"
            )
        ).fetchall()
        assert len(view_rows) == 4
        total_share = sum(r[2] for r in view_rows)
        assert pytest.approx(float(total_share), abs=0.1) == 100.0
