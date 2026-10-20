# Data Profiling & Structural Inventory Report

**Source**: Brazilian E-Commerce Public Dataset by Olist (9 Raw CSV Entities)  
**Environment**: Python 3.13 | Pandas | Pure Read-Only Profiling  
**Audit Status**: Verified across all 9 source files  

---

## 1. High-Level Inventory

| Filename | Rows | Columns | Memory (MB) | Exact Duplicates | Candidate Primary Key |
|---|---|---|---|---|---|
| `olist_customers_dataset.csv` | 99,441 | 5 | 26.59 | 0 | `customer_id` |
| `olist_geolocation_dataset.csv` | 1,000,163 | 5 | 129.38 | 261,831 | None |
| `olist_order_items_dataset.csv` | 112,650 | 7 | 35.99 | 0 | Composite: `(order_id, order_item_id)` |
| `olist_order_payments_dataset.csv` | 103,886 | 5 | 16.23 | 0 | Composite: `(order_id, payment_sequential)` |
| `olist_order_reviews_dataset.csv` | 99,224 | 7 | 39.12 | 0 | Composite: `(review_id, order_id)` |
| `olist_orders_dataset.csv` | 99,441 | 8 | 52.94 | 0 | `order_id, customer_id` |
| `olist_products_dataset.csv` | 32,951 | 9 | 6.30 | 0 | `product_id` |
| `olist_sellers_dataset.csv` | 3,095 | 4 | 0.59 | 0 | `seller_id` |
| `product_category_name_translation.csv` | 71 | 2 | 0.01 | 0 | `product_category_name, product_category_name_english` |

---

## 2. Table-by-Table Architectural Findings

### Table: `olist_customers_dataset.csv`
- **Shape**: 99,441 rows × 5 columns
- **In-Memory Size**: 26.59 MB
- **Exact Duplicate Rows**: 0
- **Strict Unique Single Column (PK Candidate)**: `customer_id`
- **Critical Profiling & Anomaly Observations**:
  - ⚠️ Contains 99,441 customer_ids (order tokens) representing 96,096 unique human customers (customer_unique_id).

**Column Schema & Quality Profile**:

| Column Name | Inferred Dtype | Non-Null | Nulls | Null % | Unique Values | Sample Values |
|---|---|---|---|---|---|---|
| `customer_id` | `str` | 99,441 | 0 | 0.0% | 99,441 | `06b8999e2fba1a1fbc88172c00ba8bc7, 18955e83d337fd6b2def6b18a428ac77` |
| `customer_unique_id` | `str` | 99,441 | 0 | 0.0% | 96,096 | `861eff4711a542e4b93843c6dd7febb0, 290c77bc529b7ac935b93aa66c333dc3` |
| `customer_zip_code_prefix` | `int64` | 99,441 | 0 | 0.0% | 14,994 | `14409, 9790` |
| `customer_city` | `str` | 99,441 | 0 | 0.0% | 4,119 | `franca, sao bernardo do campo` |
| `customer_state` | `str` | 99,441 | 0 | 0.0% | 27 | `SP, SP` |

**Numerical Distributions Summary**:

| Numeric Column | Min | 25% / Median | Mean | Max | Std Dev |
|---|---|---|---|---|---|
| `customer_zip_code_prefix` | 1003.00 | 24416.00 | 35137.47 | 99990.00 | 29797.94 |

---

### Table: `olist_geolocation_dataset.csv`
- **Shape**: 1,000,163 rows × 5 columns
- **In-Memory Size**: 129.38 MB
- **Exact Duplicate Rows**: 261,831
- **Strict Unique Single Column (PK Candidate)**: `None`
- **Critical Profiling & Anomaly Observations**:
  - ⚠️ Contains 261,831 exact duplicate rows (26.18%).
  - ⚠️ Zip code prefix is NOT unique: 19,015 unique prefixes across 1,000,163 rows.

**Column Schema & Quality Profile**:

