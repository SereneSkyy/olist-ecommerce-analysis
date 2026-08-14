SELECT
    t.product_category_name_english,
    SUM(f.price) AS total_revenue,
    COUNT(*) AS items_sold
FROM fact_order_items f
JOIN dim_products p ON f.product_id = p.product_id
JOIN dim_product_category_translation t ON p.product_category_name = t.product_category_name
GROUP BY t.product_category_name_english
ORDER BY total_revenue DESC
LIMIT 10;