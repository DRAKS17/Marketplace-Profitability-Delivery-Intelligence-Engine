"""
Power BI Data Preparation, Mart Views Deployment & Architecture Engine.

Prepares high-performance analytical datasets for Power BI Desktop:
- 1. Merges risk-scored orders with review sentiment into fact_order_intelligence.csv.
- 2. Generates dimensional lookup tables: dim_date.csv, dim_geography.csv, dim_seller_summary.csv, dim_category_summary.csv.
- 3. Deploys optimized SQL views in PostgreSQL mart schema (sql/08_power_bi_views.sql).
- 4. Generates enterprise DAX formula catalog and documentation in docs/power_bi_architecture.md.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from sqlalchemy import text

from src.marketplace_intelligence.database import get_postgres_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Brazilian State to Macro-Region Mapping
MACRO_REGION_MAP = {
    "SP": "Southeast",
    "RJ": "Southeast",
    "MG": "Southeast",
    "ES": "Southeast",
    "PR": "South",
    "SC": "South",
    "RS": "South",
    "BA": "Northeast",
    "PE": "Northeast",
    "CE": "Northeast",
    "MA": "Northeast",
    "PB": "Northeast",
    "RN": "Northeast",
    "AL": "Northeast",
    "SE": "Northeast",
    "PI": "Northeast",
    "DF": "Central-West",
    "GO": "Central-West",
    "MT": "Central-West",
    "MS": "Central-West",
    "AM": "North",
    "PA": "North",
    "RO": "North",
    "AC": "North",
    "TO": "North",
    "AP": "North",
    "RR": "North",
}


class PowerBIExporter:
    """Exports structured dimensional datasets and deploys Power BI mart views."""

    def __init__(
        self,
        processed_dir: Path | str = "data/processed",
        powerbi_dir: Path | str = "data/power_bi",
        docs_dir: Path | str = "docs",
        sql_dir: Path | str = "sql",
    ):
        self.processed_dir = Path(processed_dir)
        self.powerbi_dir = Path(powerbi_dir)
        self.docs_dir = Path(docs_dir)
        self.sql_dir = Path(sql_dir)

        self.powerbi_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    def prepare_and_export_datasets(self) -> dict[str, Path]:
        """Prepares and exports clean dimensional and fact CSVs for Power BI."""
        logger.info("Loading risk-scored orders and enriched reviews...")
        orders_path = self.processed_dir / "orders_risk_scored.parquet"
        reviews_path = self.processed_dir / "order_reviews_enriched.parquet"

        if not orders_path.exists():
            raise FileNotFoundError(f"Missing {orders_path}. Run Phase 13 first.")
        if not reviews_path.exists():
            raise FileNotFoundError(f"Missing {reviews_path}. Run Phase 6 first.")

        df_orders = pd.read_parquet(orders_path)
        df_reviews = pd.read_parquet(reviews_path)

        # Deduplicate reviews to single order grain (take minimum rating / worst feedback)
        rev_order = (
            df_reviews.groupby("order_id")
            .agg(
                review_score=("review_score", "min"),
                csat_category=("csat_category", "first"),
                is_delivery_issue=("is_delivery_issue", "max"),
                is_product_quality_issue=("is_product_quality_issue", "max"),
                is_positive_experience=("is_positive_experience", "max"),
                operational_feedback_tag=("operational_feedback_tag", "first"),
            )
            .reset_index()
        )

        logger.info("Merging orders with review sentiment intelligence...")
        df_fact = pd.merge(df_orders, rev_order, on="order_id", how="left")

        # Macro region mapping
        df_fact["customer_macro_region"] = df_fact["customer_state"].map(MACRO_REGION_MAP).fillna("Other")
        df_fact["seller_macro_region"] = df_fact["seller_state"].map(MACRO_REGION_MAP).fillna("Other")

        # Format dates for Power BI calendar relationships
        df_fact["order_purchase_date"] = pd.to_datetime(df_fact["order_purchase_timestamp"]).dt.date
        df_fact["order_purchase_year_month"] = pd.to_datetime(df_fact["order_purchase_timestamp"]).dt.strftime("%Y-%m")

        # -------------------------------------------------------------
        # 1. Fact Table: fact_order_intelligence.csv
        # -------------------------------------------------------------
        fact_cols = [
            "order_id",
            "customer_id",
            "customer_unique_id",
            "seller_id",
            "primary_product_category",
            "customer_state",
            "customer_macro_region",
            "seller_state",
            "seller_macro_region",
            "order_purchase_timestamp",
            "order_purchase_date",
            "order_purchase_year_month",
            "order_total_item_value",
            "order_total_freight_value",
            "order_total_value",
            "freight_ratio",
            "haversine_distance_km",
            "is_interstate_delivery",
            "predicted_late_probability",
            "delay_risk_score",
            "freight_friction_score",
            "merchant_unreliability_score",
            "route_complexity_score",
            "operational_vulnerability_index",
            "vulnerability_tier",
            "gross_platform_revenue_brl",
            "payment_processing_fee_brl",
            "expected_late_remedy_cost_brl",
            "expected_net_contribution_brl",
            "profitability_tier",
            "strategic_quadrant",
            "estimated_delivery_duration_days",
            "seller_dispatch_duration_hours",
            "carrier_transit_duration_days",
            "delivery_delay_days",
            "is_delivered",
            "is_late_delivery",
            "review_score",
            "csat_category",
            "is_delivery_issue",
            "is_product_quality_issue",
            "is_positive_experience",
            "operational_feedback_tag",
        ]

        fact_export = df_fact[fact_cols].copy()
        fact_path = self.powerbi_dir / "fact_order_intelligence.csv"
        fact_export.to_csv(fact_path, index=False)
        logger.info(f"Exported {len(fact_export):,} rows to {fact_path.resolve()}")

        # -------------------------------------------------------------
        # 2. Dimension: dim_date.csv
        # -------------------------------------------------------------
        min_date = df_fact["order_purchase_date"].min()
        max_date = df_fact["order_purchase_date"].max()
        dates = pd.date_range(min_date, max_date, freq="D")
        df_date = pd.DataFrame({
            "date": dates.date,
            "year": dates.year,
            "quarter": "Q" + dates.quarter.astype(str),
            "month": dates.month,
            "month_name": dates.strftime("%B"),
            "year_month": dates.strftime("%Y-%m"),
            "day": dates.day,
            "day_of_week": dates.day_name(),
            "is_weekend": dates.dayofweek.isin([5, 6]),
        })
        date_path = self.powerbi_dir / "dim_date.csv"
        df_date.to_csv(date_path, index=False)
        logger.info(f"Exported {len(df_date):,} dates to {date_path.resolve()}")

        # -------------------------------------------------------------
        # 3. Dimension: dim_geography.csv
        # -------------------------------------------------------------
        geo_data = []
        for state, region in MACRO_REGION_MAP.items():
            state_orders = df_fact[df_fact["customer_state"] == state]
            geo_data.append({
                "state_code": state,
                "macro_region": region,
                "total_orders": len(state_orders),
                "total_gmv": float(state_orders["order_total_item_value"].sum()),
            })
        df_geo = pd.DataFrame(geo_data)
        geo_path = self.powerbi_dir / "dim_geography.csv"
        df_geo.to_csv(geo_path, index=False)
        logger.info(f"Exported {len(df_geo):,} states to {geo_path.resolve()}")

        # -------------------------------------------------------------
        # 4. Dimension: dim_seller_summary.csv
        # -------------------------------------------------------------
        seller_summary = (
            df_fact.groupby("seller_id")
            .agg(
                total_orders=("order_id", "count"),
                total_gmv=("order_total_item_value", "sum"),
                avg_ovi=("operational_vulnerability_index", "mean"),
                danger_zone_orders=("strategic_quadrant", lambda s: (s.str.startswith("Q2")).sum()),
                crown_jewel_orders=("strategic_quadrant", lambda s: (s.str.startswith("Q1")).sum()),
                actual_late_rate=("is_late_delivery", "mean"),
                avg_csat=("review_score", "mean"),
            )
            .reset_index()
        )
        seller_summary["danger_zone_share_pct"] = (
            seller_summary["danger_zone_orders"] / seller_summary["total_orders"]
        ) * 100.0
        seller_path = self.powerbi_dir / "dim_seller_summary.csv"
        seller_summary.to_csv(seller_path, index=False)
        logger.info(f"Exported {len(seller_summary):,} sellers to {seller_path.resolve()}")

        # -------------------------------------------------------------
        # 5. Dimension: dim_category_summary.csv
        # -------------------------------------------------------------
        cat_summary = (
            df_fact.groupby("primary_product_category")
            .agg(
                total_orders=("order_id", "count"),
                total_gmv=("order_total_item_value", "sum"),
                total_net_cm=("expected_net_contribution_brl", "sum"),
                avg_freight_ratio=("freight_ratio", "mean"),
                avg_ovi=("operational_vulnerability_index", "mean"),
                actual_late_rate=("is_late_delivery", "mean"),
                avg_csat=("review_score", "mean"),
            )
            .reset_index()
        )
        cat_path = self.powerbi_dir / "dim_category_summary.csv"
        cat_summary.to_csv(cat_path, index=False)
        logger.info(f"Exported {len(cat_summary):,} categories to {cat_path.resolve()}")

        return {
            "fact": fact_path,
            "date": date_path,
            "geography": geo_path,
            "seller": seller_path,
            "category": cat_path,
        }

    def deploy_postgres_views(self) -> None:
        """Executes sql/08_power_bi_views.sql in PostgreSQL marketplace_analytics database."""
        logger.info("Deploying Power BI optimized views in PostgreSQL mart schema...")
        engine = get_postgres_engine()
        views_sql = (self.sql_dir / "08_power_bi_views.sql").read_text(encoding="utf-8")

        with engine.connect() as conn:
            statements = [stmt.strip() for stmt in views_sql.split(";") if stmt.strip()]
            for stmt in statements:
                conn.execute(text(stmt))

        with engine.connect() as conn:
            v1_count = conn.execute(text("SELECT COUNT(*) FROM mart.view_powerbi_orders;")).scalar()
            v2_count = conn.execute(text("SELECT COUNT(*) FROM mart.view_powerbi_monthly_trend;")).scalar()
            v3_count = conn.execute(text("SELECT COUNT(*) FROM mart.view_powerbi_regional_logistics;")).scalar()

            logger.info("Power BI Views deployed and verified in PostgreSQL:")
            logger.info(f"  - mart.view_powerbi_orders: {v1_count:,} rows")
            logger.info(f"  - mart.view_powerbi_monthly_trend: {v2_count:,} monthly cohorts")
            logger.info(f"  - mart.view_powerbi_regional_logistics: {v3_count:,} state profiles")

    def generate_architecture_doc(self) -> Path:
        """Authors full architectural and DAX specification guide in docs/power_bi_architecture.md."""
        doc_path = self.docs_dir / "power_bi_architecture.md"
        logger.info(f"Generating Power BI Architecture Guide at {doc_path}...")

        lines = [
            "# Power BI Executive Dashboard Architecture & DAX Specification",
            "",
            "## 1. Executive Overview & Data Model Architecture",
            "This document establishes the enterprise Power BI reporting architecture for the **Marketplace Profitability & Delivery Intelligence Engine**.",
            "",
            "The data model follows the classic **Kimball Star Schema** pattern with strict 1-to-many single-direction filtering:",
            "",
            "```text",
            "               +-----------------------+",
            "               |       dim_date        |",
            "               +-----------------------+",
            "                           │ 1",
            "                           │",
            "                           ▼ *",
            "+--------------------+   +------------------------------------+   +-------------------------+",
            "|   dim_geography    |──▶|      fact_order_intelligence       |◀──|   dim_seller_summary    |",
            "+--------------------+ 1 |     (99,441 Order Grain Rows)      | 1 +-------------------------+",
            "                         +------------------------------------+",
            "                                           ▲",
            "                                           │ *",
            "                                           │ 1",
            "                               +-------------------------+",
            "                               |  dim_category_summary   |",
            "                               +-------------------------+",
            "```",
            "",
            "---",
            "",
            "## 2. Enterprise DAX Measures Library",
            "All metrics are defined as explicit DAX measures housed in a dedicated `_Measures` table organized into functional display folders:",
            "",
            "### Folder: `01. Financial & Commercial`",
            "```dax",
            "-- Gross Merchandise Value (GMV)",
            "Total GMV = SUM(fact_order_intelligence[order_total_item_value])",
            "",
            "-- Total Shipping Fees Charged",
            "Total Freight = SUM(fact_order_intelligence[order_total_freight_value])",
            "",
            "-- Total Order Value (GMV + Freight)",
            "Total Order Value = SUM(fact_order_intelligence[order_total_value])",
            "",
            "-- Platform Gross Commission Revenue (12% Take-Rate on GMV)",
            "Gross Revenue = SUM(fact_order_intelligence[gross_platform_revenue_brl])",
            "",
            "-- Payment Processing Costs",
            "Payment Processing Cost = SUM(fact_order_intelligence[payment_processing_fee_brl])",
            "",
            "-- Expected Late Remedy Liability ($20 per expected incident)",
            "Expected Remedy Cost = SUM(fact_order_intelligence[expected_late_remedy_cost_brl])",
            "",
            "-- Platform Net Contribution Margin",
            "Net Contribution Margin = SUM(fact_order_intelligence[expected_net_contribution_brl])",
            "",
            "-- Effective Platform Take-Rate (%)",
            "Effective Take-Rate Pct = ",
            "DIVIDE([Net Contribution Margin], [Total GMV], 0) * 100",
            "",
            "-- Average Order Value (AOV)",
            "Average Order Value = DIVIDE([Total GMV], [Total Orders], 0)",
            "```",
            "",
            "### Folder: `02. Logistics & Delivery Performance`",
            "```dax",
            "-- Total Orders",
            "Total Orders = COUNTROWS(fact_order_intelligence)",
            "",
            "-- Delivered Orders",
            "Delivered Orders = ",
            "CALCULATE(COUNTROWS(fact_order_intelligence), fact_order_intelligence[is_delivered] = TRUE)",
            "",
            "-- Late Delivery Count",
            "Late Delivery Orders = ",
            "CALCULATE(COUNTROWS(fact_order_intelligence), fact_order_intelligence[is_late_delivery] = 1)",
            "",
            "-- Late Delivery Rate (%)",
            "Late Delivery Rate Pct = ",
            "DIVIDE([Late Delivery Orders], [Delivered Orders], 0) * 100",
            "",
            "-- On-Time Delivery Rate (%)",
            "On-Time Delivery Rate Pct = 100 - [Late Delivery Rate Pct]",
            "",
            "-- Average Carrier Transit Duration (Days)",
            "Avg Carrier Transit Days = AVERAGE(fact_order_intelligence[carrier_transit_duration_days])",
            "",
            "-- Average Seller Dispatch Latency (Hours)",
            "Avg Seller Dispatch Hours = AVERAGE(fact_order_intelligence[seller_dispatch_duration_hours])",
            "",
            "-- Average Delivery Delay (Days)",
            "Avg Delivery Delay Days = AVERAGE(fact_order_intelligence[delivery_delay_days])",
            "```",
            "",
            "### Folder: `03. Risk & Strategic Quadrants`",
            "```dax",
            "-- Average Operational Vulnerability Index (OVI)",
            "Avg OVI = AVERAGE(fact_order_intelligence[operational_vulnerability_index])",
            "",
            "-- Danger Zone (Q2) GMV",
            "Danger Zone GMV = ",
            "CALCULATE([Total GMV], LEFT(fact_order_intelligence[strategic_quadrant], 2) = \"Q2\")",
            "",
            "-- Danger Zone GMV Share (%)",
            "Danger Zone GMV Share Pct = ",
            "DIVIDE([Danger Zone GMV], [Total GMV], 0) * 100",
            "",
            "-- Crown Jewels (Q1) GMV Share (%)",
            "Crown Jewels GMV Share Pct = ",
            "DIVIDE(CALCULATE([Total GMV], LEFT(fact_order_intelligence[strategic_quadrant], 2) = \"Q1\"), [Total GMV], 0) * 100",
            "",
            "-- High Vulnerability Orders (OVI >= 50)",
            "High Vulnerability Orders = ",
            "CALCULATE(COUNTROWS(fact_order_intelligence), fact_order_intelligence[operational_vulnerability_index] >= 50)",
            "```",
            "",
            "### Folder: `04. Customer Experience (CSAT)`",
            "```dax",
            "-- Average Customer Rating (Stars)",
            "Average CSAT = AVERAGE(fact_order_intelligence[review_score])",
            "",
            "-- Total Reviews Logged",
            "Total Reviews = COUNT(fact_order_intelligence[review_score])",
            "",
            "-- Negative Review Count (1-2 Stars)",
            "Negative Reviews = ",
            "CALCULATE(COUNTROWS(fact_order_intelligence), fact_order_intelligence[review_score] IN {1, 2})",
            "",
            "-- Negative Review Share (%)",
            "Negative Review Share Pct = DIVIDE([Negative Reviews], [Total Reviews], 0) * 100",
            "",
            "-- Delivery Issue Complaint Rate (%)",
            "Delivery Issue Rate Pct = ",
            "DIVIDE(CALCULATE(COUNTROWS(fact_order_intelligence), fact_order_intelligence[is_delivery_issue] = TRUE), [Total Reviews], 0) * 100",
            "```",
            "",
            "---",
            "",
            "## 3. Four-Page Dashboard Blueprints & Visual Layout",
            "",
            "### Page 1: Executive Overview & Commercial Health",
            "- **Header KPI Cards**: `Total GMV` ($13.59M), `Total Orders` (99.4k), `Net Contribution Margin` ($1.17M), `Effective Take-Rate` (8.77%), `Avg CSAT` (4.09 ★).",
            "- **Visual 1 (Area/Line Chart)**: Monthly GMV vs Net Contribution Margin over time with dynamic Take-Rate line.",
            "- **Visual 2 (2x2 Matrix / Scatter)**: The Strategic Profit-Risk Matrix (X-Axis: Expected Net CM, Y-Axis: OVI, Bubble Size: GMV, Color: Quadrant).",
            "- **Visual 3 (Horizontal Bar Chart)**: Top 10 Product Categories by Net Cash Contribution Margin.",
            "- **Visual 4 (Donut Chart)**: GMV Concentration by Strategic Quadrant (showing 54.6% Crown Jewels vs 13.6% Danger Zone).",
            "",
            "### Page 2: Delivery Intelligence & Logistics Operations",
            "- **Header KPI Cards**: `Late Delivery Rate` (8.11%), `On-Time Rate` (91.89%), `Avg Transit Time` (12.1 days), `Avg Dispatch Latency` (79.2 hours).",
            "- **Visual 1 (Dual-Axis Combo Chart)**: Carrier Transit Duration (Days) vs Seller Dispatch Hours by Destination State.",
            "- **Visual 2 (Choropleth Map / Shape Map)**: Brazil State Late Delivery Rate (%) heatmap (visualizing high delay risk in Northern/Northeastern corridors).",
            "- **Visual 3 (Histogram / Column Chart)**: Delivery Delay Distribution in Days (clipped from -20 to +20 days with vertical SLA target marker).",
            "- **Visual 4 (Decomposition Tree)**: Delivery SLA Failure root-cause breakdown: Interstate vs Intrastate $\\rightarrow$ Customer Macro Region $\\rightarrow$ Seller Late Dispatch.",
            "",
            "### Page 3: Customer Experience & Sentiment Intelligence",
            "- **Header KPI Cards**: `Avg CSAT` (4.09), `Promoter Share` (77.2% 4-5 stars), `Detractor Share` (14.2% 1-2 stars), `Delivery Complaints` (5,245 tickets).",
            "- **Visual 1 (Box Plot / Scatter)**: Customer Rating vs Delivery Delay (demonstrating the collapse from 4.29 to 2.57 stars when delay > 0 days).",
            "- **Visual 2 (Stacked Bar Chart)**: CSAT Rating distribution (1 to 5 stars) split by Delivery Timeliness (On-Time vs Late).",
            "- **Visual 3 (Treemap / Bar Chart)**: NLP Issue Category breakdown (`delivery_issue` vs `product_quality_issue` vs `positive_experience`).",
            "- **Visual 4 (Table Visual)**: Recent negative customer feedback verbatim with sentiment classification and seller attribution.",
            "",
            "### Page 4: Merchant & Seller Risk Audit",
            "- **Header KPI Cards**: `Total Active Sellers` (3,095), `High-Risk Sellers` (312), `Danger Zone Exposure GMV` ($1.85M), `Avg Seller Late Rate` (8.3%).",
            "- **Visual 1 (Scatter Plot)**: Seller Order Volume vs Historical Delay Rate (log scale, identifying chronic operational offenders).",
            "- **Visual 2 (Lorenz / Pareto Curve)**: Cumulative Merchant GMV concentration (confirming top 20% of merchants generate 84% of platform GMV).",
            "- **Visual 3 (Audit Table Visual)**: Top 20 Merchants with highest Q2 Danger Zone GMV exposure, with columns for `Total Orders`, `GMV`, `Danger Zone Orders`, `Danger Zone %`, `Avg Late Rate`, and `Probation Status Flag`.",
            "",
            "---",
            "",
            "## 4. Visual Design System & Color Palette",
            "",
            "| Role | Color Name | Hex Code | Usage |",
            "|---|---|---|---|",
            "| **Primary Brand** | Slate Navy | `#1E293B` | Titles, card headers, primary text, navigation bar |",
            "| **Secondary Accent** | Royal Blue | `#2563EB` | GMV trends, Q1 Crown Jewels visuals, primary bars |",
            "| **Risk / Failure** | Crimson Red | `#DC2626` | Late deliveries, Q2 Danger Zone, 1-2 star CSAT alerts |",
            "| **Warning / Moderate** | Amber Orange | `#F59E0B` | Q3 Value Drains, 3-star CSAT, moderate vulnerability |",
            "| **Success / Safe** | Emerald Green | `#10B981` | On-time deliveries, Q4 Workhorses, 5-star CSAT |",
            "| **Neutral Canvas** | Ice White | `#F8FAFC` | Page background canvas, card containers |",
            "",
            "---",
            "",
            "## 5. How to Connect in Power BI Desktop",
            "",
            "### Method A: High-Performance CSV Import (Recommended for offline / portable `.pbix`)",
            "1. Open **Power BI Desktop**.",
            "2. Click **Get Data** $\\rightarrow$ **Text/CSV**.",
            "3. Select `data/power_bi/fact_order_intelligence.csv`.",
            "4. Repeat for `dim_date.csv`, `dim_geography.csv`, `dim_seller_summary.csv`, and `dim_category_summary.csv`.",
            "5. Navigate to **Model View** and verify 1-to-many single-direction relationships from dimensions to fact table on keys (`order_purchase_date` $\\rightarrow$ `date`, `customer_state` $\\rightarrow$ `state_code`, `seller_id`, `primary_product_category`).",
            "",
            "### Method B: PostgreSQL Direct Connection",
            "1. In Power BI Desktop, select **Get Data** $\\rightarrow$ **PostgreSQL Database**.",
            "2. Server: `localhost:5432` | Database: `marketplace_analytics`.",
            "3. Select Data Connectivity mode: **Import** (or **DirectQuery**).",
            "4. Check views in schema `mart`: `mart.view_powerbi_orders`, `mart.view_powerbi_monthly_trend`, and `mart.view_powerbi_regional_logistics`.",
        ]

        with open(doc_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return doc_path

    def run_all(self) -> dict[str, any]:
        """Executes full Power BI data export, SQL view deployment, and architecture authoring."""
        exported_files = self.prepare_and_export_datasets()
        self.deploy_postgres_views()
        doc_path = self.generate_architecture_doc()

        return {
            "exported_files": exported_files,
            "architecture_doc": doc_path,
        }


if __name__ == "__main__":
    exporter = PowerBIExporter()
    exporter.run_all()