| Column Name | Inferred Dtype | Non-Null | Nulls | Null % | Unique Values | Sample Values |
|---|---|---|---|---|---|---|
| `geolocation_zip_code_prefix` | `int64` | 1,000,163 | 0 | 0.0% | 19,015 | `1037, 1046` |
| `geolocation_lat` | `float64` | 1,000,163 | 0 | 0.0% | 717,360 | `-23.54562128115268, -23.54608112703553` |
| `geolocation_lng` | `float64` | 1,000,163 | 0 | 0.0% | 717,613 | `-46.63929204800168, -46.64482029837157` |
| `geolocation_city` | `str` | 1,000,163 | 0 | 0.0% | 8,011 | `sao paulo, sao paulo` |
| `geolocation_state` | `str` | 1,000,163 | 0 | 0.0% | 27 | `SP, SP` |

**Numerical Distributions Summary**:

| Numeric Column | Min | 25% / Median | Mean | Max | Std Dev |
|---|---|---|---|---|---|
| `geolocation_zip_code_prefix` | 1001.00 | 26530.00 | 36574.17 | 99990.00 | 30549.34 |
| `geolocation_lat` | -36.61 | -22.92 | -21.18 | 45.07 | 5.72 |
| `geolocation_lng` | -101.47 | -46.64 | -46.39 | 121.11 | 4.27 |

---

### Table: `olist_order_items_dataset.csv`
- **Shape**: 112,650 rows × 7 columns
- **In-Memory Size**: 35.99 MB
- **Exact Duplicate Rows**: 0
- **Strict Unique Single Column (PK Candidate)**: `None`
- **Composite Key Uniqueness Tests**:
  - `(order_id, order_item_id)`: ✅ Valid (100% Unique & Complete)
- **Critical Profiling & Anomaly Observations**:
  - ⚠️ Column 'freight_value' has 383 zero-value transactions.

**Column Schema & Quality Profile**:

| Column Name | Inferred Dtype | Non-Null | Nulls | Null % | Unique Values | Sample Values |
|---|---|---|---|---|---|---|
| `order_id` | `str` | 112,650 | 0 | 0.0% | 98,666 | `00010242fe8c5a6d1ba2dd792cb16214, 00018f77f2f0320c557190d7a144bdd3` |
| `order_item_id` | `int64` | 112,650 | 0 | 0.0% | 21 | `1, 1` |
| `product_id` | `str` | 112,650 | 0 | 0.0% | 32,951 | `4244733e06e7ecb4970a6e2683c13e61, e5f2d52b802189ee658865ca93d83a8f` |
| `seller_id` | `str` | 112,650 | 0 | 0.0% | 3,095 | `48436dade18ac8b2bce089ec2a041202, dd7ddc04e1b6c2c614352b383efe2d36` |
| `shipping_limit_date` | `str` | 112,650 | 0 | 0.0% | 93,318 | `2017-09-19 09:45:35, 2017-05-03 11:05:13` |
| `price` | `float64` | 112,650 | 0 | 0.0% | 5,968 | `58.9, 239.9` |
| `freight_value` | `float64` | 112,650 | 0 | 0.0% | 6,999 | `13.29, 19.93` |

**Numerical Distributions Summary**:

| Numeric Column | Min | 25% / Median | Mean | Max | Std Dev |
|---|---|---|---|---|---|
| `order_item_id` | 1.00 | 1.00 | 1.20 | 21.00 | 0.71 |
| `price` | 0.85 | 74.99 | 120.65 | 6735.00 | 183.63 |
| `freight_value` | 0.00 | 16.26 | 19.99 | 409.68 | 15.81 |

**Temporal Boundaries (Date Ranges)**:

| Date Column | Earliest Timestamp | Latest Timestamp | Parsing Issues |
|---|---|---|---|
| `shipping_limit_date` | 2016-09-19 00:15:34 | 2020-04-09 22:35:08 | 0 |

---

### Table: `olist_order_payments_dataset.csv`
- **Shape**: 103,886 rows × 5 columns
- **In-Memory Size**: 16.23 MB
- **Exact Duplicate Rows**: 0
- **Strict Unique Single Column (PK Candidate)**: `None`
- **Composite Key Uniqueness Tests**:
  - `(order_id, payment_sequential)`: ✅ Valid (100% Unique & Complete)
