"""
Feature Engineering and Analytical Mart Generation Module.

Generates comprehensive order-level feature store from cleaned processed datasets:
- Financial & basket complexity metrics (GMV, freight ratio, item counts).
- Physical cargo metrics (weight, cubic volume, primary category).
- Payment characteristics (primary tender, max installments, tender splits).
- Spatial logistics metrics (interstate flags, Haversine distance in km).
- Leakage-free historical performance (expanding cumulative seller late delivery rates).
- Calendar and temporal features.
- Fulfillment operational durations (promised SLA window, seller processing time).
- Explicit target variables (is_late_delivery, delivery_delay_days).
- Exports feature store to data/processed/order_features.parquet and CSV.
- Generates exhaustive feature dictionary in docs/feature_dictionary.md.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def haversine_distance(
    lat1: pd.Series, lon1: pd.Series, lat2: pd.Series, lon2: pd.Series
) -> pd.Series:
    """Calculates great-circle distance between two GPS points in kilometers using the Haversine formula."""
    r_earth = 6371.0  # Earth radius in kilometers

    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)

    a = (
        np.sin(delta_phi / 2.0) ** 2
        + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return r_earth * c


class FeatureEngineer:
    """Constructs order-grain analytical and predictive feature stores."""

    def __init__(
        self,
        processed_dir: Path | str = "data/processed",
        docs_dir: Path | str = "docs",
    ):
        self.processed_dir = Path(processed_dir)
        self.docs_dir = Path(docs_dir)
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    def build_feature_store(self) -> pd.DataFrame:
        """Executes full feature engineering pipeline and exports order-level feature store."""
        logger.info("Loading cleaned processed tables for feature engineering...")

        orders = pd.read_parquet(self.processed_dir / "orders_cleaned.parquet")
        items = pd.read_parquet(self.processed_dir / "order_items_cleaned.parquet")
        payments = pd.read_parquet(
            self.processed_dir / "order_payments_cleaned.parquet"
        )
        products = pd.read_parquet(self.processed_dir / "products_cleaned.parquet")
        customers = pd.read_parquet(self.processed_dir / "customers_cleaned.parquet")
        sellers = pd.read_parquet(self.processed_dir / "sellers_cleaned.parquet")
        geo = pd.read_parquet(self.processed_dir / "geolocation_cleaned.parquet")

        logger.info(
            "1. Engineering order item, basket, and product physical features..."
        )
        item_features = self._engineer_item_features(items, products)

        logger.info("2. Engineering payment method and financing features...")
        payment_features = self._engineer_payment_features(payments)

        logger.info("3. Assembling base order table and customer attributes...")
        base = pd.merge(orders, customers, on="customer_id", how="left")
        base = pd.merge(base, item_features, on="order_id", how="left")
        base = pd.merge(base, payment_features, on="order_id", how="left")

        # Impute missing items/payments for canceled orders (e.g. orders canceled prior to itemization)
        base["order_item_count"] = base["order_item_count"].fillna(0).astype(int)
        base["order_total_item_value"] = base["order_total_item_value"].fillna(0.0)
        base["order_total_freight_value"] = base["order_total_freight_value"].fillna(
            0.0
        )
        base["order_total_value"] = (
            base["order_total_item_value"] + base["order_total_freight_value"]
        )
        base["freight_ratio"] = np.where(
            base["order_total_value"] > 0,
            base["order_total_freight_value"] / base["order_total_value"],
            0.0,
        )
        base["is_multi_seller"] = (
            base["order_unique_seller_count"].fillna(0) > 1
        ).astype(int)

        logger.info("4. Attaching seller location and calculating spatial distances...")
        base = self._attach_spatial_features(base, sellers, geo)

        logger.info(
            "5. Engineering temporal, calendar, and operational SLA duration features..."
        )
        base = self._engineer_temporal_features(base)

        logger.info(
            "6. Calculating expanding historical seller performance without future leakage..."
        )
        base = self._engineer_historical_seller_performance(base)

        logger.info("7. Constructing ground-truth late delivery target variables...")
        base = self._construct_target_variables(base)

        # Export features
        output_parquet = self.processed_dir / "order_features.parquet"
        output_csv = self.processed_dir / "order_features.csv"
        base.to_parquet(output_parquet, index=False)
        base.to_csv(output_csv, index=False)
        logger.info(
            f"Order feature store exported to {output_parquet.name} ({len(base):,} rows, {len(base.columns)} features)"
        )

        # Generate documentation
        self._generate_feature_dictionary(base)
        return base

    def _engineer_item_features(
        self, items: pd.DataFrame, products: pd.DataFrame
    ) -> pd.DataFrame:
        """Aggregates item line items up to the order grain."""
        # Join product attributes
        items_prod = pd.merge(
            items,
            products[
                [
                    "product_id",
                    "product_category_name_english",
                    "product_weight_g",
                    "product_length_cm",
                    "product_height_cm",
                    "product_width_cm",
                ]
            ],
            on="product_id",
            how="left",
        )

        # Compute cubic volume in cm3
        items_prod["product_volume_cm3"] = (
            items_prod["product_length_cm"]
            * items_prod["product_height_cm"]
            * items_prod["product_width_cm"]
        )

        # Identify primary seller and category (highest price item in each order)
        items_sorted = items_prod.sort_values(
            ["order_id", "price"], ascending=[True, False]
        )
        primary_seller = (
            items_sorted.groupby("order_id")["seller_id"]
            .first()
            .rename("primary_seller_id")
        )
        primary_category = (
            items_sorted.groupby("order_id")["product_category_name_english"]
            .first()
            .rename("primary_product_category")
        )
        latest_shipping_limit = (
            items_sorted.groupby("order_id")["shipping_limit_date"]
            .max()
            .rename("max_shipping_limit_date")
        )

        # Aggregations at order grain
        agg_items = items_prod.groupby("order_id").agg(
            order_item_count=("order_item_id", "count"),
            order_unique_product_count=("product_id", "nunique"),
            order_unique_seller_count=("seller_id", "nunique"),
            order_total_item_value=("price", "sum"),
            order_total_freight_value=("freight_value", "sum"),
            order_total_weight_g=("product_weight_g", "sum"),
            order_max_item_weight_g=("product_weight_g", "max"),
            order_total_volume_cm3=("product_volume_cm3", "sum"),
        )

        res = (
            agg_items.join(primary_seller)
            .join(primary_category)
            .join(latest_shipping_limit)
            .reset_index()
        )
        return res

    def _engineer_payment_features(self, payments: pd.DataFrame) -> pd.DataFrame:
        """Aggregates payment transactions up to the order grain."""
        # Find primary payment tender (the one with the largest payment value)
        pay_sorted = payments.sort_values(
            ["order_id", "payment_value"], ascending=[True, False]
        )
        primary_type = (
            pay_sorted.groupby("order_id")["payment_type"]
            .first()
            .rename("primary_payment_type")
        )

        agg_pay = payments.groupby("order_id").agg(
            payment_split_count=("payment_sequential", "count"),
            max_payment_installments=("payment_installments", "max"),
            total_payment_value=("payment_value", "sum"),
        )

        res = agg_pay.join(primary_type).reset_index()
        res["is_multi_payment"] = (res["payment_split_count"] > 1).astype(int)
        return res

    def _attach_spatial_features(
        self, base: pd.DataFrame, sellers: pd.DataFrame, geo: pd.DataFrame
    ) -> pd.DataFrame:
        """Attaches customer/seller geographic centroids and computes Haversine distance."""
        # Merge seller metadata
        base = pd.merge(
            base,
            sellers[
                ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"]
            ],
            left_on="primary_seller_id",
            right_on="seller_id",
            how="left",
        )

        # Merge customer geo coordinates
        base = pd.merge(
            base,
            geo[
                ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng"]
            ].rename(
                columns={
                    "geolocation_zip_code_prefix": "customer_zip_code_prefix",
                    "geolocation_lat": "customer_lat",
                    "geolocation_lng": "customer_lng",
                }
            ),
            on="customer_zip_code_prefix",
            how="left",
        )

        # Merge seller geo coordinates
        base = pd.merge(
            base,
            geo[
                ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng"]
            ].rename(
                columns={
                    "geolocation_zip_code_prefix": "seller_zip_code_prefix",
                    "geolocation_lat": "seller_lat",
                    "geolocation_lng": "seller_lng",
                }
            ),
            on="seller_zip_code_prefix",
            how="left",
        )

        # Interstate flag
        base["is_interstate_delivery"] = (
            (base["customer_state"].notna())
            & (base["seller_state"].notna())
            & (base["customer_state"] != base["seller_state"])
        ).astype(int)

        # Calculate Haversine distance in km
        base["haversine_distance_km"] = haversine_distance(
            base["customer_lat"],
            base["customer_lng"],
            base["seller_lat"],
            base["seller_lng"],
        )

        # Impute missing distance with state median or overall national median
        overall_median_dist = float(base["haversine_distance_km"].median())
        base["haversine_distance_km"] = base["haversine_distance_km"].fillna(
            overall_median_dist
        )
        return base

    def _engineer_temporal_features(self, base: pd.DataFrame) -> pd.DataFrame:
        """Extracts calendar properties and operational time windows."""
        p_time = base["order_purchase_timestamp"]

        # Calendar features (known at checkout)
        base["purchase_year"] = p_time.dt.year
        base["purchase_month"] = p_time.dt.month
        base["purchase_day"] = p_time.dt.day
        base["purchase_day_of_week"] = p_time.dt.dayofweek
        base["purchase_hour"] = p_time.dt.hour
        base["is_weekend"] = base["purchase_day_of_week"].isin([5, 6]).astype(int)

        # SLA buffer communicated to customer at purchase (in days)
        base["estimated_delivery_duration_days"] = (
            base["order_estimated_delivery_date"] - base["order_purchase_timestamp"]
        ).dt.total_seconds() / 86400.0

        # Seller processing time until carrier handoff (in hours) - known at dispatch moment
        base["seller_dispatch_duration_hours"] = (
            base["order_delivered_carrier_date"] - base["order_purchase_timestamp"]
        ).dt.total_seconds() / 3600.0

        # Flag whether seller breached shipping deadline
        base["is_seller_late_dispatch"] = (
            base["order_delivered_carrier_date"] > base["max_shipping_limit_date"]
        ).astype(int)

        # Retrospective operational durations (outcome metrics - NOT FOR PREDICTION)
        base["carrier_transit_duration_days"] = (
            base["order_delivered_customer_date"] - base["order_delivered_carrier_date"]
        ).dt.total_seconds() / 86400.0
        base["actual_delivery_duration_days"] = (
            base["order_delivered_customer_date"] - base["order_purchase_timestamp"]
        ).dt.total_seconds() / 86400.0
        return base

    def _engineer_historical_seller_performance(
        self, base: pd.DataFrame
    ) -> pd.DataFrame:
        """Calculates historical seller late rate using strictly expanding historical windows without future data leakage."""
        # Sort chronologically by purchase timestamp
        sorted_orders = base.sort_values("order_purchase_timestamp").copy()

        # Temporary target: was the order delivered late?
        temp_is_late = (
            (sorted_orders["order_delivered_customer_date"].notna())
            & (
                sorted_orders["order_delivered_customer_date"]
                > sorted_orders["order_estimated_delivery_date"]
            )
        ).astype(int)

        sorted_orders["_temp_late"] = temp_is_late

        # Expanding window per primary seller
        # Count of prior orders strictly before current row
        sorted_orders["seller_prior_order_count"] = sorted_orders.groupby(
            "primary_seller_id"
        ).cumcount()
        # Count of prior late orders strictly before current row
        sorted_orders["seller_prior_late_count"] = (
            sorted_orders.groupby("primary_seller_id")["_temp_late"].cumsum()
            - sorted_orders["_temp_late"]
        )

        # Expanding historical late rate (0.0 if seller has no prior history or no seller)
        sorted_orders["seller_prior_late_rate"] = np.where(
            sorted_orders["seller_prior_order_count"] > 0,
            sorted_orders["seller_prior_late_count"]
            / sorted_orders["seller_prior_order_count"],
            0.0,
        )

        # Impute orders without items/seller (775 canceled orders) with 0
        sorted_orders["seller_prior_order_count"] = (
            sorted_orders["seller_prior_order_count"].fillna(0).astype(int)
        )
        sorted_orders["seller_prior_late_rate"] = sorted_orders[
            "seller_prior_late_rate"
        ].fillna(0.0)

        # Drop temporary column and restore original index order
        sorted_orders = sorted_orders.drop(columns=["_temp_late"])
        return sorted_orders.sort_index()

    def _construct_target_variables(self, base: pd.DataFrame) -> pd.DataFrame:
        """Constructs late delivery ground-truth target variables."""
        # Delivery delay in days: actual arrival date - estimated delivery date
        # Positive = delivered after estimate (LATE)
        # Negative or 0 = delivered on or before estimate (ON TIME)
        base["delivery_delay_days"] = (
            base["order_delivered_customer_date"]
            - base["order_estimated_delivery_date"]
        ).dt.total_seconds() / 86400.0

        # Binary classification target: 1 = Late, 0 = On Time
        # Only defined for delivered orders with observable arrival timestamps
        base["is_late_delivery"] = np.where(
            base["order_delivered_customer_date"].isna(),
            np.nan,
            (base["delivery_delay_days"] > 0.0).astype(float),
        )

        # Delivered order filter flag (target population for classification)
        base["is_delivered"] = base["order_status"] == "delivered"
        return base

    def _generate_feature_dictionary(self, df: pd.DataFrame) -> Path:
        """Generates comprehensive feature dictionary and anti-leakage timeline documentation."""
        report_path = self.docs_dir / "feature_dictionary.md"
        total_orders = len(df)
        delivered_orders = int(df["is_delivered"].sum())
        late_orders = int((df["is_late_delivery"] == 1.0).sum())
        late_rate = (
            (late_orders / delivered_orders) * 100 if delivered_orders > 0 else 0.0
        )

        lines: list[str] = [
            "# Feature Store Dictionary & Availability Timeline",
            "",
            "**Module**: `src/marketplace_intelligence/feature_engineering.py`  ",
            "**Output Asset**: `data/processed/order_features.parquet`  ",
            "**Grain**: Exactly 1 row per order (`order_id`)  ",
            "",
            "---",
            "",
            "## 1. Population & Target Variable Overview",
            "",
            f"- **Total Market Orders**: {total_orders:,}",
            f"- **Delivered Orders (Model Target Population)**: {delivered_orders:,} ({delivered_orders / total_orders:.1%})",
            f"- **Late Delivered Orders (`is_late_delivery = 1`)**: {late_orders:,} (**{late_rate:.2f}% Baseline Late Rate**)",
            f"- **On-Time Delivered Orders (`is_late_delivery = 0`)**: {delivered_orders - late_orders:,} ({100 - late_rate:.2f}%)",
            "",
            "---",
            "",
            "## 2. Feature Availability Timeline & Anti-Leakage Tiers",
            "",
            "To prevent data leakage, every feature in this dataset is classified into strict operational availability moments:",
            "",
            "```text",
            "TIMELINE:   [T0: Purchase]  ----->  [T1: Carrier Dispatch]  ----->  [T2: Doorstep Delivery]  ----->  [T3: Review Survey]",
            "TIER:       Checkout Known          Carrier Handoff Known           Actual Outcome Realized          Customer Feedback",
            "STATUS:     VALID PREDICTION        VALID PREDICTION                POST-OUTCOME (LEAKAGE)           POST-OUTCOME (LEAKAGE)",
            "```",
            "",
            "| Availability Tier | Availability Moment | Safe for Late-Delivery ML Model? | Example Features |",
            "|---|---|---|---|",
            "| **Tier 1 (Checkout)** | `order_purchase_timestamp` | ✅ **YES** | `order_total_value`, `freight_ratio`, `haversine_distance_km`, `purchase_hour`, `primary_product_category`, `estimated_delivery_duration_days` |",
            "| **Tier 2 (Dispatch)** | `order_delivered_carrier_date` | ✅ **YES** | All Tier 1 PLUS `seller_dispatch_duration_hours`, `is_seller_late_dispatch` |",
            "| **Tier 3 (Delivery)** | `order_delivered_customer_date`| ❌ **STRICT LEAKAGE** | `is_late_delivery` (TARGET), `delivery_delay_days`, `actual_delivery_duration_days` |",
            "| **Tier 4 (Review)** | `review_answer_timestamp` | ❌ **STRICT LEAKAGE** | `review_score`, `is_delivery_issue`, `review_comment_message` |",
            "",
            "---",
            "",
            "## 3. Detailed Feature Dictionary",
            "",
            "| Feature Name | Data Type | Availability Tier | Business Definition & Formula |",
            "|---|---|---|---|",
            "| `order_id` | `VARCHAR(32)` | Identifier | Unique order key |",
            "| `customer_unique_id` | `VARCHAR(32)` | Identifier | Human customer key |",
            "| `order_item_count` | `INTEGER` | Tier 1 (Checkout) | Number of physical line items in order |",
            "| `order_total_item_value` | `NUMERIC(10,2)` | Tier 1 (Checkout) | Sum of item sales prices (GMV) in BRL |",
            "| `order_total_freight_value`| `NUMERIC(10,2)` | Tier 1 (Checkout) | Total shipping fee charged for order in BRL |",
            "| `order_total_value` | `NUMERIC(10,2)` | Tier 1 (Checkout) | GMV + Freight total order transaction amount |",
            "| `freight_ratio` | `FLOAT` | Tier 1 (Checkout) | `freight_value / total_value` (Cost friction metric) |",
            "| `order_total_weight_g` | `FLOAT` | Tier 1 (Checkout) | Combined mass of items in grams |",
            "| `order_total_volume_cm3` | `FLOAT` | Tier 1 (Checkout) | Package cubic volume in cubic centimeters ($L \\times W \\times H$) |",
            "| `primary_product_category` | `VARCHAR(64)` | Tier 1 (Checkout) | English category of highest priced item in order |",
            "| `primary_payment_type` | `VARCHAR(16)` | Tier 1 (Checkout) | Payment method with highest charge |",
            "| `max_payment_installments` | `INTEGER` | Tier 1 (Checkout) | Maximum monthly installment financing selected |",
            "| `is_multi_payment` | `INTEGER` | Tier 1 (Checkout) | Flag indicating multiple split tenders (1 if splits > 1) |",
            "| `is_multi_seller` | `INTEGER` | Tier 1 (Checkout) | Flag indicating multi-vendor fulfillment (1 if sellers > 1) |",
            "| `customer_state` | `CHAR(2)` | Tier 1 (Checkout) | Destination Brazilian state abbreviation (UF) |",
            "| `seller_state` | `CHAR(2)` | Tier 1 (Checkout) | Fulfillment origin Brazilian state abbreviation (UF) |",
            "| `is_interstate_delivery` | `INTEGER` | Tier 1 (Checkout) | Flag indicating cross-state logistics (1 if customer_state != seller_state) |",
            "| `haversine_distance_km` | `FLOAT` | Tier 1 (Checkout) | Great-circle distance between customer and seller centroids in km |",
            "| `purchase_year` | `INTEGER` | Tier 1 (Checkout) | Calendar year of purchase |",
            "| `purchase_month` | `INTEGER` | Tier 1 (Checkout) | Month of purchase (1-12) |",
            "| `purchase_day_of_week` | `INTEGER` | Tier 1 (Checkout) | Day of week (0=Monday, 6=Sunday) |",
            "| `purchase_hour` | `INTEGER` | Tier 1 (Checkout) | Hour of purchase (0-23) |",
            "| `is_weekend` | `INTEGER` | Tier 1 (Checkout) | Weekend transaction flag (1 if Saturday/Sunday) |",
            "| `estimated_delivery_duration_days`| `FLOAT` | Tier 1 (Checkout) | Promised delivery SLA buffer in days (`estimated_date - purchase_date`) |",
            "| `seller_prior_order_count` | `INTEGER` | Tier 1 (Checkout) | Prior orders fulfilled by primary seller strictly before purchase date |",
            "| `seller_prior_late_rate` | `FLOAT` | Tier 1 (Checkout) | Historical late rate of seller prior to purchase date (expanding window) |",
            "| `seller_dispatch_duration_hours` | `FLOAT` | Tier 2 (Dispatch) | Seller processing time until carrier handoff (`carrier_date - purchase_date`) |",
            "| `is_seller_late_dispatch`| `INTEGER` | Tier 2 (Dispatch) | Flag indicating seller breached shipping limit (`carrier_date > shipping_limit`) |",
            "| `carrier_transit_duration_days` | `FLOAT` | Tier 3 (Outcome) | Actual transit duration on the road (`delivered_date - carrier_date`) |",
            "| `actual_delivery_duration_days` | `FLOAT` | Tier 3 (Outcome) | Total order-to-doorstep duration (`delivered_date - purchase_date`) |",
            "| `delivery_delay_days` | `FLOAT` | Tier 3 (Outcome) | Days delivered after promised estimate (`delivered_date - estimated_date`) |",
            "| `is_late_delivery` | `FLOAT (0/1)`| Tier 3 (TARGET) | Ground-truth late delivery target (1 if delay > 0, 0 if on time) |",
        ]

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Feature dictionary written to {report_path.resolve()}")
        return report_path


if __name__ == "__main__":
    fe = FeatureEngineer(processed_dir="data/processed", docs_dir="docs")
    fe.build_feature_store()
