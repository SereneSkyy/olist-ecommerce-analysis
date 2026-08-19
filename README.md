# Olist E-Commerce Analytics: From Acquisition to Delivery

End-to-end analytics project on the Brazilian e-commerce marketplace Olist, covering the full funnel from marketing acquisition through order fulfillment and delivery risk. Built on Postgres with a validated data pipeline, SQL-driven analysis, a delivery-delay classification model, and a browser-accessible dashboard.

## Business Questions

1. Which marketing channels drive the highest-converting, highest-value customers?
2. What are the key drivers of delivery delays, and can they be predicted before dispatch?
3. How do delivery delays affect customer review scores and repeat purchase behavior?
4. Which product categories and seller regions contribute most to revenue and to delay risk?
5. How can customers be segmented (RFM) to prioritize retention efforts?

## Dataset

- **Core dataset:** [Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — 8 relational CSVs covering orders, customers, products, sellers, payments, reviews, and geolocation (2016-2018).
- **Marketing funnel dataset:** Olist Marketing Funnel dataset — closed deals and marketing qualified leads, joined against the core dataset to connect acquisition to downstream revenue and delivery outcomes.

## Architecture and Tech Stack

| Layer | Tool | Reason |
|---|---|---|
| Database | PostgreSQL | Production-realistic: supports indexing, constraints, `EXPLAIN ANALYZE` query tuning — not available in SQLite |
| Ingestion | Python (pandas, SQLAlchemy) | Scripted, repeatable load rather than manual CSV import |
| Validation | Python (pandera / custom checks) | Schema checks, null thresholds, referential integrity between fact and dimension tables |
| Modeling | scikit-learn | Delivery-delay classification, review-score regression, RFM segmentation |
| Dashboard | Streamlit / Power BI (Publish to Web) | Browser-accessible without requiring Power BI Desktop |

## Project Structure

```
olist-ecommerce-analytics/
├── data/
│   └── raw/                     # original CSVs (not committed, see data/README.md)
├── 01_data_sources/              # dataset scope, lineage, source documentation
├── 02_ddl_table_creation/        # staging + star schema DDL
├── 03_ingestion/                 # load scripts (pandas + SQLAlchemy)
├── 04_data_validation/           # schema checks, null thresholds, referential integrity
├── 05_sql_analysis/              # analytical SQL: joins, aggregations, window functions
├── 06_modeling/                  # delivery-delay model, review regressor, RFM segmentation
├── 07_dashboard/                 # Streamlit app or Power BI report
├── tests/                        # unit tests for ingestion and validation logic
├── requirements.txt
└── README.md
```

## Data Model

Star schema design, modeled around the order as the core business event.

**Fact table:** `fact_orders` — one row per order line item, with foreign keys to all dimensions and measures for price, freight, and delivery time.

**Dimension tables:** `dim_customers`, `dim_products`, `dim_sellers`, `dim_payments`, `dim_reviews`, `dim_geolocation`, `dim_marketing_leads`.

Fact/dimension boundaries and the reasoning behind excluded or reclassified orders (e.g. canceled orders, missing delivery timestamps) are documented in `02_ddl_table_creation/README.md`.

## Data Validation

Before any analysis runs against the warehouse, a validation stage checks:

- Referential integrity between `fact_orders` and each dimension table
- Null thresholds on required fields (delivery timestamps, order status, payment value)
- Duplicate primary keys
- Value-range checks (e.g. no negative prices or freight values)

Validation results and any records excluded or flagged are logged in `04_data_validation/validation_report.md`, along with the reasoning for each exclusion.

## Modeling Notes

The delivery-delay classifier predicts whether an order will arrive after its estimated delivery date, using features available at the time of dispatch (product category, freight value, seller region, order weekday).

Because on-time deliveries substantially outnumber late ones, accuracy alone is a misleading metric. Model evaluation reports precision, recall, and F1 for the minority (late) class alongside ROC-AUC, and class weighting is applied during training to address the imbalance. This tradeoff, and why accuracy was not used as the primary metric, is documented in `06_modeling/README.md`.

## Key Findings

*(To be filled in as analysis is completed.)*

- Marketing channel performance:
- Delivery delay drivers:
- Delay-to-review-score relationship:
- Category / region revenue and risk breakdown:
- Customer segments (RFM):

## Dashboard

[Link to deployed Streamlit app or Power BI web report]

## How to Run

```bash
# 1. Clone and install dependencies
git clone <repo-url>
cd olist-ecommerce-analytics
pip install -r requirements.txt

# 2. Set up Postgres and configure connection in .env
createdb olist_analytics

# 3. Run ingestion
python 03_ingestion/load_data.py

# 4. Run validation
python 04_data_validation/validate.py

# 5. Run analysis / modeling notebooks or scripts as needed
```