- **Critical Profiling & Anomaly Observations**:
  - ⚠️ Column 'payment_installments' has 2 orders with 0 installments.
  - ⚠️ Column 'payment_value' has 9 zero-value transactions.

**Column Schema & Quality Profile**:

| Column Name | Inferred Dtype | Non-Null | Nulls | Null % | Unique Values | Sample Values |
|---|---|---|---|---|---|---|
| `order_id` | `str` | 103,886 | 0 | 0.0% | 99,440 | `b81ef226f3fe1789b1e8b2acac839d17, a9810da82917af2d9aefd1278f1dcfa0` |
| `payment_sequential` | `int64` | 103,886 | 0 | 0.0% | 29 | `1, 1` |
| `payment_type` | `str` | 103,886 | 0 | 0.0% | 5 | `credit_card, credit_card` |
| `payment_installments` | `int64` | 103,886 | 0 | 0.0% | 24 | `8, 1` |
| `payment_value` | `float64` | 103,886 | 0 | 0.0% | 29,077 | `99.33, 24.39` |

**Numerical Distributions Summary**:

| Numeric Column | Min | 25% / Median | Mean | Max | Std Dev |
|---|---|---|---|---|---|
| `payment_sequential` | 1.00 | 1.00 | 1.09 | 29.00 | 0.71 |
| `payment_installments` | 0.00 | 1.00 | 2.85 | 24.00 | 2.69 |
| `payment_value` | 0.00 | 100.00 | 154.10 | 13664.08 | 217.49 |

---

### Table: `olist_order_reviews_dataset.csv`
- **Shape**: 99,224 rows × 7 columns
- **In-Memory Size**: 39.12 MB
- **Exact Duplicate Rows**: 0
- **Strict Unique Single Column (PK Candidate)**: `None`
- **Composite Key Uniqueness Tests**:
  - `(review_id, order_id)`: ✅ Valid (100% Unique & Complete)
- **Critical Profiling & Anomaly Observations**:
  - ⚠️ review_id is NOT unique (found 814 duplicated review_ids across different rows).

**Column Schema & Quality Profile**:

| Column Name | Inferred Dtype | Non-Null | Nulls | Null % | Unique Values | Sample Values |
|---|---|---|---|---|---|---|
| `review_id` | `str` | 99,224 | 0 | 0.0% | 98,410 | `7bc2406110b926393aa56f80a40eba40, 80e641a11e56f04c1ad469d5645fdfde` |
| `order_id` | `str` | 99,224 | 0 | 0.0% | 98,673 | `73fc7af87114b39712e6da79b0a377eb, a548910a1c6147796b98fdf73dbeba33` |
| `review_score` | `int64` | 99,224 | 0 | 0.0% | 5 | `4, 5` |
| `review_comment_title` | `str` | 11,568 | 87,656 | 88.3% | 4,528 | `recomendo, Super recomendo` |
| `review_comment_message` | `str` | 40,977 | 58,247 | 58.7% | 36,160 | `Recebi bem antes do prazo estipulado., Parabéns lojas lannister adorei comprar pela Internet seguro e prático Parabéns a todos feliz Páscoa` |
| `review_creation_date` | `str` | 99,224 | 0 | 0.0% | 636 | `2018-01-18 00:00:00, 2018-03-10 00:00:00` |
| `review_answer_timestamp` | `str` | 99,224 | 0 | 0.0% | 98,248 | `2018-01-18 21:46:59, 2018-03-11 03:05:13` |

**Numerical Distributions Summary**:

| Numeric Column | Min | 25% / Median | Mean | Max | Std Dev |
|---|---|---|---|---|---|
| `review_score` | 1.00 | 5.00 | 4.09 | 5.00 | 1.35 |

**Temporal Boundaries (Date Ranges)**:

| Date Column | Earliest Timestamp | Latest Timestamp | Parsing Issues |
|---|---|---|---|
| `review_creation_date` | 2016-10-02 00:00:00 | 2018-08-31 00:00:00 | 0 |
| `review_answer_timestamp` | 2016-10-07 18:32:28 | 2018-10-29 12:27:35 | 0 |

---

### Table: `olist_orders_dataset.csv`
- **Shape**: 99,441 rows × 8 columns
- **In-Memory Size**: 52.94 MB
- **Exact Duplicate Rows**: 0
- **Strict Unique Single Column (PK Candidate)**: `order_id, customer_id`

