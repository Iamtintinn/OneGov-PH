"""Add Maya checkout columns to payments if they are missing."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util


def _load_app():
    spec = importlib.util.spec_from_file_location("onegov_flask_app", ROOT / "app.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.create_app()


def column_exists(connection, table: str, column: str) -> bool:
    row = connection.execute(
        text(
            """
            SELECT COUNT(1)
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = :table
              AND column_name = :column
            """
        ),
        {"table": table, "column": column},
    ).scalar()
    return bool(row)


def index_exists(connection, table: str, index: str) -> bool:
    row = connection.execute(
        text(
            """
            SELECT COUNT(1)
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = :table
              AND index_name = :index
            """
        ),
        {"table": table, "index": index},
    ).scalar()
    return bool(row)


def main() -> int:
    application = _load_app()
    from app import db

    with application.app_context():
        with db.engine.begin() as connection:
            if not column_exists(connection, "payments", "provider_checkout_id"):
                connection.execute(
                    text(
                        "ALTER TABLE payments ADD COLUMN provider_checkout_id "
                        "varchar(64) DEFAULT NULL COMMENT 'Maya checkoutId'"
                    )
                )
                print("Added payments.provider_checkout_id")
            else:
                print("payments.provider_checkout_id already present")

            if not column_exists(connection, "payments", "provider_status"):
                connection.execute(
                    text(
                        "ALTER TABLE payments ADD COLUMN provider_status "
                        "varchar(40) DEFAULT NULL COMMENT 'Latest Maya paymentStatus'"
                    )
                )
                print("Added payments.provider_status")
            else:
                print("payments.provider_status already present")

            if not index_exists(connection, "payments", "uq_payments_provider_checkout"):
                connection.execute(
                    text(
                        "ALTER TABLE payments ADD UNIQUE KEY "
                        "uq_payments_provider_checkout (provider_checkout_id)"
                    )
                )
                print("Added unique key uq_payments_provider_checkout")
            else:
                print("uq_payments_provider_checkout already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
