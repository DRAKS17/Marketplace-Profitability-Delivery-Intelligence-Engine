-- ==============================================================================
-- 05_business_analysis.sql
-- Database: marketplace_analytics
-- Purpose: Advanced SQL Business Intelligence and Analytical Engineering
-- Demonstrates: CTEs, Window Functions (ROW_NUMBER, DENSE_RANK, LAG, LEAD, NTILE,
--               Running Totals, Rolling Averages), Conditional Aggregation, and Cohorts
-- ==============================================================================

-- ==============================================================================
-- 1. MONTHLY GMV, MOM GROWTH & 3-MONTH ROLLING AVERAGE
-- Business Question: What is our monthly marketplace GMV, MoM growth velocity,
-- and 3-month moving average to smooth out seasonal volatility?
-- ==============================================================================
WITH monthly_metrics AS (
    SELECT 
        d.year,
        d.month,
        TO_CHAR(MIN(d.full_date), 'YYYY-MM') AS year_month,
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(SUM(o.order_total_item_value), 2) AS monthly_gmv,
        ROUND(SUM(o.order_total_freight_value), 2) AS monthly_freight
    FROM core.fact_orders o
    JOIN core.dim_date d ON o.purchase_date_key = d.date_key
    WHERE o.order_status = 'delivered'
    GROUP BY d.year, d.month
),
mom_calc AS (
    SELECT 
        year_month,
        total_orders,
        monthly_gmv,
        monthly_freight,
        LAG(monthly_gmv, 1) OVER (ORDER BY year_month) AS prev_month_gmv,
        -- 3-Month Moving Average (Current month + 2 preceding months)
        ROUND(AVG(monthly_gmv) OVER (
            ORDER BY year_month 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 2) AS gmv_3month_rolling_avg
    FROM monthly_metrics
)
SELECT 
    year_month,
    total_orders,
    monthly_gmv,
    prev_month_gmv,
    ROUND(((monthly_gmv - prev_month_gmv) / NULLIF(prev_month_gmv, 0)) * 100.0, 2) AS mom_growth_pct,
    gmv_3month_rolling_avg
FROM mom_calc
ORDER BY year_month;


-- ==============================================================================
-- 2. SELLER REVENUE CONCENTRATION & PARETO ANALYSIS (80/20 RULE)
-- Business Question: What percentage of our sellers generate 80% of our marketplace GMV?
-- Demonstrates: Running Totals (Window SUM), DENSE_RANK, and Cumulative Percentages
-- ==============================================================================
WITH seller_gmv AS (
    SELECT 
        s.seller_id,
        s.seller_city,
        s.seller_state,
        COUNT(DISTINCT i.order_id) AS orders_fulfilled,
        ROUND(SUM(i.price), 2) AS total_seller_gmv
    FROM core.fact_order_items i
    JOIN core.dim_seller s ON i.seller_key = s.seller_key
    GROUP BY s.seller_id, s.seller_city, s.seller_state
),
ranked_sellers AS (
    SELECT 
        seller_id,
        seller_city,
        seller_state,
        orders_fulfilled,
        total_seller_gmv,
        DENSE_RANK() OVER (ORDER BY total_seller_gmv DESC) AS revenue_rank,
        SUM(total_seller_gmv) OVER (ORDER BY total_seller_gmv DESC) AS cumulative_gmv,
        SUM(total_seller_gmv) OVER () AS marketplace_total_gmv,
        COUNT(*) OVER () AS total_seller_count
    FROM seller_gmv
)
SELECT 
    revenue_rank,
    seller_id,
    seller_city,
    seller_state,
    orders_fulfilled,
    total_seller_gmv,
    ROUND((cumulative_gmv / marketplace_total_gmv) * 100.0, 2) AS cumulative_gmv_pct,
    ROUND((revenue_rank::NUMERIC / total_seller_count) * 100.0, 2) AS cumulative_seller_pct,
    CASE 
        WHEN (cumulative_gmv / marketplace_total_gmv) <= 0.80 THEN 'Top 80% GMV Driver'
        ELSE 'Long Tail Merchant'
    END AS pareto_tier
FROM ranked_sellers
ORDER BY revenue_rank
LIMIT 25;


-- ==============================================================================
-- 3. TOP 3 PRODUCT CATEGORIES WITHIN EACH BRAZILIAN STATE
-- Business Question: What are the top 3 best-selling product categories by revenue
-- within each destination Brazilian state?
-- Demonstrates: DENSE_RANK() OVER (PARTITION BY ... ORDER BY ...)
-- ==============================================================================
WITH state_category_gmv AS (
    SELECT 
        c.customer_state,
        p.product_category_name_english AS category,
        COUNT(DISTINCT i.order_id) AS orders_count,
        ROUND(SUM(i.price), 2) AS category_gmv
    FROM core.fact_order_items i
    JOIN core.dim_customer c ON i.customer_key = c.customer_key
    JOIN core.dim_product p ON i.product_key = p.product_key
    GROUP BY c.customer_state, p.product_category_name_english
),
ranked_categories AS (
    SELECT 
        customer_state,
        category,
        orders_count,
        category_gmv,
        DENSE_RANK() OVER (
            PARTITION BY customer_state 
            ORDER BY category_gmv DESC
        ) AS category_rank_in_state
    FROM state_category_gmv
)
SELECT 
    customer_state,
    category_rank_in_state,
    category,
    orders_count,
    category_gmv
FROM ranked_categories
WHERE category_rank_in_state <= 3
ORDER BY customer_state, category_rank_in_state;


-- ==============================================================================
-- 4. CUSTOMER ACQUISITION COHORTS & MONTHLY LIFETIME RETENTION
-- Business Question: How do customer cohorts behave over time? Do customers acquired
-- in earlier months continue purchasing in subsequent months?
-- Demonstrates: Minimum Acquisition Date per Customer, Cohort Age Index, and CTEs
-- ==============================================================================
WITH customer_first_purchase AS (
    SELECT 
        c.customer_unique_id,
        MIN(d.full_date) AS first_purchase_date,
        TO_CHAR(MIN(d.full_date), 'YYYY-MM') AS cohort_month
    FROM core.fact_orders o
    JOIN core.dim_customer c ON o.customer_key = c.customer_key
    JOIN core.dim_date d ON o.purchase_date_key = d.date_key
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
customer_orders AS (
    SELECT 
        c.customer_unique_id,
        fp.cohort_month,
        TO_CHAR(d.full_date, 'YYYY-MM') AS order_month,
        (EXTRACT(YEAR FROM d.full_date) - EXTRACT(YEAR FROM fp.first_purchase_date)) * 12 +
        (EXTRACT(MONTH FROM d.full_date) - EXTRACT(MONTH FROM fp.first_purchase_date)) AS cohort_index,
        o.order_total_item_value AS gmv
    FROM core.fact_orders o
    JOIN core.dim_customer c ON o.customer_key = c.customer_key
    JOIN core.dim_date d ON o.purchase_date_key = d.date_key
    JOIN customer_first_purchase fp ON c.customer_unique_id = fp.customer_unique_id
    WHERE o.order_status = 'delivered'
)
SELECT 
    cohort_month,
    cohort_index,
    COUNT(DISTINCT customer_unique_id) AS active_customers,
    ROUND(SUM(gmv), 2) AS cohort_gmv
FROM customer_orders
WHERE cohort_month BETWEEN '2017-01' AND '2017-06'
  AND cohort_index <= 6
GROUP BY cohort_month, cohort_index
ORDER BY cohort_month, cohort_index;


-- ==============================================================================
-- 5. REPEAT PURCHASE VELOCITY & REPURCHASE INTERVAL (DAYS BETWEEN ORDERS)
-- Business Question: For customers who make multiple purchases, what is the average
-- and median time (in days) between consecutive orders?
-- Demonstrates: LAG() OVER (PARTITION BY customer ORDER BY purchase_time)
-- ==============================================================================
WITH repeat_orders AS (
    SELECT 
        c.customer_unique_id,
        o.order_id,
        o.order_purchase_timestamp,
        LAG(o.order_purchase_timestamp) OVER (
            PARTITION BY c.customer_unique_id 
            ORDER BY o.order_purchase_timestamp
        ) AS prev_purchase_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY c.customer_unique_id 
            ORDER BY o.order_purchase_timestamp
        ) AS customer_order_sequence
    FROM core.fact_orders o
    JOIN core.dim_customer c ON o.customer_key = c.customer_key
    WHERE o.order_status = 'delivered'
),
intervals AS (
    SELECT 
        customer_unique_id,
        customer_order_sequence,
        EXTRACT(EPOCH FROM (order_purchase_timestamp - prev_purchase_timestamp)) / 86400.0 AS days_between_orders
    FROM repeat_orders
    WHERE prev_purchase_timestamp IS NOT NULL
)
SELECT 
    customer_order_sequence AS order_transition_number,
    COUNT(*) AS repeat_events_count,
    ROUND(AVG(days_between_orders)::NUMERIC, 1) AS avg_days_to_repurchase,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY days_between_orders)::NUMERIC, 1) AS median_days_to_repurchase,
    ROUND(MIN(days_between_orders)::NUMERIC, 1) AS min_days,
    ROUND(MAX(days_between_orders)::NUMERIC, 1) AS max_days
