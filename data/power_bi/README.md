# Power BI Data Layer

This directory holds optimized analytical CSV extracts for **Power BI Desktop Import Mode**:

- `fact_order_intelligence.csv`: Unified fact table at the order grain (99,441 rows) with all financial metrics, risk scores, OVI, quadrants, and review sentiment.
- `dim_date.csv`: Comprehensive calendar dimension (774 days) with year, quarter, month, day, and day-of-week attributes.
- `dim_geography.csv`: State-level regional lookup table (27 Brazilian states mapped to 5 macro-regions).
- `dim_seller_summary.csv`: Aggregated merchant profiles (3,086 sellers) with GMV, orders, Danger Zone exposure, and CSAT.
- `dim_category_summary.csv`: Aggregated product category profiles (74 categories) with GMV, net margin, and late delivery rates.

### Regeneration
To regenerate these CSV extracts and deploy SQL views to PostgreSQL, execute:
```bash
python src/marketplace_intelligence/powerbi_export.py
```
