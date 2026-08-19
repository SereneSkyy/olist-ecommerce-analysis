WITH customer_first_order AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        o.order_purchase_timestamp,
        CASE
            WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 'late'
            ELSE 'on_time'
        END AS delivery_status,
        ROW_NUMBER() OVER (
            PARTITION BY c.customer_unique_id
            ORDER BY o.order_purchase_timestamp
        ) AS order_rank
    FROM dim_orders o
    JOIN dim_customers c ON o.customer_id = c.customer_id
    WHERE o.order_delivered_customer_date IS NOT NULL
),
customer_order_counts AS (
    SELECT customer_unique_id, COUNT(*) AS total_orders
    FROM dim_orders o
    JOIN dim_customers c ON o.customer_id = c.customer_id
    GROUP BY customer_unique_id
)
SELECT
    f.delivery_status AS first_order_status,
    COUNT(*) AS customers,
    ROUND(AVG(oc.total_orders), 3) AS avg_orders_per_customer,
    SUM(CASE WHEN oc.total_orders > 1 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(100.0 * SUM(CASE WHEN oc.total_orders > 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS repeat_pct
FROM customer_first_order f
JOIN customer_order_counts oc ON f.customer_unique_id = oc.customer_unique_id
WHERE f.order_rank = 1
GROUP BY f.delivery_status;