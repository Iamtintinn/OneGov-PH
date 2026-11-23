"""Create missing OneGov PH tables and verify the database safely.

Usage:
    python database/migrate.py            # create missing tables, then verify
    python database/migrate.py --seed     # also load database/seed.sql (idempotent)
    python database/migrate.py --check    # verify only, never create anything

Safety:
    * Never drops or truncates a table.
    * Never deletes or updates existing rows.
    * Only creates tables that are missing (checkfirst).
    * seed.sql uses INSERT IGNORE and reference data only.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Config

SEED_FILE = PROJECT_ROOT / "database" / "seed.sql"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def _safe_uri():
    return make_url(Config.SQLALCHEMY_DATABASE_URI).render_as_string(hide_password=True)


def _split_sql(source: str):
    """Split a .sql file into statements, respecting quotes and comments."""
    statements = []
    buffer = []
    quote_char = None
    i = 0
    length = len(source)
    while i < length:
        char = source[i]
        nxt = source[i + 1] if i + 1 < length else ""

        if quote_char:
            buffer.append(char)
            if char == "\\" and nxt:
                buffer.append(nxt)
                i += 2
                continue
            if char == quote_char:
                quote_char = None
            i += 1
            continue

        if char in ("'", '"', "`"):
            quote_char = char
            buffer.append(char)
            i += 1
            continue

        if char == "-" and nxt == "-":
            while i < length and source[i] != "\n":
                i += 1
            continue

        if char == "#":
            while i < length and source[i] != "\n":
                i += 1
            continue

        if char == ";":
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
            i += 1
            continue

        buffer.append(char)
        i += 1

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


def _ensure_database(url):
    """Create the database only when it does not exist. Returns True if created."""
    database_name = url.database
    if not database_name or not _IDENTIFIER.fullmatch(database_name):
        raise RuntimeError("The configured database name is missing or invalid.")

    server_url = URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        query=url.query,
    )
    server_engine = create_engine(server_url, **Config.SQLALCHEMY_ENGINE_OPTIONS)
    try:
        with server_engine.begin() as connection:
            exists = connection.execute(
                text(
                    "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                    "WHERE SCHEMA_NAME = :name"
                ),
                {"name": database_name},
            ).scalar()
            if exists:
                return False
            connection.execute(
                text(
                    f"CREATE DATABASE `{database_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
            return True
    finally:
        server_engine.dispose()


def _load_models():
    from app import db

    import app.models  # noqa: F401  (registers every table on db.metadata)

    return db


def _foreign_keys(engine, table_names):
    inspector = inspect(engine)
    rows = []
    for table in sorted(table_names):
        try:
            fks = inspector.get_foreign_keys(table)
        except SQLAlchemyError:
            fks = []
        for fk in fks:
            rows.append(
                (
                    table,
                    tuple(fk.get("constrained_columns") or ()),
                    fk.get("referred_table"),
                    tuple(fk.get("referred_columns") or ()),
                )
            )
    return rows


def _apply_seed(engine):
    if not SEED_FILE.exists():
        return 0, "seed.sql not found"
    statements = _split_sql(SEED_FILE.read_text(encoding="utf-8"))
    applied = 0
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
            applied += 1
    return applied, "ok"


def main():
    parser = argparse.ArgumentParser(description="OneGov PH safe database migration")
    parser.add_argument("--seed", action="store_true", help="load database/seed.sql")
    parser.add_argument("--check", action="store_true", help="verify only; do not create tables")
    args = parser.parse_args()

    url = make_url(Config.SQLALCHEMY_DATABASE_URI)
    database_name = url.database

    print("OneGov PH database migration")
    print(f"  Target URI : {_safe_uri()}")

    try:
        created_database = _ensure_database(url)
    except (RuntimeError, SQLAlchemyError) as exc:
        print(f"  FAILED: could not verify/create database: {exc}")
        return 1

    print(f"  Database   : {database_name} ({'created' if created_database else 'exists'})")

    db = _load_models()
    expected = set(db.metadata.tables.keys())
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, **Config.SQLALCHEMY_ENGINE_OPTIONS)

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("  Connection : OK")

        before = set(inspect(engine).get_table_names())
        print(f"  Existing   : {len(before)} table(s)")

        if args.check:
            created = []
        else:
            db.metadata.create_all(bind=engine, checkfirst=True)
            created = sorted(set(inspect(engine).get_table_names()) - before)

        after = set(inspect(engine).get_table_names())

        if args.seed:
            applied, note = _apply_seed(engine)
            if note == "ok":
                print(f"  Seed       : applied {applied} statement(s) (idempotent)")
            else:
                print(f"  Seed       : skipped ({note})")

        missing = sorted(expected - after)
        extra = sorted(after - expected)
        fks = _foreign_keys(engine, after)
        fk_tables = {row[0] for row in fks}

        print("")
        print("Migration summary")
        print(f"  Tables now      : {len(after)}")
        print(f"  Missing tables  : {', '.join(missing) if missing else 'none'}")
        if created:
            print(f"  Created tables  : {', '.join(created)}")
        else:
            print("  Created tables  : none (already present or --check)")
        if extra:
            print(f"  Unmanaged tables: {', '.join(extra)}")

        if fks:
            print(f"  Foreign keys    : {len(fks)} across {len(fk_tables)} table(s)")
            for table, cols, ref_table, ref_cols in fks:
                print(
                    f"    - {table}{list(cols)} -> {ref_table}{list(ref_cols)}"
                )
        else:
            print("  Foreign keys    : none reported by the driver")

        if args.seed:
            with engine.connect() as connection:
                try:
                    departments = connection.execute(text("SELECT COUNT(*) FROM departments")).scalar()
                    services = connection.execute(text("SELECT COUNT(*) FROM services")).scalar()
                    print(f"  Reference rows  : departments={departments}, services={services}")
                except SQLAlchemyError:
                    pass

        if missing:
            print("")
            print("  RESULT: FAILED - some expected tables are still missing.")
            return 1

        print("")
        print("  RESULT: OK - schema is ready. No existing data was modified.")
        return 0
    except SQLAlchemyError as exc:
        print(f"  FAILED: {exc}")
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
