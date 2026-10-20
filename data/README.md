# Data Architecture & Storage Guidelines

This directory houses all local data assets for the **Marketplace Profitability & Delivery Intelligence Engine**.

---

## 1. Directory Structure

```text
data/
├── raw/         <- Immutable, read-only original dataset directly as downloaded.
├── processed/   <- Cleaned, transformed, and feature-engineered datasets ready for modeling or staging.
└── external/    <- Supplemental third-party reference data (e.g. IBGE codes, regional classifications).
```

---

## 2. Dataset Attribution & Source

- **Dataset Name**: Brazilian E-Commerce Public Dataset by Olist
- **Publisher**: Olist & Kaggle
- **URL**: [https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- **License**: **CC BY-NC-SA 4.0** (Attribution-NonCommercial-ShareAlike 4.0 International)
  - You are free to share and adapt the material for non-commercial purposes.
  - You must give appropriate credit and provide a link to the license.

---

## 3. Expected Files in `data/raw/`

The raw Olist dataset contains 9 relational CSV files covering ~100k Brazilian e-commerce orders from 2016 to 2018:

| # | Filename | Description |
|---|---|---|
| 1 | `olist_customers_dataset.csv` | Customer identifiers, unique IDs, and zip codes |
| 2 | `olist_geolocation_dataset.csv` | Brazilian zip code prefixes with lat/long and state mappings |
| 3 | `olist_order_items_dataset.csv` | Line-item level details (price, freight, seller, product, shipping limits) |
| 4 | `olist_order_payments_dataset.csv` | Payment methods, installments, and payment values |
| 5 | `olist_order_reviews_dataset.csv` | Customer ratings (1-5), review titles, comments, and survey timestamps |
| 6 | `olist_orders_dataset.csv` | Core order lifecycle: status and operational timestamps |
| 7 | `olist_products_dataset.csv` | Product metadata: categories, weight, dimensions, photo counts |
| 8 | `olist_sellers_dataset.csv` | Seller identifiers, zip codes, cities, and states |
| 9 | `product_category_name_translation.csv` | Portuguese-to-English translation mapping for product categories |

---

## 4. Engineering Principles: The Raw Data Contract

1. **Immutability**: Files inside `data/raw/` must **never** be manually modified, overwritten, or resaved in Excel/Notepad. Excel often reformats dates or corrupts leading zeroes in zip codes.
2. **Reproducibility**: If any pipeline step fails or downstream artifacts become corrupt, the entire system can be re-run deterministically from the raw files.
3. **Traceability**: Separating raw and processed data ensures that transformations, imputations, and joins can always be audited against original truth.
4. **Git Hygiene**: Raw CSV files are excluded from Git version control via `.gitignore` to prevent repository bloat and potential licensing or secret leakage issues.
