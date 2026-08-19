"""
Olist Funnel-to-Fulfillment Dashboard
Streamlit app pulling directly from the validated Postgres warehouse.
Run with: streamlit run app.py
"""

import os
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Olist Funnel-to-Fulfillment",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Database connection (cached so it's created once per session, not per rerun)
# ---------------------------------------------------------------------------
@st.cache_resource
def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )

engine = get_engine()

# Cache query results for 1 hour so navigating tabs doesn't re-hit Postgres every time
@st.cache_data(ttl=3600)
def run_query(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, engine)


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.title("Olist Analytics")
page = st.sidebar.radio(
    "Section",
    [
        "Overview",
        "Revenue & Delay by Category",
        "Delay by Seller Region",
        "Delay Impact on Reviews",
        "Customer Segments (RFM)",
        "Marketing Channel Performance",
        "Delivery-Delay Model",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Built on a validated Postgres star schema. "
    "See the project README for full methodology and data validation notes."
)

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
if page == "Overview":
    st.title("Olist E-Commerce: Funnel-to-Fulfillment Analytics")
    st.markdown(
        "End-to-end analysis connecting marketing acquisition, order fulfillment, "
        "delivery risk, and customer retention for the Olist Brazilian marketplace."
    )

    kpi_query = """
        SELECT
            (SELECT COUNT(*) FROM dim_orders) AS total_orders,
            (SELECT COUNT(DISTINCT customer_unique_id) FROM dim_customers) AS total_customers,
            (SELECT ROUND(SUM(price)::numeric, 2) FROM fact_order_items) AS total_revenue,
            (SELECT ROUND(AVG(review_score)::numeric, 2) FROM dim_reviews) AS avg_review_score
    """
    kpis = run_query(kpi_query).iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Orders", f"{int(kpis['total_orders']):,}")
    col2.metric("Unique Customers", f"{int(kpis['total_customers']):,}")
    col3.metric("Total Revenue", f"${kpis['total_revenue']:,.0f}")
    col4.metric("Avg Review Score", f"{kpis['avg_review_score']:.2f} / 5")

    st.markdown("### Key Findings")
    st.markdown(
        """
- **Revenue and delay risk don't move together.** `health_beauty` is the top revenue
  category, but its delay rate is only moderate — the worst delay rate belongs to a
  different, lower-revenue category.
- **Seller region matters more than product category for delay risk.** One state
  (Maranhão) shows a delay rate nearly 3x the next-worst state.
- **Late deliveries have a large effect on review scores** — a 1.7-point gap on a
  5-point scale between on-time and late orders.
- **High spend and loyalty don't necessarily go together** — several top lifetime-value
  customers made only a single purchase, motivating the RFM segmentation below.
        """
    )

# ---------------------------------------------------------------------------
# Revenue & Delay by Category
# ---------------------------------------------------------------------------
elif page == "Revenue & Delay by Category":
    st.title("Revenue and Delay Risk by Product Category")

    revenue_query = """
        SELECT t.product_category_name_english AS category, SUM(f.price) AS total_revenue,
               COUNT(*) AS items_sold
        FROM fact_order_items f
        JOIN dim_products p ON f.product_id = p.product_id
        JOIN dim_product_category_translation t ON p.product_category_name = t.product_category_name
        GROUP BY t.product_category_name_english
        ORDER BY total_revenue DESC
        LIMIT 15
    """
    revenue_df = run_query(revenue_query)

    delay_query = """
        SELECT t.product_category_name_english AS category,
               COUNT(*) AS total_delivered_items,
               ROUND(100.0 * SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
                   THEN 1 ELSE 0 END) / COUNT(*), 2) AS late_pct
        FROM fact_order_items f
        JOIN dim_products p ON f.product_id = p.product_id
        JOIN dim_product_category_translation t ON p.product_category_name = t.product_category_name
        JOIN dim_orders o ON f.order_id = o.order_id
        WHERE o.order_delivered_customer_date IS NOT NULL
        GROUP BY t.product_category_name_english
        HAVING COUNT(*) >= 100
        ORDER BY late_pct DESC
        LIMIT 15
    """
    delay_df = run_query(delay_query)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top 15 Categories by Revenue")
        fig = px.bar(revenue_df, x="total_revenue", y="category", orientation="h",
                     labels={"total_revenue": "Total Revenue ($)", "category": ""})
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Top 15 Categories by Delay Rate")
        fig = px.bar(delay_df, x="late_pct", y="category", orientation="h",
                     labels={"late_pct": "Late Delivery Rate (%)", "category": ""},
                     color_discrete_sequence=["#d62728"])
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Delay rate limited to categories with at least 100 delivered items, to avoid "
        "small-sample noise. Orders with a null delivery date are excluded (see validation report)."
    )

