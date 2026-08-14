SELECT
    order_id,
    order_estimated_delivery_date,
    order_delivered_customer_date,
    CASE
        WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 'late'
        ELSE 'on_time'
    END AS delivery_status
FROM dim_orders
WHERE order_delivered_customer_date IS NOT NULL
LIMIT 10;