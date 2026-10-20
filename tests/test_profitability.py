"""
Unit and regression tests for Marketplace Profitability & Commercial Scenario Engine.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.marketplace_intelligence.profitability import ProfitabilityModeler

DOCS_DIR = Path("docs")
PROCESSED_DIR = Path("data/processed")

pytestmark = pytest.mark.skipif(
    not (PROCESSED_DIR / "order_features.parquet").exists()
    or not (PROCESSED_DIR / "order_reviews_enriched.parquet").exists(),
    reason="Processed data files not present in environment",
)


@pytest.fixture(scope="module")
def modeler():
    return ProfitabilityModeler(processed_dir=PROCESSED_DIR, docs_dir=DOCS_DIR)


@pytest.fixture(scope="module")
def delivered_df(modeler):
    orders = pd.read_parquet(modeler.processed_dir / "order_features.parquet")
    reviews = pd.read_parquet(modeler.processed_dir / "order_reviews_enriched.parquet")
    df = pd.merge(
        orders,
        reviews[["order_id", "is_delivery_issue", "is_product_quality_issue"]],
        on="order_id",
        how="left",
    )
    df["is_delivery_issue"] = df["is_delivery_issue"].fillna(False)
    df["is_product_quality_issue"] = df["is_product_quality_issue"].fillna(False)
    df["has_formal_complaint"] = (
        df["is_delivery_issue"] | df["is_product_quality_issue"]
    )
    return df[df["is_delivered"]].copy()


def test_profitability_report_generation(modeler):
    """Verifies that the markdown report is generated and contains all standard sections."""
    report_path = modeler.run_all_profitability()
    assert report_path.exists()
    assert report_path.is_file()

    content = report_path.read_text(encoding="utf-8")
    assert "## 1. Macro Marketplace P&L Scenarios" in content
    assert "## 2. 2D Sensitivity Analysis" in content
    assert "## 3. Product Category Profitability Ranking" in content
    assert (
        "## 4. The 'Late GMV = Lost Revenue' Myth vs True Commercial Exposure"
        in content
    )
    assert "health_beauty" in content


def test_macro_scenarios_hierarchy(modeler, delivered_df):
    """Verifies that scenario margins follow economic logic (Optimistic > Base > Conservative)."""
    results = modeler._compute_macro_scenarios(delivered_df)

    base = results["Base Case (Realistic)"]
    conservative = results["Conservative (Stress Test)"]
    optimistic = results["Optimistic (Growth Scale)"]

    # Monotonic ordering of net contribution
    assert optimistic["net_contribution_margin"] > base["net_contribution_margin"]
    assert base["net_contribution_margin"] > conservative["net_contribution_margin"]

    # Bounds on net take-rate (all positive, realistic e-commerce range)
    for res in results.values():
        assert 4.0 <= res["net_take_rate_pct"] <= 15.0
        assert res["total_variable_expenses"] > 0
        assert res["platform_revenue"] > res["total_variable_expenses"]


def test_sensitivity_matrix_structure(modeler, delivered_df):
    """Validates 2D sensitivity grid shape and column headers."""
    matrix = modeler._compute_sensitivity_matrix(delivered_df)

    assert len(matrix) == 4  # 10%, 12%, 14%, 16%
    assert list(matrix.columns) == [
        "Commission Rate",
        "$10 Voucher",
        "$15 Voucher",
        "$20 Voucher",
        "$25 Voucher",
        "$30 Voucher",
    ]


def test_category_pnl_consistency(modeler, delivered_df):
    """Ensures category P&L arithmetic holds exactly."""
    base_sc = modeler.scenarios["Base Case (Realistic)"]
    cat_pnl = modeler._compute_category_pnl(delivered_df, base_sc)

    assert len(cat_pnl) > 0
    for _, row in cat_pnl.iterrows():
        # Contribution margin = revenue - expenses
        expected_cm = row["commission_rev"] - row["total_expenses"]
        assert pytest.approx(row["net_contribution_margin"], rel=1e-5) == expected_cm
        # Net take rate calculation
        expected_rate = (row["net_contribution_margin"] / row["gmv"]) * 100.0
        assert pytest.approx(row["net_take_rate_pct"], rel=1e-5) == expected_rate


def test_commercial_exposure_metrics(modeler, delivered_df):
    """Tests accuracy of late delivery commercial exposure calculations."""
    exposure = modeler._evaluate_commercial_exposure(delivered_df)

    assert exposure["late_order_count"] > 0
    assert exposure["late_gmv_associated"] > 0
    assert exposure["late_gmv_associated"] < exposure["total_delivered_gmv"]
    # Direct operational costs must equal voucher + support
    assert exposure["total_direct_operational_exposure"] == (
        exposure["direct_voucher_remedy_cost"] + exposure["direct_support_cost"]
    )
    # The platform still netted positive cash on late orders
    assert exposure["net_platform_cash_retained_on_late"] > 0