FROM intervals
GROUP BY customer_order_sequence
ORDER BY customer_order_sequence;


-- ==============================================================================
-- 6. LATE DELIVERY PERFORMANCE BY SHIPPING DISTANCE QUARTILE
-- Business Question: Does shipping distance cause delivery delays? How does late delivery
-- rate scale across Haversine distance quartiles?
-- Demonstrates: NTILE(4), Conditional Aggregation, and SLA Duration Calculations
-- ==============================================================================
WITH distance_binned AS (
    SELECT 
        order_id,
        haversine_distance_km,
        is_interstate_delivery,
        is_late_delivery,
        delivery_delay_days,
        actual_delivery_duration_days,
        NTILE(4) OVER (ORDER BY haversine_distance_km) AS distance_quartile
    FROM core.fact_orders
    WHERE is_delivered = TRUE AND haversine_distance_km IS NOT NULL
)
SELECT 
    distance_quartile,
    ROUND(MIN(haversine_distance_km)::NUMERIC, 1) AS min_distance_km,
    ROUND(MAX(haversine_distance_km)::NUMERIC, 1) AS max_distance_km,
    COUNT(*) AS total_delivered_orders,
    ROUND(AVG(haversine_distance_km)::NUMERIC, 1) AS avg_distance_km,
    ROUND(AVG(actual_delivery_duration_days)::NUMERIC, 1) AS avg_delivery_days,
    COUNT(CASE WHEN is_late_delivery THEN 1 END) AS late_orders_count,
    ROUND(
        (COUNT(CASE WHEN is_late_delivery THEN 1 END)::NUMERIC / COUNT(*)) * 100.0, 
        2
    ) AS late_delivery_rate_pct,
    ROUND(AVG(CASE WHEN is_late_delivery THEN delivery_delay_days END)::NUMERIC, 1) AS avg_days_delayed_when_late
