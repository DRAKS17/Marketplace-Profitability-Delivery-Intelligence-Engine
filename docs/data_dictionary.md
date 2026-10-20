# Master Data Dictionary & Relational Architecture

This data dictionary serves as the single source of truth for the **Marketplace Profitability & Delivery Intelligence Engine**. All schemas, grains, data types, constraints, and relational mappings have been verified empirically against the 9 raw CSV files.

---

## 1. Relational Architecture & Table Summary

| Table / Entity | Source File | Verified Grain | Primary Key (PK) | Foreign Keys (FK) | Total Rows | Null Summary |
|---|---|---|---|---|---|---|
| **Customers** | `olist_customers_dataset.csv` | 1 row per order-scoped customer token | `customer_id` | `customer_zip_code_prefix` -> Geolocation | 99,441 | 0 nulls across all columns |
| **Orders** | `olist_orders_dataset.csv` | 1 row per purchase order | `order_id` | `customer_id` -> Customers | 99,441 | Structural nulls in carrier and delivery dates |
| **Order Items** | `olist_order_items_dataset.csv` | 1 row per ordered physical line-item | Composite: `(order_id, order_item_id)` | `order_id` -> Orders<br>`product_id` -> Products<br>`seller_id` -> Sellers | 112,650 | 0 nulls; 383 free-shipping records (`freight = 0`) |
| **Order Payments** | `olist_order_payments_dataset.csv` | 1 row per payment installment or tender split | Composite: `(order_id, payment_sequential)` | `order_id` -> Orders | 103,886 | 0 nulls; 9 zero-value records |
| **Order Reviews** | `olist_order_reviews_dataset.csv` | 1 row per customer feedback response | Composite: `(review_id, order_id)` | `order_id` -> Orders | 99,224 | 88.3% null titles, 58.7% null messages |
| **Products** | `olist_products_dataset.csv` | 1 row per distinct SKU catalog listing | `product_id` | `product_category_name` -> Translations | 32,951 | 610 missing category names; 2 missing dimensions |
| **Sellers** | `olist_sellers_dataset.csv` | 1 row per registered marketplace merchant | `seller_id` | `seller_zip_code_prefix` -> Geolocation | 3,095 | 0 nulls across all columns |
| **Geolocation** | `olist_geolocation_dataset.csv` | 1 row per recorded GPS coordinate reading | Non-unique (requires spatial aggregation) | `geolocation_zip_code_prefix` | 1,000,163 | 261,831 exact duplicate rows; 0 nulls |
| **Category Translations** | `product_category_name_translation.csv`| 1 row per category language mapping | `product_category_name` | None | 71 | 0 nulls; 2 catalog categories untranslated |

---

## 2. Table-by-Table Data Dictionary

### Table 1: `olist_customers_dataset.csv` (Customers)
- **Description**: Contains customer identification and geographic location.
- **Grain**: Exactly 1 row per order transaction token (`customer_id`).
- **Critical Distinction**: `customer_id` is an order-specific pseudonym assigned to each checkout. `customer_unique_id` represents the true human buyer across all their historical orders.
- **Primary Key**: `customer_id` (Unique, 0 nulls).
- **Foreign Key Candidates**: `customer_zip_code_prefix` -> `olist_geolocation_dataset.csv`.
- **Analytical Uses**: Customer cohort analysis, repeat purchase retention (LTV), geographic buyer distribution.

| Column Name | Raw Dtype | SQL Target Dtype | Nullable | Description & Domain | Sample Values |
|---|---|---|---|---|---|
| `customer_id` | `object` | `VARCHAR(32)` | No | Order-level customer token (1:1 with orders) | `06b8999e2fba1a1fbc88172c00ba8bc7` |
| `customer_unique_id` | `object` | `VARCHAR(32)` | No | Unique identifier for a human being | `861eff4711a542e4b93843c6dd7febb0` |
| `customer_zip_code_prefix` | `int64` | `INTEGER` | No | First 5 digits of Brazilian postal code (CEP) | `14409`, `9790` |
| `customer_city` | `object` | `VARCHAR(64)` | No | Customer's delivery city | `franca`, `sao paulo` |
| `customer_state` | `object` | `CHAR(2)` | No | Customer's Brazilian state abbreviation (UF) | `SP`, `RJ`, `MG` |

