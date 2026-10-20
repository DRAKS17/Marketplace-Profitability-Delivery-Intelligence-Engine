-- ==============================================================================
-- 03_create_dimensions_facts.sql
-- Database: marketplace_analytics
-- Schema: core
-- Purpose: Implement Kimball Dimensional Model (Star Schema) with Constraints
-- ==============================================================================

-- ==============================================================================
-- 1. DIMENSION TABLES
-- ==============================================================================

-- DIM_CUSTOMER
DROP TABLE IF EXISTS core.dim_customer CASCADE;
CREATE TABLE core.dim_customer (
    customer_key SERIAL PRIMARY KEY,
    customer_id VARCHAR(32) UNIQUE NOT NULL,
    customer_unique_id VARCHAR(32) NOT NULL,
    customer_zip_code_prefix INTEGER NOT NULL,
    customer_city VARCHAR(64) NOT NULL,
    customer_state CHAR(2) NOT NULL
);
CREATE INDEX idx_dim_cust_unique ON core.dim_customer(customer_unique_id);
CREATE INDEX idx_dim_cust_state ON core.dim_customer(customer_state);

-- DIM_SELLER
DROP TABLE IF EXISTS core.dim_seller CASCADE;
CREATE TABLE core.dim_seller (
    seller_key SERIAL PRIMARY KEY,
    seller_id VARCHAR(32) UNIQUE NOT NULL,
    seller_zip_code_prefix INTEGER NOT NULL,
    seller_city VARCHAR(64) NOT NULL,
    seller_state CHAR(2) NOT NULL
);
CREATE INDEX idx_dim_seller_state ON core.dim_seller(seller_state);

-- DIM_PRODUCT
DROP TABLE IF EXISTS core.dim_product CASCADE;
CREATE TABLE core.dim_product (
    product_key SERIAL PRIMARY KEY,
    product_id VARCHAR(32) UNIQUE NOT NULL,
    product_category_name VARCHAR(64) NOT NULL,
    product_category_name_english VARCHAR(64) NOT NULL,
    product_name_lenght INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty INTEGER,
    product_weight_g NUMERIC(10, 2),
    product_length_cm NUMERIC(10, 2),
    product_height_cm NUMERIC(10, 2),
    product_width_cm NUMERIC(10, 2),
    product_volume_cm3 NUMERIC(12, 2)
);
CREATE INDEX idx_dim_prod_cat_en ON core.dim_product(product_category_name_english);

-- DIM_LOCATION (Postal Centroids)
DROP TABLE IF EXISTS core.dim_location CASCADE;
CREATE TABLE core.dim_location (
    location_key SERIAL PRIMARY KEY,
    zip_code_prefix INTEGER UNIQUE NOT NULL,
    latitude NUMERIC(9, 6) NOT NULL,
    longitude NUMERIC(9, 6) NOT NULL,
    city VARCHAR(64) NOT NULL,
    state CHAR(2) NOT NULL
);

