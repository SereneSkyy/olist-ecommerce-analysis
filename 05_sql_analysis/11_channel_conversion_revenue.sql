SELECT
    l.origin,
    COUNT(DISTINCT l.mql_id) AS total_leads,
    COUNT(DISTINCT d.mql_id) AS closed_deals,
    ROUND(100.0 * COUNT(DISTINCT d.mql_id) / COUNT(DISTINCT l.mql_id), 2) AS conversion_pct,
    COUNT(DISTINCT f.order_id) AS orders_generated,
    ROUND(COALESCE(SUM(f.price), 0), 2) AS total_revenue
FROM dim_marketing_leads l
LEFT JOIN dim_closed_deals d ON l.mql_id = d.mql_id
LEFT JOIN dim_sellers s ON d.seller_id = s.seller_id
LEFT JOIN fact_order_items f ON s.seller_id = f.seller_id
GROUP BY l.origin
ORDER BY total_revenue DESC;