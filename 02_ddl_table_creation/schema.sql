-- Dimension tables

CREATE TABLE dim_customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    customer_unique_id VARCHAR(32) NOT NULL,
    customer_zip_code_prefix VARCHAR(5),
    customer_city VARCHAR(100),
    customer_state VARCHAR(2)
);

CREATE TABLE dim_sellers (
    seller_id VARCHAR(32) PRIMARY KEY,
    seller_zip_code_prefix VARCHAR(5),
    seller_city VARCHAR(100),
    seller_state VARCHAR(2)
);

CREATE TABLE dim_product_category_translation (
    product_category_name VARCHAR(100) PRIMARY KEY,
    product_category_name_english VARCHAR(100)
);

CREATE TABLE dim_products (
    product_id VARCHAR(32) PRIMARY KEY,
    product_category_name VARCHAR(100)
        REFERENCES dim_product_category_translation(product_category_name),
    product_name_lenght INT,
    product_description_lenght INT,
    product_photos_qty INT,
    product_weight_g INT,
    product_length_cm INT,
    product_height_cm INT,
    product_width_cm INT
);

CREATE TABLE dim_geolocation (
    geolocation_zip_code_prefix VARCHAR(5) PRIMARY KEY,
    geolocation_lat NUMERIC(10, 6),
    geolocation_lng NUMERIC(10, 6),
    geolocation_city VARCHAR(100),
    geolocation_state VARCHAR(2)
);

CREATE TABLE dim_orders (
    order_id VARCHAR(32) PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL REFERENCES dim_customers(customer_id),
    order_status VARCHAR(20),
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

CREATE TABLE dim_reviews (
    review_id VARCHAR(32) NOT NULL,
    order_id VARCHAR(32) NOT NULL REFERENCES dim_orders(order_id),
    review_score INT CHECK (review_score BETWEEN 1 AND 5),
    review_comment_title VARCHAR(255),
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    PRIMARY KEY (review_id, order_id)
);

CREATE TABLE dim_marketing_leads (
    mql_id VARCHAR(32) PRIMARY KEY,
    first_contact_date DATE,
    landing_page_id VARCHAR(32),
    origin VARCHAR(50)
);

CREATE TABLE dim_closed_deals (
    mql_id VARCHAR(32) PRIMARY KEY REFERENCES dim_marketing_leads(mql_id),
    seller_id VARCHAR(32) REFERENCES dim_sellers(seller_id),
    sdr_id VARCHAR(32),
    sr_id VARCHAR(32),
    won_date DATE,
    business_segment VARCHAR(100),
    lead_type VARCHAR(50),
    lead_behaviour_profile VARCHAR(50),
    has_company VARCHAR(10),
    has_gtin VARCHAR(10),
    average_stock VARCHAR(50),
    business_type VARCHAR(50),
    declared_product_catalog_size NUMERIC,
    declared_monthly_revenue NUMERIC
);

-- Fact tables

CREATE TABLE fact_order_items (
    order_id VARCHAR(32) NOT NULL REFERENCES dim_orders(order_id),
    order_item_id INT NOT NULL,
    product_id VARCHAR(32) NOT NULL REFERENCES dim_products(product_id),
    seller_id VARCHAR(32) NOT NULL REFERENCES dim_sellers(seller_id),
    shipping_limit_date TIMESTAMP,
    price NUMERIC(10, 2) CHECK (price >= 0),
    freight_value NUMERIC(10, 2) CHECK (freight_value >= 0),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE fact_order_payments (
    order_id VARCHAR(32) NOT NULL REFERENCES dim_orders(order_id),
    payment_sequential INT NOT NULL,
    payment_type VARCHAR(20),
    payment_installments INT,
    payment_value NUMERIC(10, 2) CHECK (payment_value >= 0),
    PRIMARY KEY (order_id, payment_sequential)
);