**Column Schema & Quality Profile**:

| Column Name | Inferred Dtype | Non-Null | Nulls | Null % | Unique Values | Sample Values |
|---|---|---|---|---|---|---|
| `order_id` | `str` | 99,441 | 0 | 0.0% | 99,441 | `e481f51cbdc54678b7cc49136f2d6af7, 53cdb2fc8bc7dce0b6741e2150273451` |
| `customer_id` | `str` | 99,441 | 0 | 0.0% | 99,441 | `9ef432eb6251297304e76186b10a928d, b0830fb4747a6c6d20dea0b8c802d7ef` |
| `order_status` | `str` | 99,441 | 0 | 0.0% | 8 | `delivered, delivered` |
| `order_purchase_timestamp` | `str` | 99,441 | 0 | 0.0% | 98,875 | `2017-10-02 10:56:33, 2018-07-24 20:41:37` |
| `order_approved_at` | `str` | 99,281 | 160 | 0.2% | 90,734 | `2017-10-02 11:07:15, 2018-07-26 03:24:27` |
| `order_delivered_carrier_date` | `str` | 97,658 | 1,783 | 1.8% | 81,019 | `2017-10-04 19:55:00, 2018-07-26 14:31:00` |
| `order_delivered_customer_date` | `str` | 96,476 | 2,965 | 3.0% | 95,665 | `2017-10-10 21:25:13, 2018-08-07 15:27:45` |
| `order_estimated_delivery_date` | `str` | 99,441 | 0 | 0.0% | 459 | `2017-10-18 00:00:00, 2018-08-13 00:00:00` |

**Temporal Boundaries (Date Ranges)**:

| Date Column | Earliest Timestamp | Latest Timestamp | Parsing Issues |
|---|---|---|---|
| `order_purchase_timestamp` | 2016-09-04 21:15:19 | 2018-10-17 17:30:18 | 0 |
| `order_approved_at` | 2016-09-15 12:16:38 | 2018-09-03 17:40:06 | 0 |
| `order_delivered_carrier_date` | 2016-10-08 10:34:01 | 2018-09-11 19:48:28 | 0 |
| `order_delivered_customer_date` | 2016-10-11 13:46:32 | 2018-10-17 13:22:46 | 0 |
| `order_estimated_delivery_date` | 2016-09-30 00:00:00 | 2018-11-12 00:00:00 | 0 |

---

### Table: `olist_products_dataset.csv`
- **Shape**: 32,951 rows × 9 columns
- **In-Memory Size**: 6.30 MB
- **Exact Duplicate Rows**: 0
- **Strict Unique Single Column (PK Candidate)**: `product_id`

**Column Schema & Quality Profile**:

| Column Name | Inferred Dtype | Non-Null | Nulls | Null % | Unique Values | Sample Values |
|---|---|---|---|---|---|---|
| `product_id` | `str` | 32,951 | 0 | 0.0% | 32,951 | `1e9e8ef04dbcff4541ed26657ea517e5, 3aa071139cb16b67ca9e5dea641aaa2f` |
| `product_category_name` | `str` | 32,341 | 610 | 1.9% | 74 | `perfumaria, artes` |
| `product_name_lenght` | `float64` | 32,341 | 610 | 1.9% | 67 | `40.0, 44.0` |
| `product_description_lenght` | `float64` | 32,341 | 610 | 1.9% | 2,961 | `287.0, 276.0` |
| `product_photos_qty` | `float64` | 32,341 | 610 | 1.9% | 20 | `1.0, 1.0` |
| `product_weight_g` | `float64` | 32,949 | 2 | 0.0% | 2,205 | `225.0, 1000.0` |
| `product_length_cm` | `float64` | 32,949 | 2 | 0.0% | 100 | `16.0, 30.0` |
| `product_height_cm` | `float64` | 32,949 | 2 | 0.0% | 103 | `10.0, 18.0` |
| `product_width_cm` | `float64` | 32,949 | 2 | 0.0% | 96 | `14.0, 20.0` |

**Numerical Distributions Summary**:

