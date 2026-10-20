# Data Architecture & Database Engineering Specification

This document details the multi-layer relational data architecture, schema design, and Kimball dimensional model (Star Schema) engineered for the **Marketplace Profitability & Delivery Intelligence Engine**.

---

## 1. Multi-Layer Medallion Architecture

The engine implements a modern 4-tier analytical data pipeline:

```text
+-----------------------------------------------------------------------------------+
| 1. RAW LAYER (data/raw/)                                                          |
|    - Immutable, read-only Olist CSVs (9 relational source tables).                |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 2. PROCESSED & FEATURE LAYER (data/processed/)                                    |
|    - Schema validation, Portuguese text NLP, spatial centroid deduplication.      |
|    - Exported to high-performance Apache Parquet with embedded strict types.      |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 3. POSTGRESQL STAGING LAYER (stg.*)                                              |
|    - Source-shaped, typed tables in PostgreSQL matching operational entities.     |
|    - Serves as the landing and audit zone inside the relational database.         |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 4. POSTGRESQL CORE DIMENSIONAL MODEL (core.*)                                     |
|    - Kimball Star Schema: 5 Dimensions (dim_*) & 4 Fact Tables (fact_*).          |
|    - Enforces primary keys, foreign keys, constraints, and B-Tree indexes.        |
|    - Guarantees zero join fanout and penny-perfect financial reconciliation.       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 5. ANALYTICAL MARTS & BI LAYER (mart.* & Power BI Desktop)                        |
|    - Business aggregation views (Cohort LTV, Seller Risk, GMV Trends, CSAT).     |
+-----------------------------------------------------------------------------------+
```

---

## 2. Kimball Dimensional Star Schema (`core.*`)

The relational database separates context entities (**Dimensions**) from quantitative transactional metrics (**Facts**).

### A. Dimension Tables
Dimensions contain descriptive context attributes used for slicing, dicing, and grouping:

1. **`core.dim_customer`**:
   - **Grain**: 1 row per order-scoped customer token (`customer_id`).
   - **Key Attributes**: Surrogate key `customer_key`, `customer_id`, `customer_unique_id` (real human buyer), `customer_city`, `customer_state`.
   - **Surrogate Key**: `customer_key SERIAL PRIMARY KEY`.
2. **`core.dim_seller`**:
   - **Grain**: 1 row per registered merchant vendor (`seller_id`).
   - **Key Attributes**: Surrogate key `seller_key`, `seller_id`, `seller_city`, `seller_state`, `seller_zip_code_prefix`.
3. **`core.dim_product`**:
   - **Grain**: 1 row per catalog product SKU (`product_id`).
   - **Key Attributes**: Surrogate key `product_key`, `product_id`, `product_category_name_english`, dimensions, weight, cubic volume.
4. **`core.dim_date`**:
   - **Grain**: 1 row per calendar day from 2016-01-01 to 2020-12-31.
   - **Key Attributes**: Smart integer key `date_key` (Format: `YYYYMMDD`), `full_date`, `year`, `quarter`, `month`, `day_of_week`, `is_weekend`.
5. **`core.dim_location`**:
   - **Grain**: 1 row per unique 5-digit Brazilian postal code prefix centroid (`zip_code_prefix`).
   - **Key Attributes**: `location_key`, `zip_code_prefix`, `latitude`, `longitude`, `city`, `state`.

---

### B. Fact Tables
Fact tables contain numerical additive measures and foreign keys linking to dimensions:

1. **`core.fact_orders`**:
   - **Grain**: Exactly 1 row per purchase order (`order_id`).
   - **Foreign Keys**: `customer_key` $\rightarrow$ `dim_customer`, `purchase_date_key` $\rightarrow$ `dim_date`.
   - **Additive Measures**: `order_item_count`, `order_total_item_value` (GMV), `order_total_freight_value`, `order_total_value`, `haversine_distance_km`.
   - **Operational Timestamps & Flags**: `order_purchase_timestamp`, `order_delivered_customer_date`, `delivery_delay_days`, `is_late_delivery`, `is_delivered`.
2. **`core.fact_order_items`**:
   - **Grain**: Exactly 1 row per ordered physical line-item.
   - **Foreign Keys**: `customer_key`, `seller_key`, `product_key`, `purchase_date_key`.
   - **Measures**: `price`, `freight_value`, `item_total_value`.
3. **`core.fact_payments`**:
   - **Grain**: Exactly 1 row per payment transaction attempt/split.
   - **Foreign Keys**: `order_id` (Logical reference).
   - **Measures**: `payment_value`, `payment_installments`.
4. **`core.fact_reviews`**:
   - **Grain**: Exactly 1 row per customer survey response.
   - **Foreign Keys**: `order_id` (Logical reference).
   - **Qualitative Attributes**: `review_score` (1-5), `csat_category`, `is_delivery_issue`, `is_product_quality_issue`, `operational_feedback_tag`.

---

## 3. Database Integrity & Foreign Key Enforcement

1. **Surrogate Keys**: Integer `SERIAL` keys (`customer_key`, `seller_key`, `product_key`) decouple the analytical warehouse from natural business keys.
2. **Composite Primary Keys**: Enforced on staging line-item and payment entities (`(order_id, order_item_id)`, `(order_id, payment_sequential)`, `(review_id, order_id)`).
3. **Referential Constraints**: Fact tables enforce foreign key references to dimension tables using PostgreSQL `FOREIGN KEY (...) REFERENCES ...`.
4. **B-Tree Indexes**: Placed on all foreign keys, status columns, date keys, and high-frequency join columns to guarantee sub-second query performance.
5. **Exact Financial Reconciliation**: `core.fact_orders` totals are populated directly from pre-aggregated order features, guaranteeing that `SUM(order_total_item_value)` across all orders matches `SUM(price)` across all line items to the penny (\$0.00 discrepancy).
