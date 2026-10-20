-- ==============================================================================
-- 08_power_bi_views.sql
-- Database: marketplace_analytics
-- Purpose: Optimized SQL Mart Views for Power BI Desktop DirectQuery / Import
-- ==============================================================================

-- 1. VIEW: POWER BI UNIFIED ORDER INTELLIGENCE
CREATE OR REPLACE VIEW mart.view_powerbi_orders AS
SELECT 
    r.order_id,
    r.customer_id,
    r.seller_id,
    r.primary_product_category,
    r.customer_state,
    CASE 
        WHEN r.customer_state IN ('SP', 'RJ', 'MG', 'ES') THEN 'Southeast'
        WHEN r.customer_state IN ('PR', 'SC', 'RS') THEN 'South'
        WHEN r.customer_state IN ('BA', 'PE', 'CE', 'MA', 'PB', 'RN', 'AL', 'SE', 'PI') THEN 'Northeast'
        WHEN r.customer_state IN ('DF', 'GO', 'MT', 'MS') THEN 'Central-West'
        WHEN r.customer_state IN ('AM', 'PA', 'RO', 'AC', 'TO', 'AP', 'RR') THEN 'North'
        ELSE 'Other'
    END AS customer_macro_region,
    r.seller_state,
    r.order_total_item_value AS gmv_brl,
    r.order_total_freight_value AS freight_brl,
    r.order_total_value AS total_order_value_brl,
    r.freight_ratio,
    r.haversine_distance_km,
    r.is_interstate_delivery,
    r.predicted_late_probability,
    r.operational_vulnerability_index AS ovi_score,
    r.vulnerability_tier,
    r.gross_platform_revenue_brl,
    r.payment_processing_fee_brl,
    r.expected_late_remedy_cost_brl,
    r.expected_net_contribution_brl,
    r.profitability_tier,
    r.strategic_quadrant,
    r.actual_is_delivered,
    r.actual_is_late_delivery,
    f.order_purchase_timestamp,
    f.order_purchase_timestamp::date AS purchase_date,
    TO_CHAR(f.order_purchase_timestamp, 'YYYY-MM') AS purchase_year_month,
    f.estimated_delivery_duration_days,
    f.seller_dispatch_duration_hours,
    f.carrier_transit_duration_days,
    f.delivery_delay_days,
    rev.review_score,
    rev.csat_category,
    rev.is_delivery_issue,
    rev.is_product_quality_issue,
    rev.is_positive_experience
FROM mart.order_risk_profile r
JOIN core.fact_orders f ON r.order_id = f.order_id
LEFT JOIN (
    -- Deduplicate reviews to single order grain
    SELECT 
        order_id,
        MIN(review_score) AS review_score,
        MIN(csat_category) AS csat_category,
        BOOL_OR(is_delivery_issue) AS is_delivery_issue,
        BOOL_OR(is_product_quality_issue) AS is_product_quality_issue,
        BOOL_OR(is_positive_experience) AS is_positive_experience
    FROM core.fact_reviews
    GROUP BY order_id
) rev ON r.order_id = rev.order_id;

-- 2. VIEW: MONTHLY EXECUTIVE TREND FOR TIME-SERIES VISUALS
CREATE OR REPLACE VIEW mart.view_powerbi_monthly_trend AS
SELECT 
    TO_CHAR(f.order_purchase_timestamp, 'YYYY-MM') AS year_month,
    DATE_TRUNC('month', f.order_purchase_timestamp)::date AS month_start_date,
    COUNT(r.order_id) AS total_orders,
    ROUND(SUM(r.order_total_item_value), 2) AS total_gmv_brl,
    ROUND(SUM(r.gross_platform_revenue_brl), 2) AS total_gross_revenue_brl,
    ROUND(SUM(r.expected_net_contribution_brl), 2) AS total_net_contribution_brl,
    ROUND((SUM(r.expected_net_contribution_brl) / NULLIF(SUM(r.order_total_item_value), 0)) * 100.0, 2) AS effective_take_rate_pct,
    ROUND(AVG(r.operational_vulnerability_index), 2) AS avg_ovi,
    ROUND(AVG(CASE WHEN r.actual_is_delivered = TRUE THEN r.actual_is_late_delivery ELSE NULL END) * 100.0, 2) AS actual_late_rate_pct,
    COUNT(CASE WHEN r.strategic_quadrant LIKE 'Q1%' THEN 1 END) AS q1_crown_jewel_orders,
    COUNT(CASE WHEN r.strategic_quadrant LIKE 'Q2%' THEN 1 END) AS q2_danger_zone_orders,
    COUNT(CASE WHEN r.strategic_quadrant LIKE 'Q3%' THEN 1 END) AS q3_value_drain_orders,
    COUNT(CASE WHEN r.strategic_quadrant LIKE 'Q4%' THEN 1 END) AS q4_steady_workhorse_orders
FROM mart.order_risk_profile r
JOIN core.fact_orders f ON r.order_id = f.order_id
GROUP BY 1, 2
ORDER BY 2 ASC;

-- 3. VIEW: REGIONAL LOGISTICS & CORRIDOR PERFORMANCE
CREATE OR REPLACE VIEW mart.view_powerbi_regional_logistics AS
SELECT 
    r.customer_state,
    CASE 
        WHEN r.customer_state IN ('SP', 'RJ', 'MG', 'ES') THEN 'Southeast'
        WHEN r.customer_state IN ('PR', 'SC', 'RS') THEN 'South'
        WHEN r.customer_state IN ('BA', 'PE', 'CE', 'MA', 'PB', 'RN', 'AL', 'SE', 'PI') THEN 'Northeast'
        WHEN r.customer_state IN ('DF', 'GO', 'MT', 'MS') THEN 'Central-West'
        WHEN r.customer_state IN ('AM', 'PA', 'RO', 'AC', 'TO', 'AP', 'RR') THEN 'North'
        ELSE 'Other'
    END AS customer_macro_region,
    COUNT(r.order_id) AS total_orders,
    ROUND(SUM(r.order_total_item_value), 2) AS total_gmv_brl,
    ROUND(AVG(r.freight_ratio) * 100.0, 2) AS avg_freight_ratio_pct,
    ROUND(AVG(f.carrier_transit_duration_days), 2) AS avg_carrier_transit_days,
    ROUND(AVG(f.delivery_delay_days), 2) AS avg_delivery_delay_days,
    ROUND(AVG(CASE WHEN r.actual_is_delivered = TRUE THEN r.actual_is_late_delivery ELSE NULL END) * 100.0, 2) AS actual_late_rate_pct,
    ROUND(AVG(r.operational_vulnerability_index), 2) AS avg_ovi
FROM mart.order_risk_profile r
JOIN core.fact_orders f ON r.order_id = f.order_id
GROUP BY 1, 2
ORDER BY total_orders DESC;