---

### Table 2: `olist_orders_dataset.csv` (Orders)
- **Description**: The central transaction backbone tracking the lifecycle timestamps and status of each order.
- **Grain**: Exactly 1 row per customer order.
- **Primary Key**: `order_id` (Unique, 0 nulls).
- **Foreign Keys**: `customer_id` -> `olist_customers_dataset.csv(customer_id)`.
- **Missing-Value Behavior**:
  - `order_approved_at`: 160 nulls (unapproved, rejected, or immediate cancellations).
  - `order_delivered_carrier_date`: 1,783 nulls (not yet handed to carrier or canceled).
  - `order_delivered_customer_date`: 2,965 nulls (unfulfilled, lost, canceled, or in-transit).
- **Analytical Uses**: Fulfillment lead time, carrier transit duration, delivery SLA breaches, delivery-risk target definition.

| Column Name | Raw Dtype | SQL Target Dtype | Nullable | Description & Domain | Sample Values |
|---|---|---|---|---|---|
| `order_id` | `object` | `VARCHAR(32)` | No | Unique purchase order identifier | `e481f51cbdc54678b7cc49136f2d6af7` |
| `customer_id` | `object` | `VARCHAR(32)` | No | Foreign key linking to customer order token | `9ef432eb6251297304e76186b10a928d` |
| `order_status` | `object` | `VARCHAR(16)` | No | Status (`delivered`, `shipped`, `canceled`, `invoiced`, `processing`, `unavailable`) | `delivered`, `shipped` |
| `order_purchase_timestamp` | `object` | `TIMESTAMPTZ` | No | Moment order was finalized by customer | `2017-10-02 10:56:33` |
| `order_approved_at` | `object` | `TIMESTAMPTZ` | Yes | Moment payment was authorized | `2017-10-02 11:07:15` |
| `order_delivered_carrier_date` | `object` | `TIMESTAMPTZ` | Yes | Moment seller handed package to carrier | `2017-10-04 19:55:00` |
| `order_delivered_customer_date`| `object` | `TIMESTAMPTZ` | Yes | Actual arrival timestamp at customer doorstep | `2017-10-10 21:25:13` |
| `order_estimated_delivery_date`| `object` | `DATE` | No | Promised delivery estimate communicated at checkout | `2017-10-18 00:00:00` |

---

### Table 3: `olist_order_items_dataset.csv` (Order Items)
- **Description**: Line-item ledger recording the price, freight, product, seller, and shipping deadline for every item in an order.
- **Grain**: Exactly 1 row per physical item sold.
- **Primary Key**: Composite key `(order_id, order_item_id)`.
- **Foreign Keys**:
  - `order_id` -> `olist_orders_dataset.csv(order_id)`
  - `product_id` -> `olist_products_dataset.csv(product_id)`
  - `seller_id` -> `olist_sellers_dataset.csv(seller_id)`
- **Analytical Uses**: Gross Merchandise Value (GMV), item-level margins, freight-to-price ratios, seller fulfillment speed, product category sales.

| Column Name | Raw Dtype | SQL Target Dtype | Nullable | Description & Domain | Sample Values |
|---|---|---|---|---|---|
| `order_id` | `object` | `VARCHAR(32)` | No | Foreign key to orders | `00010242fe8c5a6d1ba2dd792cb16214` |
| `order_item_id` | `int64` | `SMALLINT` | No | Item line index (1, 2, ... N within order) | `1`, `2` |
| `product_id` | `object` | `VARCHAR(32)` | No | Foreign key to product SKU | `4244733e06e7ecb4970a6e2683c13e61` |
| `seller_id` | `object` | `VARCHAR(32)` | No | Foreign key to seller merchant ID | `48436dade18ac8b2bce089ec2a041202` |
| `shipping_limit_date` | `object` | `TIMESTAMPTZ` | No | Seller fulfillment dispatch deadline | `2017-09-19 09:45:35` |
| `price` | `float64` | `NUMERIC(10,2)` | No | Item sale price in Brazilian Real (BRL) | `58.90`, `239.90` |
| `freight_value` | `float64` | `NUMERIC(10,2)` | No | Shipping fee allocated to this item in BRL | `13.29`, `19.93` |

