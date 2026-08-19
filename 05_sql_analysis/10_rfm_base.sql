WITH customer_rfm AS (
    SELECT
        c.customer_unique_id,
        MAX(o.order_purchase_timestamp) AS last_order_date,
        COUNT(DISTINCT o.order_id) AS frequency,
        SUM(f.price) AS monetary
    FROM dim_orders o
    JOIN dim_customers c ON o.customer_id = c.customer_id
    JOIN fact_order_items f ON o.order_id = f.order_id
    GROUP BY c.customer_unique_id
)
SELECT
    customer_unique_id,
    last_order_date,
    (SELECT MAX(order_purchase_timestamp) FROM dim_orders) - last_order_date AS recency,
    frequency,
    ROUND(monetary, 2) AS monetary
FROM customer_rfm
ORDER BY monetary DESC
LIMIT 10;