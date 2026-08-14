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

# Note: geolocation and dim_reviews are deliberately excluded from a naive
# raw-vs-loaded row count match — geolocation is aggregated (1,000,163 raw
# rows -> 19,015 unique zip prefixes) and dim_reviews uses a composite key
# but still loads 1:1, so it's included as a normal check.
TABLE_SOURCE_MAP = [
    {"csv": "olist_customers_dataset.csv", "table": "dim_customers", "expect_exact_match": True},
    {"csv": "olist_sellers_dataset.csv", "table": "dim_sellers", "expect_exact_match": True},
    {"csv": "product_category_name_translation.csv", "table": "dim_product_category_translation", "expect_exact_match": False},  # +2 manually inserted categories
    {"csv": "olist_products_dataset.csv", "table": "dim_products", "expect_exact_match": True},
    {"csv": "olist_orders_dataset.csv", "table": "dim_orders", "expect_exact_match": True},
    {"csv": "olist_order_reviews_dataset.csv", "table": "dim_reviews", "expect_exact_match": True},
    {"csv": "olist_order_items_dataset.csv", "table": "fact_order_items", "expect_exact_match": True},
    {"csv": "olist_order_payments_dataset.csv", "table": "fact_order_payments", "expect_exact_match": True},
]


def check_row_counts():
    print("=" * 60)
    print("CHECK 1: Row count reconciliation")
    print("=" * 60)

    results = []
    with engine.connect() as conn:
        for entry in TABLE_SOURCE_MAP:
            csv_path = os.path.join(RAW_DIR, entry["csv"])
            raw_count = len(pd.read_csv(csv_path, usecols=[0]))

            loaded_count = conn.execute(
                text(f"SELECT COUNT(*) FROM {entry['table']}")
            ).scalar()

            if entry["expect_exact_match"]:
                status = "OK" if raw_count == loaded_count else "MISMATCH"
            else:
                status = "OK (expected difference)" if loaded_count >= raw_count else "MISMATCH"

            results.append({
                "table": entry["table"],
                "raw_rows": raw_count,
                "loaded_rows": loaded_count,
                "status": status,
            })

            print(f"  {entry['table']:<32} raw={raw_count:<8} loaded={loaded_count:<8} [{status}]")

    print()
    return results


def check_null_thresholds():
    print("=" * 60)
    print("CHECK 2: Null thresholds")
    print("=" * 60)

    with engine.connect() as conn:
        # Columns that should NEVER be null, regardless of anything else
        hard_required = [
            ("dim_customers", "customer_id"),
            ("dim_orders", "order_id"),
            ("dim_orders", "customer_id"),
            ("dim_orders", "order_purchase_timestamp"),
            ("dim_products", "product_id"),
            ("dim_sellers", "seller_id"),
            ("fact_order_items", "price"),
            ("fact_order_items", "freight_value"),
            ("fact_order_payments", "payment_value"),
        ]

        print("\n-- Hard-required columns (any null here is a real problem) --")
        for table, column in hard_required:
            null_count = conn.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL")
            ).scalar()
            total = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            pct = (null_count / total * 100) if total else 0
            status = "OK" if null_count == 0 else "FAIL"
            print(f"  {table}.{column:<30} nulls={null_count:<6} ({pct:.2f}%) [{status}]")

        # Columns expected to have SOME nulls, tied to order_status
        print("\n-- Status-dependent date columns (nulls expected, check they align with status) --")
        status_dependent = [
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
        ]
        for column in status_dependent:
            result = conn.execute(
                text(f"""
                    SELECT order_status, COUNT(*) 
                    FROM dim_orders 
                    WHERE {column} IS NULL 
                    GROUP BY order_status 
                    ORDER BY COUNT(*) DESC
                """)
            ).fetchall()
            total_nulls = sum(r[1] for r in result)
            print(f"\n  {column}: {total_nulls} total nulls, broken down by order_status:")
            for status, count in result:
                print(f"    {status:<15} {count}")

    print()