---

### Table 4: `olist_order_payments_dataset.csv` (Order Payments)
- **Description**: Financial ledger recording tender methods, installments, and payment amounts.
- **Grain**: Exactly 1 row per payment transaction attempt/split.
- **Primary Key**: Composite key `(order_id, payment_sequential)`.
- **Foreign Keys**: `order_id` -> `olist_orders_dataset.csv(order_id)`.
- **Analytical Uses**: Payment tender mix (Boleto vs Credit Card vs Voucher), installment financing behavior, cash flow settlement.

| Column Name | Raw Dtype | SQL Target Dtype | Nullable | Description & Domain | Sample Values |
|---|---|---|---|---|---|
| `order_id` | `object` | `VARCHAR(32)` | No | Foreign key to orders | `b81ef226f3fe1789b1e8b2acac839d17` |
| `payment_sequential` | `int64` | `SMALLINT` | No | Sequence index when order uses multiple tenders | `1`, `2` |
| `payment_type` | `object` | `VARCHAR(16)` | No | Method (`credit_card`, `boleto`, `voucher`, `debit_card`) | `credit_card`, `boleto` |
| `payment_installments` | `int64` | `SMALLINT` | No | Number of monthly financing installments (1-24) | `1`, `8` |
| `payment_value` | `float64` | `NUMERIC(10,2)` | No | Total amount charged in this payment split | `99.33`, `154.10` |

---

### Table 5: `olist_order_reviews_dataset.csv` (Order Reviews)
- **Description**: Post-delivery customer satisfaction survey scores and qualitative feedback.
- **Grain**: Exactly 1 row per order survey response.
- **Primary Key**: Composite key `(review_id, order_id)`. Single `review_id` contains duplicates when multi-order surveys occur.
- **Foreign Keys**: `order_id` -> `olist_orders_dataset.csv(order_id)`.
- **Analytical Uses**: Customer satisfaction (CSAT), NLP review sentiment, correlation between shipping delay and 1-star reviews.

| Column Name | Raw Dtype | SQL Target Dtype | Nullable | Description & Domain | Sample Values |
|---|---|---|---|---|---|
| `review_id` | `object` | `VARCHAR(32)` | No | Survey response identifier | `7bc2406110b926393aa56f80a40eba40` |
| `order_id` | `object` | `VARCHAR(32)` | No | Foreign key to surveyed order | `73fc7af87114b39712e6da79b0a377eb` |
| `review_score` | `int64` | `SMALLINT` | No | Rating from 1 (poor) to 5 (excellent) | `1`, `4`, `5` |
| `review_comment_title` | `object` | `TEXT` | Yes (88.3%)| Optional title/header written by reviewer | `recomendo`, `Super recomendo` |
| `review_comment_message`| `object` | `TEXT` | Yes (58.7%)| Text review commentary in Portuguese | `Recebi bem antes do prazo...` |
| `review_creation_date` | `object` | `DATE` | No | Date survey invitation was dispatched | `2018-01-18 00:00:00` |
| `review_answer_timestamp`| `object` | `TIMESTAMPTZ` | No | Timestamp customer submitted response | `2018-01-18 21:46:59` |

---

### Table 6: `olist_products_dataset.csv` (Products)
- **Description**: Catalog metadata describing physical dimensions, weight, and category of products.
- **Grain**: Exactly 1 row per unique product SKU.
- **Primary Key**: `product_id` (Unique, 0 nulls).
- **Foreign Keys**: `product_category_name` -> `product_category_name_translation.csv`.
- **Analytical Uses**: Dimensional weight calculation, category profitability, packaging complexity, logistics cost modeling.