| Numeric Column | Min | 25% / Median | Mean | Max | Std Dev |
|---|---|---|---|---|---|
| `product_name_lenght` | 5.00 | 51.00 | 48.48 | 76.00 | 10.25 |
| `product_description_lenght` | 4.00 | 595.00 | 771.50 | 3992.00 | 635.12 |
| `product_photos_qty` | 1.00 | 1.00 | 2.19 | 20.00 | 1.74 |
| `product_weight_g` | 0.00 | 700.00 | 2276.47 | 40425.00 | 4282.04 |
| `product_length_cm` | 7.00 | 25.00 | 30.82 | 105.00 | 16.91 |
| `product_height_cm` | 2.00 | 13.00 | 16.94 | 105.00 | 13.64 |
| `product_width_cm` | 6.00 | 20.00 | 23.20 | 118.00 | 12.08 |

---

### Table: `olist_sellers_dataset.csv`
- **Shape**: 3,095 rows × 4 columns
- **In-Memory Size**: 0.59 MB
- **Exact Duplicate Rows**: 0
- **Strict Unique Single Column (PK Candidate)**: `seller_id`

**Column Schema & Quality Profile**:

| Column Name | Inferred Dtype | Non-Null | Nulls | Null % | Unique Values | Sample Values |
|---|---|---|---|---|---|---|
| `seller_id` | `str` | 3,095 | 0 | 0.0% | 3,095 | `3442f8959a84dea7ee197c632cb2df15, d1b65fc7debc3361ea86b5f14c68d2e2` |
| `seller_zip_code_prefix` | `int64` | 3,095 | 0 | 0.0% | 2,246 | `13023, 13844` |
| `seller_city` | `str` | 3,095 | 0 | 0.0% | 611 | `campinas, mogi guacu` |
| `seller_state` | `str` | 3,095 | 0 | 0.0% | 23 | `SP, SP` |

**Numerical Distributions Summary**:

| Numeric Column | Min | 25% / Median | Mean | Max | Std Dev |
|---|---|---|---|---|---|
| `seller_zip_code_prefix` | 1001.00 | 14940.00 | 32291.06 | 99730.00 | 32713.45 |

---

### Table: `product_category_name_translation.csv`
- **Shape**: 71 rows × 2 columns
- **In-Memory Size**: 0.01 MB
- **Exact Duplicate Rows**: 0
- **Strict Unique Single Column (PK Candidate)**: `product_category_name, product_category_name_english`

**Column Schema & Quality Profile**:

| Column Name | Inferred Dtype | Non-Null | Nulls | Null % | Unique Values | Sample Values |
|---|---|---|---|---|---|---|
| `product_category_name` | `str` | 71 | 0 | 0.0% | 71 | `beleza_saude, informatica_acessorios` |
| `product_category_name_english` | `str` | 71 | 0 | 0.0% | 71 | `health_beauty, computers_accessories` |

---

## 3. High-Priority Data Architecture Takeaways

1. **Order vs Order Item Granularity**: `olist_orders_dataset.csv` contains 99,441 unique orders. However, `olist_order_items_dataset.csv` contains 112,650 line items. Merging items directly with orders without aggregation creates duplicate order records and inflates revenue calculations.
2. **Customer Identity Decoupling**: In `olist_customers_dataset.csv`, `customer_id` is unique per order (99,441), but represents only 96,096 distinct human beings (`customer_unique_id`). Repeat purchase analyses must use `customer_unique_id`.
3. **Duplicate Review IDs Trap**: In `olist_order_reviews_dataset.csv`, `review_id` is NOT unique (total 104,719 rows, but only 98,410 unique review IDs). Some orders generated multiple reviews or a single review surveyed multiple orders.
4. **High-Frequency Coordinate Redundancy**: `olist_geolocation_dataset.csv` has 1,000,164 records with 261,831 exact duplicate rows. Zip code prefixes have hundreds of slightly differing latitude/longitude points that require spatial deduplication.
5. **Order Lifecycle Nulls**: In `olist_orders_dataset.csv`, `order_delivered_customer_date` has 2,965 nulls. These are NOT dirty records; they represent canceled, unavailable, or in-transit orders.