FROM distance_binned
GROUP BY distance_quartile
ORDER BY distance_quartile;


-- ==============================================================================
-- 7. CUSTOMER REVIEW SENTIMENT & STAR RATING IMPACT OF LATE DELIVERIES
-- Business Question: How severely does a late delivery destroy customer satisfaction (CSAT)
-- and trigger qualitative operational complaints?
-- Demonstrates: Multi-table Fact Joins, Star Score Breakdown, and NLP Keyword Tagging
-- ==============================================================================
SELECT 
    CASE 
        WHEN o.is_late_delivery = TRUE THEN 'Late Delivery (SLA Breached)'
        WHEN o.is_late_delivery = FALSE THEN 'On-Time Delivery'
        ELSE 'Undelivered / In-Transit'
    END AS fulfillment_outcome,
    COUNT(DISTINCT r.review_key) AS total_reviews,
    ROUND(AVG(r.review_score), 2) AS average_review_score,
    ROUND(
        (COUNT(CASE WHEN r.review_score = 1 THEN 1 END)::NUMERIC / COUNT(*)) * 100.0, 
        2
    ) AS one_star_pct,
    ROUND(
        (COUNT(CASE WHEN r.review_score = 5 THEN 1 END)::NUMERIC / COUNT(*)) * 100.0, 
        2
    ) AS five_star_pct,
    COUNT(CASE WHEN r.is_delivery_issue THEN 1 END) AS explicit_delay_complaints,
    ROUND(
        (COUNT(CASE WHEN r.is_delivery_issue THEN 1 END)::NUMERIC / COUNT(*)) * 100.0, 
        2
    ) AS delay_complaint_rate_pct