| Column Name | Raw Dtype | SQL Target Dtype | Nullable | Description & Domain | Sample Values |
|---|---|---|---|---|---|
| `product_id` | `object` | `VARCHAR(32)` | No | Product SKU identifier | `1e9e8ef04dbcff4541ed26657ea517e5` |
| `product_category_name` | `object` | `VARCHAR(64)` | Yes (1.9%) | Category name in Portuguese | `beleza_saude`, `cama_mesa_banho` |
| `product_name_lenght` | `float64` | `SMALLINT` | Yes (1.9%) | Character count of product title | `40`, `58` |
| `product_description_lenght` | `float64` | `INTEGER` | Yes (1.9%) | Character count of product description | `287`, `595` |
| `product_photos_qty` | `float64` | `SMALLINT` | Yes (1.9%) | Number of product photos in listing | `1`, `4` |
| `product_weight_g` | `float64` | `INTEGER` | Yes (2 rows)| Product mass in grams | `225`, `1000` |
| `product_length_cm` | `float64` | `SMALLINT` | Yes (2 rows)| Package length in cm | `16`, `30` |
| `product_height_cm` | `float64` | `SMALLINT` | Yes (2 rows)| Package height in cm | `10`, `18` |
| `product_width_cm` | `float64` | `SMALLINT` | Yes (2 rows)| Package width in cm | `14`, `20` |

---

### Table 7: `olist_sellers_dataset.csv` (Sellers)
- **Description**: Registry of independent merchants and third-party vendors selling on Olist.
- **Grain**: Exactly 1 row per registered merchant.
- **Primary Key**: `seller_id` (Unique, 0 nulls).
- **Foreign Keys**: `seller_zip_code_prefix` -> `olist_geolocation_dataset.csv`.
- **Analytical Uses**: Seller fulfillment SLA compliance, merchant concentration, regional fulfillment hubs, seller risk scoring.

| Column Name | Raw Dtype | SQL Target Dtype | Nullable | Description & Domain | Sample Values |
|---|---|---|---|---|---|
| `seller_id` | `object` | `VARCHAR(32)` | No | Unique merchant vendor identifier | `3442f8959a84dea7ee197c632cb2df15` |
| `seller_zip_code_prefix` | `int64` | `INTEGER` | No | Merchant business postal prefix | `13023`, `14940` |
| `seller_city` | `object` | `VARCHAR(64)` | No | Merchant municipality | `campinas`, `sao paulo` |
| `seller_state` | `object` | `CHAR(2)` | No | Merchant Brazilian state abbreviation (UF) | `SP`, `PR`, `MG` |

---

### Table 8: `olist_geolocation_dataset.csv` (Geolocation)
- **Description**: High-density coordinate mapping between Brazilian zip code prefixes and GPS coordinates.
- **Grain**: Spatial coordinate readings (multiple readings per zip prefix).
- **Primary Key**: None (requires spatial aggregation / centroid reduction before joining).
- **Analytical Uses**: Haversine distance calculations between customer and seller, regional logistics delay modeling.

| Column Name | Raw Dtype | SQL Target Dtype | Nullable | Description & Domain | Sample Values |
|---|---|---|---|---|---|
| `geolocation_zip_code_prefix`| `int64` | `INTEGER` | No | 5-digit Brazilian postal code prefix | `1037`, `1046` |
| `geolocation_lat` | `float64` | `NUMERIC(9,6)` | No | Latitude in decimal degrees | `-23.545621` |
| `geolocation_lng` | `float64` | `NUMERIC(9,6)` | No | Longitude in decimal degrees | `-46.639292` |
| `geolocation_city` | `object` | `VARCHAR(64)` | No | Municipal district name | `sao paulo` |
| `geolocation_state` | `object` | `CHAR(2)` | No | Brazilian state abbreviation (UF) | `SP`, `RJ` |

---

### Table 9: `product_category_name_translation.csv` (Translations)
- **Description**: Portuguese-to-English translation mapping for product catalog categories.
- **Grain**: Exactly 1 row per category pair.
- **Primary Key**: `product_category_name`.
- **Known Exception**: Missing English translations for `portateis_cozinha_e_preparadores_de_alimentos` and `pc_gamer`.

| Column Name | Raw Dtype | SQL Target Dtype | Nullable | Description & Domain | Sample Values |
|---|---|---|---|---|---|
| `product_category_name` | `object` | `VARCHAR(64)` | No | Category name in Portuguese | `beleza_saude` |
| `product_category_name_english`| `object` | `VARCHAR(64)` | No | Standardized English translation | `health_beauty` |