# ---------------------------------------------------------------------------
# Delay by Seller Region
# ---------------------------------------------------------------------------
elif page == "Delay by Seller Region":
    st.title("Delivery Delay Rate by Seller State")

    region_query = """
        SELECT s.seller_state,
               COUNT(*) AS total_delivered_items,
               ROUND(100.0 * SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
                   THEN 1 ELSE 0 END) / COUNT(*), 2) AS late_pct
        FROM fact_order_items f
        JOIN dim_sellers s ON f.seller_id = s.seller_id
        JOIN dim_orders o ON f.order_id = o.order_id
        WHERE o.order_delivered_customer_date IS NOT NULL
        GROUP BY s.seller_state
        HAVING COUNT(*) >= 100
        ORDER BY late_pct DESC
    """
    region_df = run_query(region_query)

    fig = px.bar(region_df, x="seller_state", y="late_pct",
                 labels={"seller_state": "Seller State", "late_pct": "Late Delivery Rate (%)"},
                 color="late_pct", color_continuous_scale="Reds")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(region_df, use_container_width=True, hide_index=True)
    st.caption(
        "States with fewer than 100 delivered items are excluded to avoid small-sample noise. "
        "Maranhão (MA) stands out as a severe outlier."
    )

# ---------------------------------------------------------------------------
# Delay Impact on Reviews
# ---------------------------------------------------------------------------
elif page == "Delay Impact on Reviews":
    st.title("Effect of Delivery Delay on Customer Reviews")

    review_query = """
        SELECT
            CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
                 THEN 'Late' ELSE 'On Time' END AS delivery_status,
            r.review_score
        FROM dim_orders o
        JOIN dim_reviews r ON o.order_id = r.order_id
        WHERE o.order_delivered_customer_date IS NOT NULL
    """
    review_df = run_query(review_query)

    summary = review_df.groupby("delivery_status")["review_score"].agg(
        avg_score="mean", order_count="count"
    ).round(2).reset_index()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Summary")
        st.dataframe(summary, use_container_width=True, hide_index=True)
    with col2:
        st.subheader("Review Score Distribution")
        fig = px.histogram(review_df, x="review_score", color="delivery_status",
                            barmode="group", nbins=5,
                            labels={"review_score": "Review Score (1-5)"})
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f"**On-time orders average {summary[summary.delivery_status == 'On Time']['avg_score'].values[0]} "
        f"stars, versus {summary[summary.delivery_status == 'Late']['avg_score'].values[0]} stars for late "
        "orders** — the strongest relationship found in this analysis."
    )

# ---------------------------------------------------------------------------
# RFM Segmentation
# ---------------------------------------------------------------------------
elif page == "Customer Segments (RFM)":
    st.title("Customer Segmentation (Recency / Frequency / Monetary)")

    try:
        rfm_summary = pd.read_csv("../06_modeling/outputs/rfm_segment_summary.csv")
        st.dataframe(rfm_summary, use_container_width=True, hide_index=True)

        fig = px.bar(rfm_summary, x="segment", y="total_monetary",
                     labels={"segment": "Segment", "total_monetary": "Total Historical Spend ($)"},
                     color="segment")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            """
**Segments defined on recency and monetary value** (median split), rather than a
standard 5x5 RFM grid — frequency is heavily concentrated at 1 purchase for the
large majority of customers, so it doesn't meaningfully separate segments here.

- **Champions**: recent, high spend
- **At Risk**: high spend, but haven't ordered in a long time — the highest-priority
  retention target, representing millions in historical revenue
- **New / Low Value**: recent, low spend
- **Lost**: low spend, not recent
            """
        )
    except FileNotFoundError:
        st.warning(
            "RFM output not found. Run the RFM segmentation cells in "
            "06_modeling/delivery_delay_model.ipynb and export to "
            "06_modeling/outputs/rfm_segment_summary.csv first."
        )

