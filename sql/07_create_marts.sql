-- ==============================================================================
-- 07_create_marts.sql
-- Database: marketplace_analytics
-- Purpose: Create analytical mart tables and business risk views (Phase 13)
-- ==============================================================================

-- 1. CREATE MART.ORDER_RISK_PROFILE
DROP TABLE IF EXISTS mart.order_risk_profile CASCADE;

CREATE TABLE mart.order_risk_profile (
    order_id VARCHAR(32) PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL,
    seller_id VARCHAR(32),
    primary_product_category VARCHAR(100),
    customer_state VARCHAR(2),
    seller_state VARCHAR(2),
    order_total_item_value NUMERIC(10, 2) NOT NULL,
    order_total_freight_value NUMERIC(10, 2) NOT NULL,
    order_total_value NUMERIC(10, 2) NOT NULL,
    freight_ratio NUMERIC(5, 4),
    haversine_distance_km NUMERIC(10, 2),
    is_interstate_delivery BOOLEAN,
    predicted_late_probability NUMERIC(5, 4) NOT NULL,
    delay_risk_score NUMERIC(5, 2) NOT NULL,
    freight_friction_score NUMERIC(5, 2) NOT NULL,
    merchant_unreliability_score NUMERIC(5, 2) NOT NULL,
    route_complexity_score NUMERIC(5, 2) NOT NULL,
    operational_vulnerability_index NUMERIC(5, 2) NOT NULL,
    vulnerability_tier VARCHAR(50) NOT NULL,
    gross_platform_revenue_brl NUMERIC(10, 2) NOT NULL,
    payment_processing_fee_brl NUMERIC(10, 2) NOT NULL,
    expected_late_remedy_cost_brl NUMERIC(10, 2) NOT NULL,
    expected_net_contribution_brl NUMERIC(10, 2) NOT NULL,
    profitability_tier VARCHAR(50) NOT NULL,
    strategic_quadrant VARCHAR(100) NOT NULL,
    actual_is_delivered BOOLEAN,
    actual_is_late_delivery NUMERIC(2, 1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optimization indexes for BI and analytical queries
CREATE INDEX idx_risk_quadrant ON mart.order_risk_profile(strategic_quadrant);
CREATE INDEX idx_risk_vuln_tier ON mart.order_risk_profile(vulnerability_tier);
CREATE INDEX idx_risk_profit_tier ON mart.order_risk_profile(profitability_tier);
CREATE INDEX idx_risk_seller ON mart.order_risk_profile(seller_id);
CREATE INDEX idx_risk_category ON mart.order_risk_profile(primary_product_category);

-- ------------------------------------------------------------------------------
-- 2. EXECUTIVE ANALYTICAL VIEWS
-- ------------------------------------------------------------------------------

-- View A: Strategic Profit-Risk Quadrant Executive Summary
CREATE OR REPLACE VIEW mart.view_quadrant_executive_summary AS
SELECT 
    strategic_quadrant,
    COUNT(order_id) AS total_orders,
    ROUND(COUNT(order_id)::NUMERIC / SUM(COUNT(order_id)) OVER () * 100.0, 2) AS order_share_pct,
    ROUND(SUM(order_total_item_value), 2) AS total_gmv_brl,
    ROUND(SUM(order_total_item_value)::NUMERIC / SUM(SUM(order_total_item_value)) OVER () * 100.0, 2) AS gmv_share_pct,
    ROUND(AVG(order_total_item_value), 2) AS avg_basket_gmv_brl,
    ROUND(AVG(operational_vulnerability_index), 2) AS avg_vulnerability_index,
    ROUND(AVG(expected_net_contribution_brl), 2) AS avg_expected_contribution_brl,
    ROUND(SUM(expected_net_contribution_brl), 2) AS total_expected_contribution_brl,
    ROUND(AVG(CASE WHEN actual_is_delivered = TRUE THEN actual_is_late_delivery ELSE NULL END) * 100.0, 2) AS actual_late_rate_pct
FROM mart.order_risk_profile
GROUP BY strategic_quadrant
ORDER BY total_gmv_brl DESC;

-- View B: Merchant Operational Risk Profile
CREATE OR REPLACE VIEW mart.view_seller_risk_exposure AS
SELECT 
    seller_id,
    COUNT(order_id) AS total_orders,
    ROUND(SUM(order_total_item_value), 2) AS total_gmv_brl,
    ROUND(AVG(operational_vulnerability_index), 2) AS avg_seller_ovi,
    COUNT(CASE WHEN strategic_quadrant LIKE 'Q2%' THEN 1 END) AS danger_zone_orders,
    ROUND(COUNT(CASE WHEN strategic_quadrant LIKE 'Q2%' THEN 1 END)::NUMERIC / COUNT(order_id) * 100.0, 2) AS danger_zone_pct,
    COUNT(CASE WHEN strategic_quadrant LIKE 'Q1%' THEN 1 END) AS crown_jewel_orders,
    ROUND(AVG(CASE WHEN actual_is_delivered = TRUE THEN actual_is_late_delivery ELSE NULL END) * 100.0, 2) AS actual_late_delivery_pct
FROM mart.order_risk_profile
WHERE seller_id IS NOT NULL
GROUP BY seller_id
HAVING COUNT(order_id) >= 50
ORDER BY danger_zone_pct DESC;

-- View C: Category Operational Risk Profile
CREATE OR REPLACE VIEW mart.view_category_risk_profile AS
SELECT 
    primary_product_category,
    COUNT(order_id) AS total_orders,
    ROUND(SUM(order_total_item_value), 2) AS total_gmv_brl,
    ROUND(AVG(freight_ratio) * 100.0, 2) AS avg_freight_ratio_pct,
    ROUND(AVG(operational_vulnerability_index), 2) AS avg_category_ovi,
    ROUND(SUM(expected_net_contribution_brl), 2) AS total_expected_contribution_brl,
    ROUND(AVG(CASE WHEN actual_is_delivered = TRUE THEN actual_is_late_delivery ELSE NULL END) * 100.0, 2) AS actual_late_delivery_pct
FROM mart.order_risk_profile
WHERE primary_product_category IS NOT NULL
GROUP BY primary_product_category
HAVING COUNT(order_id) >= 100
ORDER BY total_gmv_brl DESC;