---

## 3. The Central Analytical Concept: Table Grain and Join Fanout

### What is Table "Grain"?
In dimensional modeling and analytics engineering (Kimball methodology), the **grain** represents the most atomic level of detail represented by a single row in a table:
- Grain of `orders`: 1 order.
- Grain of `order_items`: 1 ordered item within an order.
- Grain of `order_payments`: 1 payment installment / tender split within an order.

### The Join Fanout Trap: Why Blind Joins Multiply Financial Figures
When an analyst joins two one-to-many (`1:N`) child tables directly on their shared parent key (`order_id`) without prior aggregation, a **Cartesian Product** occurs for that order.

$$\text{Resulting Rows} = N_{\text{items}} \times M_{\text{payments}}$$

### Empirical Demonstration 1: Micro Case Study (Order `53036d8a739a905871d7f0096fa3b339`)

Consider Order `53036d8a739a905871d7f0096fa3b339` from the raw data:
- It contains **2 items** (Item 1 = \$99.99, Item 2 = \$99.99 $\rightarrow$ True Item Total = **\$199.98**).
- It was paid with **2 payment splits** (Voucher 1 = \$20.00, Credit Card 2 = \$220.36 $\rightarrow$ True Payment Total = **\$240.36**).

#### Naive Multi-Table SQL Join:
```sql
SELECT 
    o.order_id,
    SUM(i.price) AS total_item_value,
    SUM(p.payment_value) AS total_payment_value
FROM orders o
JOIN order_items i ON o.order_id = i.order_id
JOIN order_payments p ON o.order_id = p.order_id
WHERE o.order_id = '53036d8a739a905871d7f0096fa3b339'
GROUP BY o.order_id;
```

#### What Happens Under the Hood:
| Joined Row # | Item ID | Item Price | Payment Seq | Payment Value |
|---|---|---|---|---|
| 1 | 1 | \$99.99 | 1 | \$20.00 |
| 2 | 1 | \$99.99 | 2 | \$220.36 |
| 3 | 2 | \$99.99 | 1 | \$20.00 |
| 4 | 2 | \$99.99 | 2 | \$220.36 |

- Result rows: $2 \times 2 = 4$ rows!
- Naive `SUM(i.price)`: **\$399.96** (Artificially doubled! **2.0x inflation**).
- Naive `SUM(p.payment_value)`: **\$480.72** (Artificially doubled! **2.0x inflation**).

### Empirical Demonstration 2: Macro Impact Across the Whole Marketplace

When this naive join is run across all ~100k orders in Olist, the financial corruption reaches millions of dollars:

| Financial Metric | Ground Truth (Pre-Aggregated) | Naive Joined Result | Phantom Financial Error | Error % |
|---|---|---|---|---|
| **Merchandise Value (GMV)** | **\$13,591,643.70** | **\$14,209,115.34** | **+\$617,471.64** | **+4.54% Overstated** |
| **Payments Collected** | **\$16,008,872.12** | **\$20,308,134.71** | **+\$4,299,262.59** | **+26.86% Overstated** |

### The Engineering Solution: Pre-Aggregation CTEs
To join tables of different grains safely, each child table must first be aggregated up to the parent grain (`order_id`) inside Common Table Expressions (CTEs) or subqueries before joining:

```sql
WITH order_item_totals AS (
    SELECT order_id, SUM(price) AS true_gmv, SUM(freight_value) AS true_freight
    FROM order_items
    GROUP BY order_id
),
order_payment_totals AS (
    SELECT order_id, SUM(payment_value) AS true_payment
    FROM order_payments
    GROUP BY order_id
)
SELECT 
    o.order_id,
    it.true_gmv,
    it.true_freight,
    pt.true_payment
FROM orders o
LEFT JOIN order_item_totals it ON o.order_id = it.order_id
LEFT JOIN order_payment_totals pt ON o.order_id = pt.order_id;
```
This guarantees a **1:1 join**, preserving mathematical accuracy to the penny.