-- DIM_DATE (Calendar Dimension 2016-2020)
DROP TABLE IF EXISTS core.dim_date CASCADE;
CREATE TABLE core.dim_date (
    date_key INTEGER PRIMARY KEY, -- Format: YYYYMMDD
    full_date DATE UNIQUE NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(16) NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL, -- 0=Monday, 6=Sunday
    day_name VARCHAR(16) NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

-- ==============================================================================
-- 2. FACT TABLES
-- ==============================================================================

-- FACT_ORDERS (Grain: 1 row per order)
DROP TABLE IF EXISTS core.fact_orders CASCADE;
CREATE TABLE core.fact_orders (
    order_key SERIAL PRIMARY KEY,
    order_id VARCHAR(32) UNIQUE NOT NULL,
    customer_key INTEGER NOT NULL REFERENCES core.dim_customer(customer_key),
    purchase_date_key INTEGER NOT NULL REFERENCES core.dim_date(date_key),
    order_status VARCHAR(16) NOT NULL,
    
    -- Timestamps
    order_purchase_timestamp TIMESTAMPTZ NOT NULL,
    order_approved_at TIMESTAMPTZ,
    order_delivered_carrier_date TIMESTAMPTZ,
    order_delivered_customer_date TIMESTAMPTZ,
    order_estimated_delivery_date TIMESTAMPTZ NOT NULL,
    
    -- Financial Aggregations at Order Grain (Guaranteed Zero Fanout)
    order_item_count INTEGER NOT NULL DEFAULT 0,
    order_total_item_value NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    order_total_freight_value NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    order_total_value NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    freight_ratio NUMERIC(6, 4) NOT NULL DEFAULT 0.0000,
    
    -- Payment Metrics
    primary_payment_type VARCHAR(16),
    max_payment_installments INTEGER,
    payment_split_count INTEGER DEFAULT 0,
    
    -- Operational Logistics Metrics
    haversine_distance_km NUMERIC(10, 2),
    is_interstate_delivery BOOLEAN DEFAULT FALSE,
    estimated_delivery_duration_days NUMERIC(8, 2),
    seller_dispatch_duration_hours NUMERIC(8, 2),
    carrier_transit_duration_days NUMERIC(8, 2),
    actual_delivery_duration_days NUMERIC(8, 2),
    delivery_delay_days NUMERIC(8, 2),
    is_late_delivery BOOLEAN,
    is_delivered BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_fact_orders_cust ON core.fact_orders(customer_key);
CREATE INDEX idx_fact_orders_date ON core.fact_orders(purchase_date_key);
CREATE INDEX idx_fact_orders_status ON core.fact_orders(order_status);
CREATE INDEX idx_fact_orders_late ON core.fact_orders(is_late_delivery);

-- FACT_ORDER_ITEMS (Grain: 1 row per physical item sold)
DROP TABLE IF EXISTS core.fact_order_items CASCADE;
CREATE TABLE core.fact_order_items (
    order_item_key SERIAL PRIMARY KEY,
    order_id VARCHAR(32) NOT NULL,
    order_item_id INTEGER NOT NULL,
    customer_key INTEGER NOT NULL REFERENCES core.dim_customer(customer_key),
    seller_key INTEGER NOT NULL REFERENCES core.dim_seller(seller_key),
    product_key INTEGER NOT NULL REFERENCES core.dim_product(product_key),
    purchase_date_key INTEGER NOT NULL REFERENCES core.dim_date(date_key),
    
    shipping_limit_date TIMESTAMPTZ NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    freight_value NUMERIC(10, 2) NOT NULL,
    item_total_value NUMERIC(10, 2) NOT NULL,
    is_free_shipping BOOLEAN DEFAULT FALSE,
    
    UNIQUE(order_id, order_item_id)
);
CREATE INDEX idx_fact_items_seller ON core.fact_order_items(seller_key);
CREATE INDEX idx_fact_items_prod ON core.fact_order_items(product_key);
CREATE INDEX idx_fact_items_order ON core.fact_order_items(order_id);

-- FACT_PAYMENTS (Grain: 1 row per payment transaction attempt)
DROP TABLE IF EXISTS core.fact_payments CASCADE;
CREATE TABLE core.fact_payments (
    payment_key SERIAL PRIMARY KEY,
    order_id VARCHAR(32) NOT NULL,
    payment_sequential INTEGER NOT NULL,
    payment_type VARCHAR(16) NOT NULL,
    payment_installments INTEGER NOT NULL,
    payment_value NUMERIC(10, 2) NOT NULL,
    is_voided_payment BOOLEAN DEFAULT FALSE,
    UNIQUE(order_id, payment_sequential)
);
CREATE INDEX idx_fact_pay_order ON core.fact_payments(order_id);

-- FACT_REVIEWS (Grain: 1 row per customer survey response)
DROP TABLE IF EXISTS core.fact_reviews CASCADE;
CREATE TABLE core.fact_reviews (
    review_key SERIAL PRIMARY KEY,
    review_id VARCHAR(32) NOT NULL,
    order_id VARCHAR(32) NOT NULL,
    review_score INTEGER NOT NULL CHECK (review_score BETWEEN 1 AND 5),
    review_creation_date DATE NOT NULL,
    review_answer_timestamp TIMESTAMPTZ NOT NULL,
    has_comment_message BOOLEAN DEFAULT FALSE,
    review_char_length INTEGER DEFAULT 0,
    review_word_count INTEGER DEFAULT 0,
    is_delivery_issue BOOLEAN DEFAULT FALSE,
    is_product_quality_issue BOOLEAN DEFAULT FALSE,
    is_positive_experience BOOLEAN DEFAULT FALSE,
    csat_category VARCHAR(16) NOT NULL,
    operational_feedback_tag VARCHAR(32) NOT NULL,
    UNIQUE(review_id, order_id)
);
CREATE INDEX idx_fact_rev_order ON core.fact_reviews(order_id);
CREATE INDEX idx_fact_rev_score ON core.fact_reviews(review_score);
CREATE INDEX idx_fact_rev_csat ON core.fact_reviews(csat_category);