def check_duplicates():
    print("=" * 60)
    print("CHECK 3: Duplicates and uniqueness")
    print("=" * 60)

    with engine.connect() as conn:
        # Columns that are primary keys - verify Postgres's own guarantee
        print("\n-- Primary key columns (should always show 0 duplicates) --")
        pk_checks = [
            ("dim_customers", "customer_id"),
            ("dim_orders", "order_id"),
            ("dim_products", "product_id"),
            ("dim_sellers", "seller_id"),
        ]
        for table, column in pk_checks:
            dupe_count = conn.execute(
                text(f"""
                    SELECT COUNT(*) FROM (
                        SELECT {column} FROM {table}
                        GROUP BY {column} HAVING COUNT(*) > 1
                    ) sub
                """)
            ).scalar()
            status = "OK" if dupe_count == 0 else "UNEXPECTED"
            print(f"  {table}.{column:<20} duplicate values={dupe_count} [{status}]")

        # The review_id case - expected repeats, check the count matches what we documented
        print("\n-- dim_reviews.review_id (repeats expected, verifying against documented finding) --")
        review_dupes = conn.execute(
            text("""
                SELECT COUNT(*) FROM (
                    SELECT review_id FROM dim_reviews
                    GROUP BY review_id HAVING COUNT(*) > 1
                ) sub
            """)
        ).scalar()
        expected = 789
        status = "MATCHES DOCUMENTED FINDING" if review_dupes == expected else "CHANGED - INVESTIGATE"
        print(f"  review_ids appearing more than once: {review_dupes} (expected {expected}) [{status}]")

        # customer_id vs customer_unique_id - confirm the expected repeat pattern
        print("\n-- dim_customers: customer_id vs customer_unique_id --")
        total_customers = conn.execute(text("SELECT COUNT(*) FROM dim_customers")).scalar()
        unique_people = conn.execute(
            text("SELECT COUNT(DISTINCT customer_unique_id) FROM dim_customers")
        ).scalar()
        returning = total_customers - unique_people
        print(f"  Total customer_id records: {total_customers}")
        print(f"  Distinct customer_unique_id (real people): {unique_people}")
        print(f"  Implied returning-customer order records: {returning}")

    print()


def check_integrity_and_ranges():
    print("=" * 60)
    print("CHECK 4: Referential integrity and value ranges")
    print("=" * 60)

    with engine.connect() as conn:
        print("\n-- Orphaned foreign keys (should always be 0, Postgres enforces this) --")
        fk_checks = [
            ("fact_order_items", "product_id", "dim_products", "product_id"),
            ("fact_order_items", "seller_id", "dim_sellers", "seller_id"),
            ("fact_order_items", "order_id", "dim_orders", "order_id"),
            ("dim_reviews", "order_id", "dim_orders", "order_id"),
        ]
        for child_table, child_col, parent_table, parent_col in fk_checks:
            orphans = conn.execute(
                text(f"""
                    SELECT COUNT(*) FROM {child_table} c
                    LEFT JOIN {parent_table} p ON c.{child_col} = p.{parent_col}
                    WHERE p.{parent_col} IS NULL
                """)
            ).scalar()
            status = "OK" if orphans == 0 else "BROKEN"
            print(f"  {child_table}.{child_col} -> {parent_table}.{parent_col}: {orphans} orphans [{status}]")

        print("\n-- Value range checks --")
        neg_price = conn.execute(
            text("SELECT COUNT(*) FROM fact_order_items WHERE price < 0")
        ).scalar()
        print(f"  Negative prices in fact_order_items: {neg_price} [{'OK' if neg_price == 0 else 'FAIL'}]")

        bad_scores = conn.execute(
            text("SELECT COUNT(*) FROM dim_reviews WHERE review_score NOT BETWEEN 1 AND 5")
        ).scalar()
        print(f"  Review scores outside 1-5: {bad_scores} [{'OK' if bad_scores == 0 else 'FAIL'}]")

        bad_dates = conn.execute(
            text("""
                SELECT COUNT(*) FROM dim_orders 
                WHERE order_delivered_customer_date IS NOT NULL 
                AND order_delivered_customer_date < order_purchase_timestamp
            """)
        ).scalar()
        print(f"  Orders delivered before they were purchased: {bad_dates} [{'OK' if bad_dates == 0 else 'FAIL'}]")

    print()


if __name__ == "__main__":
    check_row_counts()
    check_null_thresholds()
    check_duplicates()
    check_integrity_and_ranges()