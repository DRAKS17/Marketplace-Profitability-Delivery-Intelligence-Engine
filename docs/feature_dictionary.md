# Feature Store Dictionary & Availability Timeline

**Module**: `src/marketplace_intelligence/feature_engineering.py`  
**Output Asset**: `data/processed/order_features.parquet`  
**Grain**: Exactly 1 row per order (`order_id`)  

---

## 1. Population & Target Variable Overview

- **Total Market Orders**: 99,441
- **Delivered Orders (Model Target Population)**: 96,478 (97.0%)
- **Late Delivered Orders (`is_late_delivery = 1`)**: 7,827 (**8.11% Baseline Late Rate**)
- **On-Time Delivered Orders (`is_late_delivery = 0`)**: 88,651 (91.89%)

---

## 2. Feature Availability Timeline & Anti-Leakage Tiers

To prevent data leakage, every feature in this dataset is classified into strict operational availability moments:

```text
TIMELINE:   [T0: Purchase]  ----->  [T1: Carrier Dispatch]  ----->  [T2: Doorstep Delivery]  ----->  [T3: Review Survey]
TIER:       Checkout Known          Carrier Handoff Known           Actual Outcome Realized          Customer Feedback
STATUS:     VALID PREDICTION        VALID PREDICTION                POST-OUTCOME (LEAKAGE)           POST-OUTCOME (LEAKAGE)
```

| Availability Tier | Availability Moment | Safe for Late-Delivery ML Model? | Example Features |
|---|---|---|---|
| **Tier 1 (Checkout)** | `order_purchase_timestamp` | ✅ **YES** | `order_total_value`, `freight_ratio`, `haversine_distance_km`, `purchase_hour`, `primary_product_category`, `estimated_delivery_duration_days` |
| **Tier 2 (Dispatch)** | `order_delivered_carrier_date` | ✅ **YES** | All Tier 1 PLUS `seller_dispatch_duration_hours`, `is_seller_late_dispatch` |
| **Tier 3 (Delivery)** | `order_delivered_customer_date`| ❌ **STRICT LEAKAGE** | `is_late_delivery` (TARGET), `delivery_delay_days`, `actual_delivery_duration_days` |
| **Tier 4 (Review)** | `review_answer_timestamp` | ❌ **STRICT LEAKAGE** | `review_score`, `is_delivery_issue`, `review_comment_message` |

---

## 3. Detailed Feature Dictionary

| Feature Name | Data Type | Availability Tier | Business Definition & Formula |
|---|---|---|---|
| `order_id` | `VARCHAR(32)` | Identifier | Unique order key |
| `customer_unique_id` | `VARCHAR(32)` | Identifier | Human customer key |
| `order_item_count` | `INTEGER` | Tier 1 (Checkout) | Number of physical line items in order |
| `order_total_item_value` | `NUMERIC(10,2)` | Tier 1 (Checkout) | Sum of item sales prices (GMV) in BRL |
| `order_total_freight_value`| `NUMERIC(10,2)` | Tier 1 (Checkout) | Total shipping fee charged for order in BRL |
| `order_total_value` | `NUMERIC(10,2)` | Tier 1 (Checkout) | GMV + Freight total order transaction amount |
| `freight_ratio` | `FLOAT` | Tier 1 (Checkout) | `freight_value / total_value` (Cost friction metric) |
| `order_total_weight_g` | `FLOAT` | Tier 1 (Checkout) | Combined mass of items in grams |
| `order_total_volume_cm3` | `FLOAT` | Tier 1 (Checkout) | Package cubic volume in cubic centimeters ($L \times W \times H$) |
| `primary_product_category` | `VARCHAR(64)` | Tier 1 (Checkout) | English category of highest priced item in order |
| `primary_payment_type` | `VARCHAR(16)` | Tier 1 (Checkout) | Payment method with highest charge |
| `max_payment_installments` | `INTEGER` | Tier 1 (Checkout) | Maximum monthly installment financing selected |
| `is_multi_payment` | `INTEGER` | Tier 1 (Checkout) | Flag indicating multiple split tenders (1 if splits > 1) |
| `is_multi_seller` | `INTEGER` | Tier 1 (Checkout) | Flag indicating multi-vendor fulfillment (1 if sellers > 1) |
| `customer_state` | `CHAR(2)` | Tier 1 (Checkout) | Destination Brazilian state abbreviation (UF) |
| `seller_state` | `CHAR(2)` | Tier 1 (Checkout) | Fulfillment origin Brazilian state abbreviation (UF) |
| `is_interstate_delivery` | `INTEGER` | Tier 1 (Checkout) | Flag indicating cross-state logistics (1 if customer_state != seller_state) |
| `haversine_distance_km` | `FLOAT` | Tier 1 (Checkout) | Great-circle distance between customer and seller centroids in km |
| `purchase_year` | `INTEGER` | Tier 1 (Checkout) | Calendar year of purchase |
| `purchase_month` | `INTEGER` | Tier 1 (Checkout) | Month of purchase (1-12) |
| `purchase_day_of_week` | `INTEGER` | Tier 1 (Checkout) | Day of week (0=Monday, 6=Sunday) |
| `purchase_hour` | `INTEGER` | Tier 1 (Checkout) | Hour of purchase (0-23) |
| `is_weekend` | `INTEGER` | Tier 1 (Checkout) | Weekend transaction flag (1 if Saturday/Sunday) |
| `estimated_delivery_duration_days`| `FLOAT` | Tier 1 (Checkout) | Promised delivery SLA buffer in days (`estimated_date - purchase_date`) |
| `seller_prior_order_count` | `INTEGER` | Tier 1 (Checkout) | Prior orders fulfilled by primary seller strictly before purchase date |
| `seller_prior_late_rate` | `FLOAT` | Tier 1 (Checkout) | Historical late rate of seller prior to purchase date (expanding window) |
| `seller_dispatch_duration_hours` | `FLOAT` | Tier 2 (Dispatch) | Seller processing time until carrier handoff (`carrier_date - purchase_date`) |
| `is_seller_late_dispatch`| `INTEGER` | Tier 2 (Dispatch) | Flag indicating seller breached shipping limit (`carrier_date > shipping_limit`) |
| `carrier_transit_duration_days` | `FLOAT` | Tier 3 (Outcome) | Actual transit duration on the road (`delivered_date - carrier_date`) |
| `actual_delivery_duration_days` | `FLOAT` | Tier 3 (Outcome) | Total order-to-doorstep duration (`delivered_date - purchase_date`) |
| `delivery_delay_days` | `FLOAT` | Tier 3 (Outcome) | Days delivered after promised estimate (`delivered_date - estimated_date`) |
| `is_late_delivery` | `FLOAT (0/1)`| Tier 3 (TARGET) | Ground-truth late delivery target (1 if delay > 0, 0 if on time) |