FROM core.fact_orders o
JOIN core.fact_reviews r ON o.order_id = r.order_id
GROUP BY 
    CASE 
        WHEN o.is_late_delivery = TRUE THEN 'Late Delivery (SLA Breached)'
        WHEN o.is_late_delivery = FALSE THEN 'On-Time Delivery'
        ELSE 'Undelivered / In-Transit'
    END
ORDER BY average_review_score DESC;


-- ==============================================================================
-- 8. FREIGHT-TO-PRICE RATIO & FRICTION BY PRODUCT CATEGORY
-- Business Question: In which product categories do customers pay disproportionately
-- high shipping fees relative to merchandise value?
-- Demonstrates: Weighted Averages, PERCENT_RANK(), and Cost Friction
-- ==============================================================================
WITH category_freight AS (
    SELECT 
        p.product_category_name_english AS category,
        COUNT(DISTINCT i.order_id) AS orders_count,
        ROUND(SUM(i.price), 2) AS total_gmv,
        ROUND(SUM(i.freight_value), 2) AS total_freight,
        ROUND((SUM(i.freight_value) / NULLIF(SUM(i.price), 0)) * 100.0, 2) AS freight_to_price_ratio_pct
    FROM core.fact_order_items i
    JOIN core.dim_product p ON i.product_key = p.product_key
    GROUP BY p.product_category_name_english
    HAVING COUNT(DISTINCT i.order_id) >= 100 -- Focus on statistically significant categories
)
SELECT 
    category,
    orders_count,
    total_gmv,
    total_freight,
    freight_to_price_ratio_pct,
    ROUND(
        PERCENT_RANK() OVER (ORDER BY freight_to_price_ratio_pct DESC)::NUMERIC, 
        2
    ) AS friction_percentile_rank
FROM category_freight
ORDER BY freight_to_price_ratio_pct DESC
LIMIT 20;


-- ==============================================================================
-- 9. SELLER FULFILLMENT DISPATCH COMPLIANCE & IMPACT ON DOORSTEP SLA
-- Business Question: What percentage of orders experience seller dispatch delays,
-- and how much does a seller delay increase the final customer late delivery rate?
-- Demonstrates: Cross-Stage SLA Analysis and Conditional Probability
-- ==============================================================================
SELECT 
    CASE 
        WHEN o.seller_dispatch_duration_hours <= 24 THEN '1. Rapid (< 24 hrs)'
        WHEN o.seller_dispatch_duration_hours <= 48 THEN '2. Fast (24 - 48 hrs)'
        WHEN o.seller_dispatch_duration_hours <= 96 THEN '3. Standard (48 - 96 hrs)'
        ELSE '4. Slow / Backlogged (> 96 hrs)'
    END AS seller_dispatch_speed_tier,
    COUNT(*) AS total_dispatched_orders,
    ROUND(AVG(o.seller_dispatch_duration_hours)::NUMERIC, 1) AS avg_dispatch_hours,
    ROUND(AVG(o.actual_delivery_duration_days)::NUMERIC, 1) AS avg_total_delivery_days,
    COUNT(CASE WHEN o.is_late_delivery THEN 1 END) AS customer_late_orders,
    ROUND(
        (COUNT(CASE WHEN o.is_late_delivery THEN 1 END)::NUMERIC / COUNT(*)) * 100.0, 
        2
    ) AS final_late_delivery_rate_pct
FROM core.fact_orders o
WHERE o.is_delivered = TRUE AND o.seller_dispatch_duration_hours IS NOT NULL
GROUP BY 
    CASE 
        WHEN o.seller_dispatch_duration_hours <= 24 THEN '1. Rapid (< 24 hrs)'
        WHEN o.seller_dispatch_duration_hours <= 48 THEN '2. Fast (24 - 48 hrs)'
        WHEN o.seller_dispatch_duration_hours <= 96 THEN '3. Standard (48 - 96 hrs)'
        ELSE '4. Slow / Backlogged (> 96 hrs)'
    END
