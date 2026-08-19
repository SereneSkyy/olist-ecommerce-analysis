# Data Sources

This folder documents where the project's data comes from. The actual raw
CSV files live in `data/raw/` (excluded from version control — see
`.gitignore`) and are not committed to this repository, since redistributing
someone else's dataset isn't appropriate and raw data doesn't belong in git.
This folder exists to document scope and lineage instead.

## Core dataset: Olist Brazilian E-Commerce

- **Source:** [Kaggle — olistbr/brazilian-ecommerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- **License:** CC BY-NC-SA 4.0
- **Coverage:** ~100,000 orders placed on the Olist marketplace between 2016 and 2018, across multiple Brazilian marketplaces.
- **Files (9 CSVs):**
  - `olist_customers_dataset.csv`
  - `olist_orders_dataset.csv`
  - `olist_order_items_dataset.csv`
  - `olist_order_payments_dataset.csv`
  - `olist_order_reviews_dataset.csv`
  - `olist_products_dataset.csv`
  - `olist_sellers_dataset.csv`
  - `olist_geolocation_dataset.csv`
  - `product_category_name_translation.csv`

## Marketing funnel dataset: Olist Marketing Funnel

- **Source:** [Kaggle — olistbr/marketing-funnel-olist](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist)
- **License:** CC BY-NC-SA 4.0
- **Coverage:** Olist's internal B2B sales funnel data for onboarding *sellers*
  onto the platform — not shopper acquisition data. See the main README's
  "Marketing Funnel Integration" section for how this was discovered and why
  Business Question #1 was revised as a result.
- **Files (2 CSVs):**
  - `olist_marketing_qualified_leads_dataset.csv`
  - `olist_closed_deals_dataset.csv`

## How to obtain the data

Requires a Kaggle account and API access token. See the main README's
"How to Run" section, step 4, for the exact download commands.

