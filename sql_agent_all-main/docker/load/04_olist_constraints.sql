\connect olist

ALTER TABLE product_category_name_translation ADD PRIMARY KEY (product_category_name);

ALTER TABLE customers ADD PRIMARY KEY (customer_id);
CREATE INDEX customers_zip_idx ON customers (customer_zip_code_prefix);

ALTER TABLE sellers ADD PRIMARY KEY (seller_id);
CREATE INDEX sellers_zip_idx ON sellers (seller_zip_code_prefix);

CREATE INDEX geolocation_zip_idx ON geolocation (geolocation_zip_code_prefix);

-- product_category_name is intentionally not FK'd to the translation table:
-- a few categories in the source data have no translation row.
ALTER TABLE products ADD PRIMARY KEY (product_id);
CREATE INDEX products_category_idx ON products (product_category_name);

ALTER TABLE orders
    ADD PRIMARY KEY (order_id),
    ADD FOREIGN KEY (customer_id) REFERENCES customers (customer_id);
CREATE INDEX orders_customer_id_idx ON orders (customer_id);

ALTER TABLE order_items
    ADD PRIMARY KEY (order_id, order_item_id),
    ADD FOREIGN KEY (order_id) REFERENCES orders (order_id),
    ADD FOREIGN KEY (product_id) REFERENCES products (product_id),
    ADD FOREIGN KEY (seller_id) REFERENCES sellers (seller_id);
CREATE INDEX order_items_product_id_idx ON order_items (product_id);
CREATE INDEX order_items_seller_id_idx ON order_items (seller_id);

ALTER TABLE order_payments
    ADD PRIMARY KEY (order_id, payment_sequential),
    ADD FOREIGN KEY (order_id) REFERENCES orders (order_id);

-- review_id is not globally unique in the source data, so it can't be the
-- (sole) primary key; a surrogate id is used instead.
ALTER TABLE order_reviews
    ADD PRIMARY KEY (id),
    ADD FOREIGN KEY (order_id) REFERENCES orders (order_id);
CREATE INDEX order_reviews_order_id_idx ON order_reviews (order_id);
CREATE INDEX order_reviews_review_id_idx ON order_reviews (review_id);