ORDER BY seller_dispatch_speed_tier;


-- ==============================================================================
-- 10. GEOGRAPHIC REGIONAL DEMAND & FULFILLMENT DURATION (BRAZIL 5 MACRO-REGIONS)
-- Business Question: How does e-commerce adoption, GMV, and fulfillment speed vary
-- across Brazil's 5 official geographic macro-regions?
-- Demonstrates: CASE Statement Regional Mapping and Regional GMV Shares
-- ==============================================================================
WITH regional_orders AS (
    SELECT 
        o.order_id,
        o.order_total_item_value AS gmv,
        o.actual_delivery_duration_days,
        o.is_late_delivery,
        CASE 
            WHEN c.customer_state IN ('SP', 'RJ', 'MG', 'ES') THEN 'Southeast (Sudeste)'
            WHEN c.customer_state IN ('PR', 'SC', 'RS') THEN 'South (Sul)'
            WHEN c.customer_state IN ('BA', 'PE', 'CE', 'MA', 'PB', 'RN', 'AL', 'SE', 'PI') THEN 'Northeast (Nordeste)'
            WHEN c.customer_state IN ('DF', 'GO', 'MT', 'MS') THEN 'Central-West (Centro-Oeste)'
            WHEN c.customer_state IN ('AM', 'PA', 'RO', 'AC', 'TO', 'AP', 'RR') THEN 'North (Norte)'
            ELSE 'Unknown'
        END AS macro_region
    FROM core.fact_orders o
    JOIN core.dim_customer c ON o.customer_key = c.customer_key
    WHERE o.is_delivered = TRUE
)
SELECT 
    macro_region,
    COUNT(*) AS delivered_orders,
    ROUND((COUNT(*)::NUMERIC / SUM(COUNT(*)) OVER ()) * 100.0, 2) AS order_share_pct,
    ROUND(SUM(gmv), 2) AS total_gmv,
    ROUND((SUM(gmv) / SUM(SUM(gmv)) OVER ()) * 100.0, 2) AS gmv_share_pct,
    ROUND(AVG(actual_delivery_duration_days)::NUMERIC, 1) AS avg_delivery_days,
    ROUND(
        (COUNT(CASE WHEN is_late_delivery THEN 1 END)::NUMERIC / COUNT(*)) * 100.0, 
        2
    ) AS late_delivery_rate_pct
FROM regional_orders
GROUP BY macro_region
ORDER BY total_gmv DESC;


-- ==============================================================================
-- 11. ESTIMATED PLATFORM CONTRIBUTION-MARGIN SCENARIO ANALYSIS
-- Business Question: Modeling platform monetization: Assuming a 12% marketplace
-- take-rate, 2% credit card / 1% boleto payment processing fees, and an estimated
-- $15 customer compensation voucher per late delivery, what is our estimated net
-- platform contribution margin by product category?
-- Demonstrates: Financial Scenario Modeling, Net Contribution Calculations
-- ==============================================================================
WITH category_financials AS (
    SELECT 
        p.product_category_name_english AS category,
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(SUM(i.price), 2) AS gmv,
        -- Platform Revenue: 12% commission take-rate on item merchandise value
        ROUND(SUM(i.price) * 0.12, 2) AS estimated_platform_commission,
        -- Payment Processing Expense: 2% on credit card, 1% on boleto/debit
        ROUND(SUM(
            CASE 
                WHEN o.primary_payment_type = 'credit_card' THEN o.order_total_value * 0.02
                ELSE o.order_total_value * 0.01
            END
        ), 2) AS estimated_payment_processing_cost,
        -- Customer Goodwill Voucher Cost: $15.00 BRL per late delivered order
        ROUND(COUNT(CASE WHEN o.is_late_delivery THEN 1 END) * 15.00, 2) AS estimated_delay_remedy_cost
    FROM core.fact_order_items i
    JOIN core.fact_orders o ON i.order_id = o.order_id
    JOIN core.dim_product p ON i.product_key = p.product_key
    WHERE o.is_delivered = TRUE
    GROUP BY p.product_category_name_english
    HAVING COUNT(DISTINCT o.order_id) >= 200
)
SELECT 
    category,
    total_orders,
    gmv,
    estimated_platform_commission,
    estimated_payment_processing_cost,
    estimated_delay_remedy_cost,
    ROUND(
        (estimated_platform_commission - estimated_payment_processing_cost - estimated_delay_remedy_cost)::NUMERIC, 
        2
    ) AS estimated_net_contribution_margin,
    ROUND(
        ((estimated_platform_commission - estimated_payment_processing_cost - estimated_delay_remedy_cost) / NULLIF(gmv, 0)) * 100.0, 
        2
    ) AS net_take_rate_pct
