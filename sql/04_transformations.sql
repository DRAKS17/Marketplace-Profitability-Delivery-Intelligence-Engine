-- ==============================================================================
-- 04_transformations.sql
-- Database: marketplace_analytics
-- Purpose: ELT Pipeline - Transform and populate core dimensional model from staging
-- ==============================================================================

-- 1. POPULATE CALENDAR DIMENSION (dim_date)
INSERT INTO core.dim_date (
    date_key,
    full_date,
    year,
    quarter,
    month,
    month_name,
    day,
    day_of_week,
    day_name,
    is_weekend
)
SELECT 
    TO_CHAR(d::date, 'YYYYMMDD')::INTEGER AS date_key,
    d::date AS full_date,
    EXTRACT(YEAR FROM d)::INTEGER AS year,
    EXTRACT(QUARTER FROM d)::INTEGER AS quarter,
    EXTRACT(MONTH FROM d)::INTEGER AS month,
    TO_CHAR(d, 'FMMonth') AS month_name,
    EXTRACT(DAY FROM d)::INTEGER AS day,
    EXTRACT(DOW FROM d)::INTEGER AS day_of_week,
    TO_CHAR(d, 'FMDay') AS day_name,
    CASE WHEN EXTRACT(DOW FROM d) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend
FROM generate_series('2016-01-01'::date, '2020-12-31'::date, '1 day'::interval) AS d
ON CONFLICT (date_key) DO NOTHING;

-- 2. POPULATE DIM_CUSTOMER
INSERT INTO core.dim_customer (
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
)
SELECT 
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
FROM stg.customers
ON CONFLICT (customer_id) DO NOTHING;

-- 3. POPULATE DIM_SELLER
INSERT INTO core.dim_seller (
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state
)
SELECT 
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state
FROM stg.sellers
ON CONFLICT (seller_id) DO NOTHING;

-- 4. POPULATE DIM_PRODUCT
INSERT INTO core.dim_product (
    product_id,
    product_category_name,
    product_category_name_english,
    product_name_lenght,
    product_description_lenght,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm,
    product_volume_cm3
)
SELECT 
    product_id,
    product_category_name,
    product_category_name_english,
    product_name_lenght,
    product_description_lenght,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm,
    ROUND((product_length_cm * product_height_cm * product_width_cm)::NUMERIC, 2) AS product_volume_cm3
FROM stg.products
ON CONFLICT (product_id) DO NOTHING;

-- 5. POPULATE DIM_LOCATION
INSERT INTO core.dim_location (
    zip_code_prefix,
    latitude,
    longitude,
    city,
    state
)
SELECT 
    geolocation_zip_code_prefix AS zip_code_prefix,
    geolocation_lat AS latitude,
    geolocation_lng AS longitude,
    geolocation_city AS city,
    geolocation_state AS state
FROM stg.geolocation
ON CONFLICT (zip_code_prefix) DO NOTHING;

-- 6. POPULATE FACT_ORDER_ITEMS
INSERT INTO core.fact_order_items (
    order_id,
    order_item_id,
    customer_key,
    seller_key,
    product_key,
    purchase_date_key,
    shipping_limit_date,
    price,
    freight_value,
    item_total_value,
    is_free_shipping
)
SELECT 
    i.order_id,
    i.order_item_id,
    c.customer_key,
    s.seller_key,
    p.product_key,
    TO_CHAR(o.order_purchase_timestamp::date, 'YYYYMMDD')::INTEGER AS purchase_date_key,
    i.shipping_limit_date,
    i.price,
    i.freight_value,
    ROUND((i.price + i.freight_value)::NUMERIC, 2) AS item_total_value,
    i.is_free_shipping
FROM stg.order_items i
JOIN stg.orders o ON i.order_id = o.order_id
JOIN core.dim_customer c ON o.customer_id = c.customer_id
JOIN core.dim_seller s ON i.seller_id = s.seller_id
JOIN core.dim_product p ON i.product_id = p.product_id
ON CONFLICT (order_id, order_item_id) DO NOTHING;

-- 7. POPULATE FACT_PAYMENTS
INSERT INTO core.fact_payments (
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value,
    is_voided_payment
)
SELECT 
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value,
    is_voided_payment
FROM stg.order_payments
ON CONFLICT (order_id, payment_sequential) DO NOTHING;

-- 8. POPULATE FACT_REVIEWS
INSERT INTO core.fact_reviews (
    review_id,
    order_id,
    review_score,
    review_creation_date,
    review_answer_timestamp,
    has_comment_message,
    review_char_length,
    review_word_count,
    is_delivery_issue,
    is_product_quality_issue,
    is_positive_experience,
    csat_category,
    operational_feedback_tag
)
SELECT 
    review_id,
    order_id,
    review_score,
    review_creation_date,
    review_answer_timestamp,
    has_comment_message,
    review_char_length,
    review_word_count,
    is_delivery_issue,
    is_product_quality_issue,
    is_positive_experience,
    csat_category,
    operational_feedback_tag
FROM stg.order_reviews
ON CONFLICT (review_id, order_id) DO NOTHING;
