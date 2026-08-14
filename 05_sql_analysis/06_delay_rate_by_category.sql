SELECT
    t.product_category_name_english,
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
JOIN dim_products p ON f.product_id = p.product_id
JOIN dim_product_category_translation t ON p.product_category_name = t.product_category_name
JOIN dim_orders o ON f.order_id = o.order_id
WHERE o.order_delivered_customer_date IS NOT NULL
GROUP BY t.product_category_name_english
HAVING COUNT(*) >= 100
ORDER BY late_pct DESC
LIMIT 10;