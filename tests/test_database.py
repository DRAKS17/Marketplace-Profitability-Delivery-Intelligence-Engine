"""
Automated Validation Tests for PostgreSQL Analytical Warehouse.

Tests verify:
1. PostgreSQL connectivity to marketplace_analytics database.
2. Existence of multi-layer schemas (stg, core, mart).
3. Record counts across all dimension and fact tables.
4. Foreign key referential integrity in core schema.
5. Zero-fanout financial reconciliation between fact_orders and fact_order_items.
"""

import pytest
from sqlalchemy import text

from src.marketplace_intelligence.database import get_postgres_engine


def _is_postgres_available() -> bool:
    try:
        engine = get_postgres_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(
    not _is_postgres_available(),
    reason="PostgreSQL marketplace_analytics database not accessible",
)


@pytest.fixture(scope="module")
def db_engine():
    """Provides SQLAlchemy engine connected to marketplace_analytics."""
    engine = get_postgres_engine()
    yield engine
    engine.dispose()


def test_database_connection(db_engine):
    """Confirms successful connection to target PostgreSQL database."""
    with db_engine.connect() as conn:
        db_name = conn.execute(text("SELECT current_database()")).scalar()
        assert db_name == "marketplace_analytics"


def test_schemas_exist(db_engine):
    """Confirms all three architectural schemas exist."""
    with db_engine.connect() as conn:
        schemas = (
            conn.execute(
                text(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('stg', 'core', 'mart')"
                )
            )
            .scalars()
            .all()
        )
        assert set(schemas) == {"stg", "core", "mart"}


def test_dimensional_table_row_counts(db_engine):
    """Confirms dimension tables are populated with correct entity counts."""
    expected = {
        "core.dim_customer": 99441,
        "core.dim_seller": 3095,
        "core.dim_product": 32951,
        "core.dim_date": 1827,
        "core.dim_location": 19010,
    }
    with db_engine.connect() as conn:
        for table, expected_cnt in expected.items():
            actual = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            assert actual == expected_cnt, (
                f"{table} expected {expected_cnt:,} rows, found {actual:,}."
            )


def test_fact_table_row_counts(db_engine):
    """Confirms fact tables are populated with exact grain counts."""
    expected = {
        "core.fact_orders": 99441,
        "core.fact_order_items": 112650,
        "core.fact_payments": 103886,
        "core.fact_reviews": 99224,
    }
    with db_engine.connect() as conn:
        for table, expected_cnt in expected.items():
            actual = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            assert actual == expected_cnt, (
                f"{table} expected {expected_cnt:,} rows, found {actual:,}."
            )


def test_foreign_key_referential_integrity(db_engine):
    """Confirms zero orphan foreign keys in fact_orders."""
    with db_engine.connect() as conn:
        orphan_customers = conn.execute(
            text("""
                SELECT COUNT(*) FROM core.fact_orders o
                LEFT JOIN core.dim_customer c ON o.customer_key = c.customer_key
                WHERE c.customer_key IS NULL
            """)
        ).scalar()
        assert orphan_customers == 0, (
            "Found orphan customer foreign keys in fact_orders."
        )

        orphan_dates = conn.execute(
            text("""
                SELECT COUNT(*) FROM core.fact_orders o
                LEFT JOIN core.dim_date d ON o.purchase_date_key = d.date_key
                WHERE d.date_key IS NULL
            """)
        ).scalar()
        assert orphan_dates == 0, "Found orphan date foreign keys in fact_orders."


def test_zero_fanout_financial_reconciliation(db_engine):
    """Confirms exact penny-perfect financial reconciliation between fact_orders and fact_order_items."""
    with db_engine.connect() as conn:
        order_gmv = conn.execute(
            text("SELECT ROUND(SUM(order_total_item_value), 2) FROM core.fact_orders")
        ).scalar()
        item_gmv = conn.execute(
            text("SELECT ROUND(SUM(price), 2) FROM core.fact_order_items")
        ).scalar()

        diff = abs(float(order_gmv) - float(item_gmv))
        assert diff == 0.0, (
            f"Financial reconciliation failed! Orders GMV: {order_gmv}, Items GMV: {item_gmv}, Diff: {diff}"
        )
