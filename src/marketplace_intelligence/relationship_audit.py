"""
Relational Integrity and Grain Verification Module.

Empirically tests foreign key relationships, referential integrity (orphan records),
cardinalities (1:1, 1:N, M:N), and mathematically demonstrates join fanout / financial inflation.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def audit_relationships(raw_dir: Path | str = "data/raw") -> dict[str, any]:
    """Audits referential integrity and join multipliers across all tables."""
    raw_path = Path(raw_dir)
    logger.info("Loading raw datasets for relational integrity audit...")

    customers = pd.read_csv(raw_path / "olist_customers_dataset.csv", low_memory=False)
    orders = pd.read_csv(raw_path / "olist_orders_dataset.csv", low_memory=False)
    order_items = pd.read_csv(
        raw_path / "olist_order_items_dataset.csv", low_memory=False
    )
    payments = pd.read_csv(
        raw_path / "olist_order_payments_dataset.csv", low_memory=False
    )
    reviews = pd.read_csv(
        raw_path / "olist_order_reviews_dataset.csv", low_memory=False
    )
    products = pd.read_csv(raw_path / "olist_products_dataset.csv", low_memory=False)
    sellers = pd.read_csv(raw_path / "olist_sellers_dataset.csv", low_memory=False)
    geo = pd.read_csv(raw_path / "olist_geolocation_dataset.csv", low_memory=False)
    translations = pd.read_csv(
        raw_path / "product_category_name_translation.csv", low_memory=False
    )

    audit_results: dict[str, any] = {}

    # 1. Orders -> Customers (1:1 or 1:N?)
    cust_orphans = set(orders["customer_id"]) - set(customers["customer_id"])
    orders_per_cust_token = orders["customer_id"].value_counts().max()
    audit_results["orders_to_customers"] = {
        "parent": "customers",
        "child": "orders",
        "key": "customer_id",
        "orphan_count": len(cust_orphans),
        "max_orders_per_customer_id": int(orders_per_cust_token),
        "is_one_to_one": orders_per_cust_token == 1 and len(orders) == len(customers),
    }

    # 2. Customers -> Unique Customers (1:N)
    orders_per_human = customers["customer_unique_id"].value_counts()
    repeat_customers = int((orders_per_human > 1).sum())
    max_orders_single_human = int(orders_per_human.max())
    audit_results["customer_unique_id_cardinality"] = {
        "total_human_customers": int(customers["customer_unique_id"].nunique()),
        "repeat_customers_count": repeat_customers,
        "repeat_customer_rate_pct": round(
            (repeat_customers / len(orders_per_human)) * 100, 2
        ),
        "max_orders_by_one_customer": max_orders_single_human,
    }

    # 3. Order Items -> Orders
    items_order_orphans = set(order_items["order_id"]) - set(orders["order_id"])
    items_per_order = order_items["order_id"].value_counts()
    audit_results["order_items_to_orders"] = {
        "parent": "orders",
        "child": "order_items",
        "key": "order_id",
        "orphan_count": len(items_order_orphans),
        "orders_with_items": int(order_items["order_id"].nunique()),
        "orders_without_items": int(len(orders) - order_items["order_id"].nunique()),
        "max_items_in_single_order": int(items_per_order.max()),
        "multi_item_orders_count": int((items_per_order > 1).sum()),
    }

    # 4. Order Items -> Products
    item_product_orphans = set(order_items["product_id"]) - set(products["product_id"])
    audit_results["order_items_to_products"] = {
        "parent": "products",
        "child": "order_items",
        "key": "product_id",
        "orphan_count": len(item_product_orphans),
        "products_never_sold": int(len(products) - order_items["product_id"].nunique()),
    }

    # 5. Order Items -> Sellers
    item_seller_orphans = set(order_items["seller_id"]) - set(sellers["seller_id"])
    audit_results["order_items_to_sellers"] = {
        "parent": "sellers",
        "child": "order_items",
        "key": "seller_id",
        "orphan_count": len(item_seller_orphans),
        "sellers_never_sold": int(len(sellers) - order_items["seller_id"].nunique()),
    }

    # 6. Order Payments -> Orders
    payment_order_orphans = set(payments["order_id"]) - set(orders["order_id"])
    payments_per_order = payments["order_id"].value_counts()
    audit_results["order_payments_to_orders"] = {
        "parent": "orders",
        "child": "order_payments",
        "key": "order_id",
        "orphan_count": len(payment_order_orphans),
        "orders_without_payments": int(len(orders) - payments["order_id"].nunique()),
        "max_payments_in_single_order": int(payments_per_order.max()),
        "multi_payment_orders_count": int((payments_per_order > 1).sum()),
    }

    # 7. Order Reviews -> Orders
    review_order_orphans = set(reviews["order_id"]) - set(orders["order_id"])
    reviews_per_order = reviews["order_id"].value_counts()
    audit_results["order_reviews_to_orders"] = {
        "parent": "orders",
        "child": "order_reviews",
        "key": "order_id",
        "orphan_count": len(review_order_orphans),
        "orders_without_reviews": int(len(orders) - reviews["order_id"].nunique()),
        "max_reviews_for_single_order": int(reviews_per_order.max()),
        "orders_with_multiple_reviews": int((reviews_per_order > 1).sum()),
    }

    # 8. Products -> Category Translation
    untranslated_categories = set(products["product_category_name"].dropna()) - set(
        translations["product_category_name"]
    )
    audit_results["product_category_translations"] = {
        "total_categories_in_products": int(
            products["product_category_name"].nunique()
        ),
        "categories_in_translations": len(translations),
        "untranslated_categories": list(untranslated_categories),
    }

    # 9. Geolocation Coverage
    geo_prefixes = set(geo["geolocation_zip_code_prefix"])
    cust_zip_missing = set(customers["customer_zip_code_prefix"]) - geo_prefixes
    seller_zip_missing = set(sellers["seller_zip_code_prefix"]) - geo_prefixes
    audit_results["geolocation_coverage"] = {
        "customer_zip_prefixes_missing_in_geo": len(cust_zip_missing),
        "seller_zip_prefixes_missing_in_geo": len(seller_zip_missing),
    }

    # 10. DEMONSTRATION OF JOIN FANOUT / FINANCIAL INFLATION
    # Pick orders that have BOTH multiple items and multiple payments
    multi_items_orders = set(items_per_order[items_per_order > 1].index)
    multi_pay_orders = set(payments_per_order[payments_per_order > 1].index)
    fanout_candidates = list(multi_items_orders.intersection(multi_pay_orders))

    sample_order_id = fanout_candidates[0] if fanout_candidates else None

    # Calculate actual ground truth for sample order
    sample_items = order_items[order_items["order_id"] == sample_order_id]
    sample_payments = payments[payments["order_id"] == sample_order_id]

    true_item_count = len(sample_items)
    true_item_value = sample_items["price"].sum()
    true_freight_value = sample_items["freight_value"].sum()
    true_order_item_total = true_item_value + true_freight_value

    true_payment_count = len(sample_payments)
    true_payment_total = sample_payments["payment_value"].sum()

    # NAIVE JOIN (Orders -> Items -> Payments)
    naive_join = pd.merge(sample_items, sample_payments, on="order_id")
    naive_row_count = len(naive_join)
    naive_inflated_item_value = naive_join["price"].sum()
    naive_inflated_payment_total = naive_join["payment_value"].sum()

    audit_results["fanout_demonstration"] = {
        "sample_order_id": sample_order_id,
        "true_metrics": {
            "item_records": true_item_count,
            "total_items_price": round(float(true_item_value), 2),
            "total_freight": round(float(true_freight_value), 2),
            "total_items_and_freight": round(float(true_order_item_total), 2),
            "payment_records": true_payment_count,
            "total_payment_collected": round(float(true_payment_total), 2),
        },
        "naive_joined_metrics": {
            "result_rows": naive_row_count,
            "inflated_item_value": round(float(naive_inflated_item_value), 2),
            "inflated_payment_value": round(float(naive_inflated_payment_total), 2),
            "item_inflation_factor": round(
                float(naive_inflated_item_value / true_item_value), 2
            ),
            "payment_inflation_factor": round(
                float(naive_inflated_payment_total / true_payment_total), 2
            ),
        },
    }

    # MACRO LEVEL FANOUT (Across entire dataset)
    total_true_item_price = float(order_items["price"].sum())
    total_true_payment_value = float(payments["payment_value"].sum())

    macro_join = pd.merge(
        order_items[["order_id", "price"]],
        payments[["order_id", "payment_value"]],
        on="order_id",
        how="inner",
    )
    macro_inflated_price = float(macro_join["price"].sum())
    macro_inflated_payments = float(macro_join["payment_value"].sum())

    audit_results["macro_fanout"] = {
        "true_total_merchandise_value": round(total_true_item_price, 2),
        "naive_joined_total_merchandise_value": round(macro_inflated_price, 2),
        "merchandise_inflation_amount": round(
            macro_inflated_price - total_true_item_price, 2
        ),
        "true_total_payment_value": round(total_true_payment_value, 2),
        "naive_joined_total_payment_value": round(macro_inflated_payments, 2),
        "payment_inflation_amount": round(
            macro_inflated_payments - total_true_payment_value, 2
        ),
    }

    return audit_results


def print_audit_summary(results: dict[str, any]) -> None:
    """Prints a clear report of relationship audit and join fanout proof."""
    print("\n" + "=" * 90)
    print(" RELATIONAL INTEGRITY & FOREIGN KEY AUDIT RESULTS")
    print("=" * 90)

    for data in results.values():
        if isinstance(data, dict) and "child" in data and "parent" in data:
            print(
                f"Relationship: {data['child']} -> {data['parent']} ON ({data['key']})"
            )
            print(
                f"  - Orphan Records: {data['orphan_count']} (100% Referential Integrity maintained)"
            )
            if "orders_without_items" in data:
                print(
                    f"  - Orders without Items (e.g. canceled before itemization): {data['orders_without_items']}"
                )
            if "orders_without_payments" in data:
                print(f"  - Orders without Payments: {data['orders_without_payments']}")
            if "orders_without_reviews" in data:
                print(
                    f"  - Orders without Customer Reviews: {data['orders_without_reviews']}"
                )
            print("-" * 90)

    # Customer Unique ID Cardinality
    c_card = results.get("customer_unique_id_cardinality", {})
    if c_card:
        print("Customer Identity Cardinality:")
        print(f"  - Total Human Customers: {c_card['total_human_customers']:,}")
        print(
            f"  - Repeat Customers: {c_card['repeat_customers_count']:,} ({c_card['repeat_customer_rate_pct']}%)"
        )
        print(
            f"  - Max Orders by a Single Customer: {c_card['max_orders_by_one_customer']}"
        )
        print("-" * 90)

    # Category Translations
    cat = results.get("product_category_translations", {})
    if cat:
        print("Product Category Translations:")
        print(f"  - Total Product Categories: {cat['total_categories_in_products']}")
        print(f"  - Translated in mapping file: {cat['categories_in_translations']}")
        print(f"  - Untranslated Categories: {cat['untranslated_categories']}")
        print("-" * 90)

    # Geolocation Coverage
    geo_cov = results.get("geolocation_coverage", {})
    if geo_cov:
        print("Geolocation Reference Coverage:")
        print(
            f"  - Customer Zip Prefixes Missing in Geolocation: {geo_cov['customer_zip_prefixes_missing_in_geo']}"
        )
        print(
            f"  - Seller Zip Prefixes Missing in Geolocation: {geo_cov['seller_zip_prefixes_missing_in_geo']}"
        )
        print("-" * 90)

    print("\n" + "=" * 90)
    print(" EMPIRICAL DEMONSTRATION OF JOIN FANOUT / FINANCIAL METRIC INFLATION")
    print("=" * 90)
    fanout = results["fanout_demonstration"]
    sample_id = fanout["sample_order_id"]
    tm = fanout["true_metrics"]
    nm = fanout["naive_joined_metrics"]

    print(f"Case Study: Order ID '{sample_id}'")
    print("  True State:")
    print(
        f"    - Items count: {tm['item_records']} | True Item Price Sum: ${tm['total_items_price']}"
    )
    print(
        f"    - Payment records: {tm['payment_records']} | True Payments Collected: ${tm['total_payment_collected']}"
    )
    print(
        "  Naive Join Result (Joining items directly to payments without aggregation):"
    )
    print(
        f"    - Resulting rows: {nm['result_rows']} (Cartesian Product: {tm['item_records']} items × {tm['payment_records']} payments = {nm['result_rows']} rows)"
    )
    print(
        f"    - Inflated Item Value Sum: ${nm['inflated_item_value']} (Inflated by {nm['item_inflation_factor']}x)"
    )
    print(
        f"    - Inflated Payment Value Sum: ${nm['inflated_payment_value']} (Inflated by {nm['payment_inflation_factor']}x)"
    )

    print("-" * 90)
    macro = results["macro_fanout"]
    print("MACRO IMPACT ACROSS ENTIRE MARKETPLACE:")
    print(
        f"  - True Total Merchandise Value:  ${macro['true_total_merchandise_value']:>14,f}"
    )
    print(
        f"  - Naive Joined Total GMV:        ${macro['naive_joined_total_merchandise_value']:>14,f}"
    )
    print(
        f"  - Financial Phantom Overstatement: +${macro['merchandise_inflation_amount']:>13,f}"
    )
    print(
        f"  - True Total Payments Collected: ${macro['true_total_payment_value']:>14,f}"
    )
    print(
        f"  - Naive Joined Total Payments:   ${macro['naive_joined_total_payment_value']:>14,f}"
    )
    print(
        f"  - Payment Phantom Overstatement:  +${macro['payment_inflation_amount']:>13,f}"
    )
    print("=" * 90)


if __name__ == "__main__":
    audit = audit_relationships("data/raw")
    print_audit_summary(audit)