# ---------------------------------------------------------------------------
# Marketing Channel Performance
# ---------------------------------------------------------------------------
elif page == "Marketing Channel Performance":
    st.title("Seller Acquisition: Marketing Channel Performance")
    st.caption(
        "Note: this tracks Olist's own B2B sales funnel for onboarding sellers, "
        "not shopper acquisition — see README for why this question was revised."
    )

    channel_query = """
        SELECT
            l.origin,
            COUNT(DISTINCT l.mql_id) AS total_leads,
            COUNT(DISTINCT d.mql_id) AS closed_deals,
            ROUND(100.0 * COUNT(DISTINCT d.mql_id) / COUNT(DISTINCT l.mql_id), 2) AS conversion_pct,
            ROUND(COALESCE(SUM(f.price), 0)::numeric, 2) AS total_revenue
        FROM dim_marketing_leads l
        LEFT JOIN dim_closed_deals d ON l.mql_id = d.mql_id
        LEFT JOIN dim_sellers s ON d.seller_id = s.seller_id
        LEFT JOIN fact_order_items f ON s.seller_id = f.seller_id
        WHERE l.origin IS NOT NULL
        GROUP BY l.origin
        ORDER BY total_revenue DESC
    """
    channel_df = run_query(channel_query)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Revenue by Channel")
        fig = px.bar(channel_df, x="origin", y="total_revenue",
                     labels={"origin": "Channel", "total_revenue": "Revenue ($)"})
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Conversion Rate by Channel")
        fig = px.bar(channel_df, x="origin", y="conversion_pct",
                     labels={"origin": "Channel", "conversion_pct": "Conversion Rate (%)"},
                     color_discrete_sequence=["#2ca02c"])
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(channel_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Delivery-Delay Model
# ---------------------------------------------------------------------------
elif page == "Delivery-Delay Model":
    st.title("Delivery-Delay Prediction Model")

    st.markdown(
        """
A Random Forest classifier predicting whether an order will be delivered late,
using only features known before dispatch.
        """
    )

    model_comparison = pd.DataFrame({
        "Model": ["v1: naive", "v1: class_weight balanced", "v2: + distance & delivery window"],
        "ROC-AUC": [0.669, 0.673, 0.769],
        "Recall (late)": [0.15, 0.22, 0.24],
        "Precision (late)": [0.50, 0.27, 0.52],
    })
    st.dataframe(model_comparison, use_container_width=True, hide_index=True)

    fig = px.line(model_comparison, x="Model", y="ROC-AUC", markers=True,
                  title="ROC-AUC Across Model Iterations")
    fig.update_yaxes(range=[0.6, 0.85])
    st.plotly_chart(fig, use_container_width=True)

    try:
        importance_df = pd.read_csv("../06_modeling/outputs/feature_importances.csv").head(15)
        st.subheader("Top Feature Importances (v2 model)")
        fig2 = px.bar(importance_df, x="importance", y="feature", orientation="h",
                      labels={"importance": "Importance", "feature": ""})
        fig2.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig2, use_container_width=True)
    except FileNotFoundError:
        st.info("Feature importance data not found — export from the modeling notebook first.")

    st.markdown(
        """
**Honest limitation:** even the improved model misses roughly 3 in 4 late orders
(recall 0.24). Delivery-window tightness and shipping distance carry more signal
than product or pricing attributes, but true logistics data (carrier performance,
warehouse processing time, weather) — not available in this public dataset — would
likely be needed for a materially stronger model.
        """
    )