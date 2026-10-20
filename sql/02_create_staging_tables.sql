-- ==============================================================================
-- 02_create_staging_tables.sql
-- Database: marketplace_analytics
-- Schema: stg
-- Purpose: Define source-shaped staging tables with strict types and primary keys
-- ==============================================================================

-- 1. STAGING CUSTOMERS
DROP TABLE IF EXISTS stg.customers CASCADE;
CREATE TABLE stg.customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    customer_unique_id VARCHAR(32) NOT NULL,
    customer_zip_code_prefix INTEGER NOT NULL,
    customer_city VARCHAR(64) NOT NULL,
    customer_state CHAR(2) NOT NULL
);

-- 2. STAGING SELLERS
DROP TABLE IF EXISTS stg.sellers CASCADE;
CREATE TABLE stg.sellers (
    seller_id VARCHAR(32) PRIMARY KEY,
    seller_zip_code_prefix INTEGER NOT NULL,
    seller_city VARCHAR(64) NOT NULL,
    seller_state CHAR(2) NOT NULL
);

-- 3. STAGING PRODUCTS
DROP TABLE IF EXISTS stg.products CASCADE;
CREATE TABLE stg.products (
    product_id VARCHAR(32) PRIMARY KEY,
    product_category_name VARCHAR(64) NOT NULL,
    product_category_name_english VARCHAR(64) NOT NULL,
    product_name_lenght INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty INTEGER,
    product_weight_g NUMERIC(10, 2),
    product_length_cm NUMERIC(10, 2),
    product_height_cm NUMERIC(10, 2),
    product_width_cm NUMERIC(10, 2)
);

-- 4. STAGING GEOLOCATION (Unique Centroids)
DROP TABLE IF EXISTS stg.geolocation CASCADE;
CREATE TABLE stg.geolocation (
    geolocation_zip_code_prefix INTEGER PRIMARY KEY,
    geolocation_lat NUMERIC(9, 6) NOT NULL,
    geolocation_lng NUMERIC(9, 6) NOT NULL,
    geolocation_city VARCHAR(64) NOT NULL,
    geolocation_state CHAR(2) NOT NULL
);

-- 5. STAGING ORDERS
DROP TABLE IF EXISTS stg.orders CASCADE;
CREATE TABLE stg.orders (
    order_id VARCHAR(32) PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL,
    order_status VARCHAR(16) NOT NULL,
    order_purchase_timestamp TIMESTAMPTZ NOT NULL,
    order_approved_at TIMESTAMPTZ,
    order_delivered_carrier_date TIMESTAMPTZ,
    order_delivered_customer_date TIMESTAMPTZ,
    order_estimated_delivery_date TIMESTAMPTZ NOT NULL,
    is_chronologically_valid BOOLEAN DEFAULT TRUE
);

-- 6. STAGING ORDER ITEMS
DROP TABLE IF EXISTS stg.order_items CASCADE;
CREATE TABLE stg.order_items (
    order_id VARCHAR(32) NOT NULL,
    order_item_id INTEGER NOT NULL,
    product_id VARCHAR(32) NOT NULL,
    seller_id VARCHAR(32) NOT NULL,
    shipping_limit_date TIMESTAMPTZ NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    freight_value NUMERIC(10, 2) NOT NULL,
    is_free_shipping BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (order_id, order_item_id)
);

-- 7. STAGING ORDER PAYMENTS
DROP TABLE IF EXISTS stg.order_payments CASCADE;
CREATE TABLE stg.order_payments (
    order_id VARCHAR(32) NOT NULL,
    payment_sequential INTEGER NOT NULL,
    payment_type VARCHAR(16) NOT NULL,
    payment_installments INTEGER NOT NULL,
    payment_value NUMERIC(10, 2) NOT NULL,
    is_voided_payment BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (order_id, payment_sequential)
);

-- 8. STAGING ORDER REVIEWS
DROP TABLE IF EXISTS stg.order_reviews CASCADE;
CREATE TABLE stg.order_reviews (
    review_id VARCHAR(32) NOT NULL,
    order_id VARCHAR(32) NOT NULL,
    review_score INTEGER NOT NULL CHECK (review_score BETWEEN 1 AND 5),
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date DATE NOT NULL,
    review_answer_timestamp TIMESTAMPTZ NOT NULL,
    has_comment_title BOOLEAN DEFAULT FALSE,
    has_comment_message BOOLEAN DEFAULT FALSE,
    review_char_length INTEGER DEFAULT 0,
    review_word_count INTEGER DEFAULT 0,
    normalized_text TEXT,
    is_delivery_issue BOOLEAN DEFAULT FALSE,
    is_product_quality_issue BOOLEAN DEFAULT FALSE,
    is_positive_experience BOOLEAN DEFAULT FALSE,
    csat_category VARCHAR(16) NOT NULL,
    operational_feedback_tag VARCHAR(32) NOT NULL,
    PRIMARY KEY (review_id, order_id)
);

-- Create Staging Indexes for high-performance extraction
CREATE INDEX IF NOT EXISTS idx_stg_orders_cust ON stg.orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_stg_items_prod ON stg.order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_stg_items_seller ON stg.order_items(seller_id);
CREATE INDEX IF NOT EXISTS idx_stg_pay_order ON stg.order_payments(order_id);
CREATE INDEX IF NOT EXISTS idx_stg_rev_order ON stg.order_reviews(order_id);
