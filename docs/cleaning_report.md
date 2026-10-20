# Data Cleaning & Quality Control Audit Report

**Engine**: `src/marketplace_intelligence/cleaning.py`  
**Standard**: Production-Grade Analytical Cleaning & Imputation  
**Destination**: `data/processed/*.parquet` and `data/processed/*.csv`  

---

## 1. Before & After Row Count Summary

| Entity / Dataset | Raw Rows | Cleaned Rows | Rows Dropped | Net Retention % |
|---|---|---|---|---|
| `geolocation` | 1,000,163 | 19,010 | 981,153 | 1.90% |
| `customers` | 99,441 | 99,441 | 0 | 100.00% |
| `sellers` | 3,095 | 3,095 | 0 | 100.00% |
| `products` | 32,951 | 32,951 | 0 | 100.00% |
| `orders` | 99,441 | 99,441 | 0 | 100.00% |
| `order_items` | 112,650 | 112,650 | 0 | 100.00% |
| `order_payments` | 103,886 | 103,886 | 0 | 100.00% |
| `order_reviews` | 99,224 | 99,224 | 0 | 100.00% |

---

## 2. Table-by-Table Cleaning Log & Business Justifications

### Entity: `geolocation`
- **Raw Count**: 1,000,163 rows
- **Cleaned Count**: 19,010 rows
- **Transformations & Data Quality Decisions**:
  - Dropped 261,831 exact duplicate rows.
  - Removed 33 coordinate records falling outside Brazilian territory.
  - Aggregated coordinates to postal prefix centroid (Reduced from 738,299 to 19,010 unique prefixes).

### Entity: `customers`
- **Raw Count**: 99,441 rows
- **Cleaned Count**: 99,441 rows
- **Transformations & Data Quality Decisions**:
  - Trimmed whitespace and normalized customer city to lowercase and state to uppercase.
  - Verified customer_id uniqueness (99,441 unique tokens) and 0 nulls.

### Entity: `sellers`
- **Raw Count**: 3,095 rows
- **Cleaned Count**: 3,095 rows
- **Transformations & Data Quality Decisions**:
  - Standardized seller city and state strings.
  - Verified seller_id uniqueness (3,095 sellers) and 0 nulls.

### Entity: `products`
- **Raw Count**: 32,951 rows
- **Cleaned Count**: 32,951 rows
- **Transformations & Data Quality Decisions**:
  - Mapped manual English translations for 'portateis_cozinha_e_preparadores_de_alimentos' and 'pc_gamer'.
  - Imputed 610 missing product categories with explicit 'outros' / 'others'.
  - Imputed 2 missing values in 'product_weight_g' using category group median.
  - Imputed 2 missing values in 'product_length_cm' using category group median.
  - Imputed 2 missing values in 'product_height_cm' using category group median.
  - Imputed 2 missing values in 'product_width_cm' using category group median.

### Entity: `orders`
- **Raw Count**: 99,441 rows
- **Cleaned Count**: 99,441 rows
- **Transformations & Data Quality Decisions**:
  - Parsed 5 lifecycle timestamp columns into datetime64[ns]. Preserved 2,965 structural delivery nulls.
  - Standardized order_status values.

### Entity: `order_items`
- **Raw Count**: 112,650 rows
- **Cleaned Count**: 112,650 rows
- **Transformations & Data Quality Decisions**:
  - Identified and flagged 383 promotional free-shipping records (freight = 0.0).

### Entity: `order_payments`
- **Raw Count**: 103,886 rows
- **Cleaned Count**: 103,886 rows
- **Transformations & Data Quality Decisions**:
  - Imputed 2 records where installments was 0 to minimum 1 installment.
  - Flagged 9 voided / zero-value payment transactions.

### Entity: `order_reviews`
- **Raw Count**: 99,224 rows
- **Cleaned Count**: 99,224 rows
- **Transformations & Data Quality Decisions**:
  - Created boolean presence indicators 'has_comment_title' and 'has_comment_message' without fabricating text.

---

## 3. Core Cleaning Decisions & Methodological Rigor

1. **Preservation of Structural Nulls**: Order delivery dates were explicitly **not** filled with zeros or medians. Filling them would convert 2,965 undelivered/canceled orders into fulfilled orders, corrupting fulfillment SLA metrics.
2. **Spatial Centroid Aggregation**: Geolocation coordinates were reduced from 1,000,163 noisy GPS readings down to 19,015 unique postal centroids using median coordinates and modal municipality labels, while filtering out coordinates outside Brazilian boundaries.
3. **Missing Category Handling**: Imputed 610 missing product categories with explicit `'outros'` / `'others'` rather than guessing categories, preserving audit integrity.
4. **Manual Category Translations**: Resolved the two missing Portuguese categories (`portateis_cozinha_e_preparadores_de_alimentos` $\rightarrow$ `small_appliances_food_preparation`, `pc_gamer` $\rightarrow$ `pc_gamer`).
5. **Free Shipping vs Corrupt Freight**: Verified that 383 records with `freight_value = 0.0` represent legitimate marketplace free shipping promotions and preserved them with an explicit `is_free_shipping` boolean flag.
6. **Review Text Integrity**: Preserved missing review comments as explicit nulls while adding `has_comment_title` and `has_comment_message` boolean indicators, avoiding textual hallucination.