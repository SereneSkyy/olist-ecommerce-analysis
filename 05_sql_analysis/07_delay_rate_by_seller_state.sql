SELECT
    s.seller_state,
    COUNT(*) AS total_delivered_items,
    SUM(
        CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
        THEN 1 ELSE 0 END
    ) AS late_items,
    ROUND(
        100.0 * SUM(
            CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
            THEN 1 ELSE 0 END
        ) / COUNT(*), 2
    ) AS late_pct
FROM fact_order_items f
JOIN dim_sellers s ON f.seller_id = s.seller_id
JOIN dim_orders o ON f.order_id = o.order_id
WHERE o.order_delivered_customer_date IS NOT NULL
GROUP BY s.seller_state
HAVING COUNT(*) >= 100
ORDER BY late_pct DESC
LIMIT 10;