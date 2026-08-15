-- Bare tables only (no PK/FK/indexes yet) so the bulk COPY load in
-- docker/load/ isn't slowed down by constraint checks. Constraints are
-- added afterwards by docker/load/04_olist_constraints.sql.
\connect olist

CREATE TABLE product_category_name_translation (
    product_category_name         TEXT NOT NULL,
    product_category_name_english TEXT NOT NULL
);

CREATE TABLE customers (
    customer_id               TEXT NOT NULL,
    customer_unique_id        TEXT NOT NULL,
    customer_zip_code_prefix  TEXT,
    customer_city             TEXT,
    customer_state            TEXT
);

CREATE TABLE sellers (
    seller_id                TEXT NOT NULL,
    seller_zip_code_prefix   TEXT,
    seller_city              TEXT,
    seller_state             TEXT
);

CREATE TABLE geolocation (
    id                          BIGSERIAL,
    geolocation_zip_code_prefix TEXT NOT NULL,
    geolocation_lat             DOUBLE PRECISION,
    geolocation_lng             DOUBLE PRECISION,
    geolocation_city            TEXT,
    geolocation_state           TEXT
);

CREATE TABLE products (
    product_id                   TEXT NOT NULL,
    product_category_name        TEXT,
    product_name_length          INTEGER,
    product_description_length   INTEGER,
    product_photos_qty           INTEGER,
    product_weight_g             INTEGER,
    product_length_cm            INTEGER,
    product_height_cm            INTEGER,
    product_width_cm             INTEGER
);

CREATE TABLE orders (
    order_id                       TEXT NOT NULL,
    customer_id                    TEXT NOT NULL,
    order_status                   TEXT NOT NULL,
    order_purchase_timestamp       TIMESTAMP,
    order_approved_at              TIMESTAMP,
    order_delivered_carrier_date   TIMESTAMP,
    order_delivered_customer_date  TIMESTAMP,
    order_estimated_delivery_date  TIMESTAMP
);

CREATE TABLE order_items (
    order_id              TEXT NOT NULL,
    order_item_id         INTEGER NOT NULL,
    product_id            TEXT NOT NULL,
    seller_id             TEXT NOT NULL,
    shipping_limit_date   TIMESTAMP,
    price                 NUMERIC(10,2),
    freight_value         NUMERIC(10,2)
);

CREATE TABLE order_payments (
    order_id               TEXT NOT NULL,
    payment_sequential     INTEGER NOT NULL,
    payment_type           TEXT,
    payment_installments   INTEGER,
    payment_value          NUMERIC(10,2)
);

CREATE TABLE order_reviews (
    id                        BIGSERIAL,
    review_id                 TEXT NOT NULL,
    order_id                  TEXT NOT NULL,
    review_score              INTEGER,
    review_comment_title      TEXT,
    review_comment_message    TEXT,
    review_creation_date      TIMESTAMP,
    review_answer_timestamp   TIMESTAMP
);
