# Data Validation Report

## Check 1: Row count reconciliation
All tables loaded with row counts matching their source CSVs exactly, except
`dim_product_category_translation` (71 raw -> 73 loaded), which is expected:
two category names (`pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos`)
appear in `products.csv` but were missing from the translation file. They were
added manually with placeholder English translations before loading products,
to satisfy the foreign key constraint on `dim_products`.

## Check 2: Null thresholds

All hard-required columns (primary keys, `order_purchase_timestamp`, `price`,
`freight_value`, `payment_value`) are 100% populated across all tables.

Status-dependent date columns (`order_approved_at`, `order_delivered_carrier_date`,
`order_delivered_customer_date`) have nulls that are largely explained by
`order_status` — e.g. a `canceled` or `shipped` order legitimately has no
delivery date yet.

**Anomaly found:** 8 orders with `order_status = 'delivered'` have a null
`order_delivered_customer_date`. Logically, a delivered order should always
have a delivery date. This affects 0.008% of orders (8 / 99,441) and is
treated as a genuine data quality issue in the source data, not an artifact
of our pipeline.

**Decision:** these 8 orders are excluded from any delivery-time analysis
(e.g. computing days-to-deliver, or training the delivery-delay model),
since delivery time cannot be computed without a delivery date. They remain
in the warehouse for other analyses (e.g. revenue, review score) where the
missing date doesn't matter. Excluded, not imputed — imputing a date for
8 rows out of 99,441 isn't worth the risk of fabricating information.

## Check 3: Duplicates and uniqueness

All primary key columns (`customer_id`, `order_id`, `product_id`, `seller_id`)
confirmed unique with zero duplicates, as expected — Postgres constraint
enforcement verified independently.

`review_id` duplication check re-confirms the finding from Check 1's ingestion
debugging: 789 review_ids appear more than once, matching the documented
number exactly. This check now serves as a regression test — if a future
data reload shows a different count, it flags that the underlying data or
assumption has changed.

`customer_id` vs `customer_unique_id`: 99,441 total customer_id records
resolve to 96,096 distinct people (`customer_unique_id`), meaning 3,345
order records came from a returning customer. This confirms the expected
Olist data pattern (a new `customer_id` per order, a stable `customer_unique_id`
per person) and will be relevant for RFM segmentation later.

## Check 4: Referential integrity and value ranges

All foreign key relationships confirmed with zero orphaned records
(order_items -> products, order_items -> sellers, order_items -> orders,
reviews -> orders). This is expected since Postgres enforces these on
every insert, but independently verifying it protects against schema
drift or manual edits bypassing the ingestion pipeline in the future.

Value range checks: no negative prices, no review scores outside 1-5,
and no orders with a delivery date earlier than their purchase date.
All clean — the CHECK constraints written into the DDL are working as
intended, and there is no evidence of business-logic-level date corruption.

## Summary

The warehouse passed all four validation categories. Two real data quality
issues were found and resolved during ingestion (missing product categories,
non-unique review_id), and one data anomaly was found and documented without
being fixed (8 orders marked delivered with no delivery date — excluded from
delivery-time analysis rather than imputed). All findings are backed by
rerunnable checks in `validate.py`, not one-off manual queries.