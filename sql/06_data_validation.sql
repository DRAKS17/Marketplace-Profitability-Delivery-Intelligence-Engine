-- ==============================================================================
-- 06_data_validation.sql
-- Database: marketplace_analytics
-- Purpose: Automated Data Quality and Relational Integrity Audit Suite
-- ==============================================================================

-- 1. PRIMARY KEY UNIQUENESS & NULL CHECK ACROSS ALL CORE TABLES
SELECT 'core.dim_customer' AS table_name, COUNT(*) - COUNT(DISTINCT customer_key) AS duplicate_pks, COUNT(*) - COUNT(customer_key) AS null_pks FROM core.dim_customer
UNION ALL
SELECT 'core.dim_seller', COUNT(*) - COUNT(DISTINCT seller_key), COUNT(*) - COUNT(seller_key) FROM core.dim_seller
UNION ALL
SELECT 'core.dim_product', COUNT(*) - COUNT(DISTINCT product_key), COUNT(*) - COUNT(product_key) FROM core.dim_product
UNION ALL
SELECT 'core.dim_date', COUNT(*) - COUNT(DISTINCT date_key), COUNT(*) - COUNT(date_key) FROM core.dim_date
UNION ALL
SELECT 'core.dim_location', COUNT(*) - COUNT(DISTINCT location_key), COUNT(*) - COUNT(location_key) FROM core.dim_location
UNION ALL
SELECT 'core.fact_orders', COUNT(*) - COUNT(DISTINCT order_key), COUNT(*) - COUNT(order_key) FROM core.fact_orders
UNION ALL
SELECT 'core.fact_order_items', COUNT(*) - COUNT(DISTINCT order_item_key), COUNT(*) - COUNT(order_item_key) FROM core.fact_order_items
UNION ALL
SELECT 'core.fact_payments', COUNT(*) - COUNT(DISTINCT payment_key), COUNT(*) - COUNT(payment_key) FROM core.fact_payments
UNION ALL
SELECT 'core.fact_reviews', COUNT(*) - COUNT(DISTINCT review_key), COUNT(*) - COUNT(review_key) FROM core.fact_reviews;

-- 2. FOREIGN KEY REFERENTIAL INTEGRITY (ORPHAN RECORD DETECTOR)
-- All queries must return 0 orphan records
SELECT 'fact_orders -> dim_customer' AS fk_relationship, COUNT(*) AS orphan_count
FROM core.fact_orders o
LEFT JOIN core.dim_customer c ON o.customer_key = c.customer_key
WHERE c.customer_key IS NULL
UNION ALL
SELECT 'fact_orders -> dim_date', COUNT(*)
FROM core.fact_orders o
LEFT JOIN core.dim_date d ON o.purchase_date_key = d.date_key
WHERE d.date_key IS NULL
UNION ALL
SELECT 'fact_order_items -> dim_seller', COUNT(*)
FROM core.fact_order_items i
LEFT JOIN core.dim_seller s ON i.seller_key = s.seller_key
WHERE s.seller_key IS NULL
UNION ALL
SELECT 'fact_order_items -> dim_product', COUNT(*)
FROM core.fact_order_items i
LEFT JOIN core.dim_product p ON i.product_key = p.product_key
WHERE p.product_key IS NULL;

-- 3. FINANCIAL INTEGRITY AUDIT (ZERO FANOUT PROOF)
-- Difference must equal exactly 0.00
SELECT 
    ROUND(SUM(o.order_total_item_value), 2) AS fact_orders_gmv,
    ROUND(SUM(i.price), 2) AS fact_order_items_gmv,
    ROUND(ABS(SUM(o.order_total_item_value) - SUM(i.price)), 2) AS gmv_discrepancy
FROM core.fact_orders o
FULL JOIN (
    SELECT ROUND(SUM(price), 2) AS price FROM core.fact_order_items
) i ON 1=1;

-- 4. LOGICAL DATE VALIDATION
-- Check for orders where actual customer delivery preceded carrier dispatch
SELECT 
    COUNT(*) AS illogical_delivery_count
FROM core.fact_orders
WHERE order_delivered_carrier_date IS NOT NULL 
  AND order_delivered_customer_date IS NOT NULL 
  AND order_delivered_customer_date < order_delivered_carrier_date;