FROM category_financials
ORDER BY estimated_net_contribution_margin DESC
LIMIT 20;


-- ==============================================================================
-- 12. HIGH-RISK SELLER MONITORING & OPERATIONAL EXPOSURE
-- Business Question: Which active merchants represent severe operational risk
-- (fulfilled > 50 orders with a late delivery rate > 15%), and what GMV is exposed?
-- Demonstrates: HAVING Clause Filtering, Exposure Aggregations
-- ==============================================================================
SELECT 
    s.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT o.order_id) AS orders_fulfilled,
    ROUND(SUM(i.price), 2) AS total_gmv_fulfilled,
    COUNT(CASE WHEN o.is_late_delivery THEN 1 END) AS late_orders_count,
    ROUND(
        (COUNT(CASE WHEN o.is_late_delivery THEN 1 END)::NUMERIC / COUNT(DISTINCT o.order_id)) * 100.0, 
        2
    ) AS seller_late_delivery_rate_pct,
    ROUND(SUM(CASE WHEN o.is_late_delivery THEN i.price ELSE 0 END), 2) AS gmv_exposed_to_delay
FROM core.fact_order_items i
JOIN core.fact_orders o ON i.order_id = o.order_id
JOIN core.dim_seller s ON i.seller_key = s.seller_key
WHERE o.is_delivered = TRUE
GROUP BY s.seller_id, s.seller_city, s.seller_state
HAVING COUNT(DISTINCT o.order_id) >= 50
   AND (COUNT(CASE WHEN o.is_late_delivery THEN 1 END)::NUMERIC / COUNT(DISTINCT o.order_id)) > 0.15
ORDER BY gmv_exposed_to_delay DESC
LIMIT 25;


-- ==============================================================================
-- 13. HEURISTIC DELIVERY RISK CLASSIFICATION & EXPOSURE (PRE-ML BASELINE)
-- Business Question: Before training a machine learning model, what is our rule-based
-- baseline? If all interstate orders with seller dispatch times > 72 hours are flagged
-- as "High Operational Risk", what volume and GMV does this heuristic flag?
-- Demonstrates: Rule-Based Operational Risk Scoring, Precision/Recall Baseline
-- ==============================================================================
WITH heuristic_flagged AS (
    SELECT 
        order_id,
        order_total_item_value AS gmv,
        is_interstate_delivery,
        seller_dispatch_duration_hours,
        is_late_delivery,
        CASE 
            WHEN is_interstate_delivery = TRUE AND seller_dispatch_duration_hours > 72.0 THEN 'High Operational Risk'
            WHEN seller_dispatch_duration_hours > 96.0 THEN 'Medium Operational Risk'
            ELSE 'Normal Operational Risk'
        END AS heuristic_risk_tier
    FROM core.fact_orders
    WHERE is_delivered = TRUE AND seller_dispatch_duration_hours IS NOT NULL
)
SELECT 
    heuristic_risk_tier,
    COUNT(*) AS total_orders,
    ROUND((COUNT(*)::NUMERIC / SUM(COUNT(*)) OVER ()) * 100.0, 2) AS order_share_pct,
    ROUND(SUM(gmv), 2) AS total_gmv,
    COUNT(CASE WHEN is_late_delivery THEN 1 END) AS actual_late_orders,
    ROUND(
        (COUNT(CASE WHEN is_late_delivery THEN 1 END)::NUMERIC / COUNT(*)) * 100.0, 
        2
    ) AS late_delivery_rate_pct
FROM heuristic_flagged
GROUP BY heuristic_risk_tier
ORDER BY late_delivery_rate_pct DESC;
