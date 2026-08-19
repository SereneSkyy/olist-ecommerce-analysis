# Olist Funnel-to-Fulfillment: End-to-End E-Commerce Analytics

End-to-end analytics project on the Brazilian e-commerce marketplace Olist, covering the full funnel from seller acquisition through order fulfillment, delivery risk, and customer retention. Built on Postgres with a validated data pipeline, SQL-driven analysis, an iteratively-improved delivery-delay classifier, and two live dashboards (Streamlit and Power BI).

## Business Questions

1. Which marketing channels drive the highest-converting, highest-revenue sellers onto the platform? *(Revised from an initial assumption that this data tracked shopper acquisition — see [Marketing Funnel Integration](#marketing-funnel-integration) below.)*
2. What are the key drivers of delivery delays, and can they be predicted before dispatch?
3. How do delivery delays affect customer review scores and repeat purchase behavior?
4. Which product categories and seller regions contribute most to revenue and to delay risk?
5. How can customers be segmented (recency, frequency, monetary) to prioritize retention efforts?

## Dataset

- **Core dataset:** [Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) : 8 relational CSVs covering orders, customers, products, sellers, payments, reviews, and geolocation (2016–2018).
- **Marketing funnel dataset:** [Olist Marketing Funnel](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist) : Olist's own B2B sales funnel data for onboarding sellers onto the platform.

Full source details, licenses, and known cross-dataset issues are documented in `01_data_sources/data_sources.md`.

## Tech Stack

| Layer | Tool | Reason |
|---|---|---|
| Database | PostgreSQL | Production-realistic: indexing, constraints, referential integrity — not available in SQLite |
| Ingestion | Python (pandas, SQLAlchemy) | Idempotent, scripted, repeatable load rather than manual CSV import |
| Validation | Python (pandas, SQLAlchemy) | Row count reconciliation, null thresholds, duplicate detection, referential integrity checks |
| Analysis | SQL (joins, CTEs, window functions) | Direct, auditable business-question answers against the warehouse |
| Modeling | scikit-learn | RFM segmentation, delivery-delay classification |
| Dashboards | Streamlit + Power BI | Two independent, browser-accessible presentations of the same validated data |

## Project Structure

```
olist-ecommerce-analysis/
├── data/raw/                     # source CSVs (not committed — see below)
├── 01_data_sources/               # dataset provenance, licenses, known issues
├── 02_ddl_table_creation/        # star schema DDL
├── 03_ingestion/                 # idempotent load script
├── 04_data_validation/           # validation script + written report
├── 05_sql_analysis/              # business-question SQL, one file per question
├── 06_modeling/                  # RFM + delivery-delay model notebook and outputs
├── 07_dashboard/                 # Streamlit app
├── requirements.txt
└── README.md
```

Raw CSVs and the Python virtual environment are excluded from version control (`.gitignore`); only code and documentation are committed.

## Data Model

Star schema, grain-driven design:

- **`fact_order_items`** : one row per product line item per order (composite key: `order_id` + `order_item_id`). Measures: `price`, `freight_value`.
- **`fact_order_payments`** : one row per payment transaction per order (composite key: `order_id` + `payment_sequential`), since payments can be split across multiple methods.
- **Dimensions:** `dim_customers`, `dim_orders`, `dim_products`, `dim_sellers`, `dim_reviews`, `dim_geolocation`, `dim_product_category_translation`, `dim_marketing_leads`, `dim_closed_deals`.

Two design decisions worth calling out:

- **`dim_reviews` uses a composite primary key** (`review_id` + `order_id`), not `review_id` alone. Initial ingestion failed on a uniqueness violation — investigation showed 789 `review_id`s are legitimately linked to two different orders (same score, same date), rather than being duplicate rows. Deduplicating would have silently dropped real order-review links, so the primary key was changed instead.
- **`dim_geolocation` is aggregated**, not loaded raw. The raw file has multiple lat/lng pairs per zip code prefix (1,000,163 raw rows). These are averaged down to one row per prefix (19,015 rows) before loading, since the schema's grain assumes one location per prefix.

## Data Validation

A dedicated validation script (`04_data_validation/validate.py`) runs four categories of checks against the loaded warehouse and produces a written report:

1. **Row count reconciliation** : loaded table counts vs. source CSV counts
2. **Null thresholds** : hard-required columns (0% tolerance) vs. status-dependent columns (nulls expected, verified against business logic)
3. **Duplicates/uniqueness** : including a regression test for the `review_id` finding above
4. **Referential integrity and value ranges** : independent verification of what Postgres's constraints already enforce, plus logic Postgres can't enforce on its own (e.g. no order delivered before it was purchased)

Full findings, including every issue found and how it was resolved, are in `04_data_validation/validation_report.md`. Highlights:

- Two product categories (`pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos`) existed in the products data but were missing from the official translation file — added manually with documented translations.
- 8 orders marked `delivered` have a null delivery date — excluded from delivery-time analysis (not imputed), since fabricating a date for 8 rows isn't worth the risk.
- The marketing funnel dataset's `dim_closed_deals.seller_id` has no match in `dim_sellers` for 462 of 842 rows (55%) — the foreign key was relaxed rather than dropping the majority of the table, since this mismatch is itself a finding (see below).

## SQL Analysis

Seven analytical queries in `05_sql_analysis/`, using joins, `GROUP BY`/`HAVING`, `CASE WHEN` conditional aggregation, CTEs, and window functions (`ROW_NUMBER() OVER (PARTITION BY ...)`). See `05_sql_analysis/README.md` for the full index of files and findings.

## Marketing Funnel Integration

The marketing funnel dataset was initially assumed to track shopper acquisition. Inspecting the actual columns (`business_segment`, `has_company`, `declared_monthly_revenue`, `sdr_id`, `sr_id`) revealed it instead tracks **Olist's internal B2B sales funnel for onboarding sellers** — a completely different business process than shopper acquisition. Business Question #1 was revised accordingly, and `dim_closed_deals.seller_id` was used to connect seller acquisition channel through to actual marketplace revenue via `fact_order_items`.

## Modeling

### RFM Segmentation

Customers were segmented on recency and monetary value (median split into four segments), rather than a standard 5×5 RFM grid — frequency is heavily concentrated at exactly 1 purchase for at least 75% of customers, so it doesn't meaningfully separate segments in this dataset. This is a deliberate adaptation, not an oversight.

- **Champions** (recent, high spend) and **At Risk** (high spend, not recent) have nearly identical average spend (~$237 vs ~$238) — the only real difference is recency. At Risk represents **$5.6M in historical revenue** from customers who haven't ordered in over a year, making it the clearest, most actionable retention target in the analysis.

### Delivery-Delay Classifier

Built and evaluated iteratively, with each step's reasoning documented rather than silently tuned away:

| Version | Features | ROC-AUC | Recall (late) | Precision (late) |
|---|---|---|---|---|
| v1 — naive | price, freight, category, seller state, day of week | 0.669 | 0.15 | 0.50 |
| v1 — class-weighted | same, with `class_weight="balanced"` | 0.673 | 0.22 | 0.27 |
| v2 — engineered features | + estimated delivery window, seller–customer distance (haversine), customer state | **0.769** | 0.24 | 0.52 |

The naive model achieves 92% accuracy purely by defaulting to "on time," since 92% of orders are on-time regardless of prediction — a class-imbalance problem, confirmed by an ROC-AUC of only 0.669. Class weighting alone barely moved ROC-AUC (0.673), showing the real limitation was the *features*, not the imbalance handling. Adding delivery-window tightness and physical shipping distance (computed via the haversine formula against aggregated geolocation data) produced a substantial, real improvement to 0.769 ROC-AUC and nearly doubled precision on the late class.

**Honest limitation:** even the improved model misses roughly 3 in 4 late orders (recall 0.24). Meaningfully better performance would likely require true logistics data — carrier performance, warehouse processing time, weather — not present in the public Olist dataset.

## Dashboards

- **Streamlit** (`07_dashboard/app.py`) : 7-page app querying the Postgres warehouse live: overview KPIs, revenue/delay by category, delay by seller region, delay's effect on reviews, RFM segments, marketing channel performance, and the delivery-delay model comparison. Run with `streamlit run 07_dashboard/app.py`.
- **Power BI** : connects directly to the same Postgres warehouse (`Import` mode), recreates the same star-schema relationships, and blends in the RFM CSV output alongside the live database connection. Published via Power BI's "Publish to Web" for browser access without requiring Power BI Desktop. [Link to published report]

## Key Findings

- **Revenue and delay risk don't move together.** `health_beauty` is the top revenue category ($1.26M), but its delay rate (9.06%) is only moderate. The worst delay rate belongs to `audio` (12.71%), a much smaller revenue contributor.
- **Seller region has a far larger effect on delay risk than product category.** Sellers in Maranhão (MA) have a 23.63% late-delivery rate — nearly 3x the next-worst state (São Paulo, 8.52%).
- **Late deliveries have a large, measurable effect on customer satisfaction.** Late orders average 2.57 review stars vs. 4.29 for on-time — a 1.7-point gap on a 5-point scale, the strongest relationship found in the analysis. Orders with no recorded delivery date at all score even lower (1.76), suggesting these are experienced as failed deliveries rather than simply delayed ones.
- **The effect on repeat purchases is real but modest.** A late first order correlates with a 2.72% repeat-purchase rate vs. 3.23% for on-time — directionally consistent with the review-score finding, but a much smaller effect in absolute terms.
- **High spend and loyalty don't necessarily go together.** Several of the highest lifetime-value customers made only a single purchase, motivating the recency/monetary-based segmentation over a frequency-heavy model.
- **Marketing channel conversion varies more than lead volume.** `organic_search` brings the most leads and strong revenue, but `social` underperforms significantly on conversion (5.56%) despite high lead volume — and a majority of closed deals across all channels show no matching seller activity in the operational data at all.

## How to Run

```bash
# 1. Clone and install dependencies
git clone <repo-url>
cd olist-ecommerce-analysis
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt

# 2. Set up Postgres
createdb olist_analytics
psql -U postgres -d olist_analytics -f 02_ddl_table_creation/schema.sql

# 3. Configure .env with your DB credentials (see .env.example)

# 4. Download data (requires Kaggle API credentials)
kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip
kaggle datasets download -d olistbr/marketing-funnel-olist -p data/raw --unzip

# 5. Run ingestion and validation
python 03_ingestion/load_data.py
python 04_data_validation/validate.py

# 6. Launch the dashboard
streamlit run 07_dashboard/app.py
```

## What This Project Does Differently

Built with reference to existing public Olist analyses on GitHub, this project differs in a few concrete, deliberate ways:

- Postgres with enforced constraints (primary keys, foreign keys, `CHECK` constraints) rather than SQLite — enabling real referential integrity checks, not just a place to dump CSVs.
- A dedicated, rerunnable data validation stage with a written report documenting every issue found and how it was resolved — not just cleaning steps assumed to be correct.
- An iteratively-improved, honestly-evaluated delivery-delay model: class imbalance is explicitly addressed and measured (precision/recall/F1/ROC-AUC, not just accuracy), and a feature-engineering pass is documented with its actual before/after impact rather than a single reported number.
- The marketing funnel dataset is integrated and its actual business meaning (seller acquisition, not shopper acquisition) is investigated and corrected rather than assumed.
- Two independent, browser-accessible dashboards (Streamlit and Power BI) rather than a `.pbix` file requiring Power BI Desktop to view.

## Acknowledgments

Built while learning data engineering and analytics end-to-end used throughout for explanation, debugging, and code review, very design decision, data issue, and fix in this repository was worked through and understood.


**Author:** Saurav Raj Khanal