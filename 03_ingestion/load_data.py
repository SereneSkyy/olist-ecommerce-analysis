import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

RAW_DIR = "data/raw"

# order matters here so parent tables are created first

LOAD_PLAN = [
    {
        "csv": "olist_customers_dataset.csv",
        "table": "dim_customers",
    },
    {
        "csv": "olist_sellers_dataset.csv",
        "table": "dim_sellers",
    },
    {
        "csv": "product_category_name_translation.csv",
        "table": "dim_product_category_translation",
    },
    {
        "csv": "olist_products_dataset.csv",
        "table": "dim_products",
    },
    {
        "csv": "olist_geolocation_dataset.csv",
        "table": "dim_geolocation",
    },
    {
        "csv": "olist_orders_dataset.csv",
        "table": "dim_orders",
    },
    {
        "csv": "olist_order_reviews_dataset.csv",
        "table": "dim_reviews",
    },
    {
        "csv": "olist_order_items_dataset.csv",
        "table": "fact_order_items",
    },
    {
        "csv": "olist_order_payments_dataset.csv",
        "table": "fact_order_payments",
    },
        {
        "csv": "olist_marketing_qualified_leads_dataset.csv",
        "table": "dim_marketing_leads",
    },
    {
        "csv": "olist_closed_deals_dataset.csv",
        "table": "dim_closed_deals",
    },
]

def load_table(csv_filename, table_name):
    path = os.path.join(RAW_DIR, csv_filename)
    print(f"Reading {csv_filename}...")
    df = pd.read_csv(path)

    print(f" {len(df)} rows found. Truncating {table_name} first...")
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))

    print(f" Loading into {table_name}...")
    df.to_sql(table_name, engine, if_exists="append", index=False)
    print(f" Done: {table_name}\n")

def ensure_missing_categories():
    """
    Ensure that all product categories in the products table have a 
    corresponding entry in the product category translation table.
    """
    missing_categories = [
        ("pc_gamer", "gaming_pc"),
        ("portateis_cozinha_e_preparadores_de_alimentos", "portable_kitchen_food_preparers"),
    ]
    print(" Ensuring known missing product categoreis exits ...")
    with engine.begin() as conn:
        for pt_name, en_name in missing_categories:
            conn.execute(
                text(
                    """
                    INSERT INTO dim_product_category_translation (product_category_name, product_category_name_english)
                    VALUES (:pt_name, :en_name)
                    ON CONFLICT (product_category_name) DO NOTHING
                    """
                ),
                {"pt_name": pt_name, "en_name": en_name}
            )
    print(" Done. \n")

def load_geolocation():
    path = os.path.join(RAW_DIR, "olist_geolocation_dataset.csv")
    print("Reading olist_geolocation_dataset.csv...")
    df = pd.read_csv(path)
    print(f"  {len(df)} raw rows found.")

    print("  Aggregating to one row per zip_code_prefix (averaging lat/lng)...")
    agg = (
        df.groupby("geolocation_zip_code_prefix")
        .agg(
            geolocation_lat=("geolocation_lat", "mean"),
            geolocation_lng=("geolocation_lng", "mean"),
            geolocation_city=("geolocation_city", "first"),
            geolocation_state=("geolocation_state", "first"),
        )
        .reset_index()
    )
    print(f"  Reduced to {len(agg)} unique prefixes.")

    print("  Truncating dim_geolocation first...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dim_geolocation CASCADE"))

    print("  Loading into dim_geolocation...")
    agg.to_sql("dim_geolocation", engine, if_exists="append", index=False)
    print("  Done: dim_geolocation\n")

def main():
    for entry in LOAD_PLAN:
        if entry["table"] == "dim_geolocation":
            load_geolocation()
        else:
            load_table(entry["csv"], entry["table"])
        if entry["table"] == "dim_product_category_translation":
            ensure_missing_categories()
    print("All tables loaded successfully.")

if __name__ == "__main__":
    main()

