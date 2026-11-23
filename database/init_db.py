"""Create the configured database and any missing application tables.

This module is intentionally non-destructive:
  * It never drops, truncates, or deletes tables or rows.
  * Existing tables and data are left untouched.
  * ``create_all`` only adds tables that are missing, so it is safe to run on
    every Flask start and safe to run repeatedly.
"""

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

_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def _server_engine(url):
    """Engine without a selected database, used only to create the database."""
    server_url = URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        query=url.query,
    )
    return create_engine(server_url, **Config.SQLALCHEMY_ENGINE_OPTIONS)


def _database_exists(connection, database_name):
    return bool(
        connection.execute(
            text(
                "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                "WHERE SCHEMA_NAME = :name"
            ),
            {"name": database_name},
        ).scalar()
    )


def initialize_database():
    """Ensure the configured database and application tables exist.

    Existing databases, tables, and records are never modified or removed.
    """
    url = make_url(Config.SQLALCHEMY_DATABASE_URI)
    database_name = url.database

    if not database_name or not _IDENTIFIER.fullmatch(database_name):
        raise RuntimeError(
            "The configured database name is missing or invalid. "
            "Check SQLALCHEMY_DATABASE_URI / DB_NAME in your .env file."
        )

    created_database = False
    server_engine = _server_engine(url)

    try:
        with server_engine.begin() as connection:
            if not _database_exists(connection, database_name):
                connection.execute(
                    text(
                        f"CREATE DATABASE `{database_name}` "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                )
                created_database = True
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Database initialization failed. Confirm MySQL/TiDB is reachable and "
            "check the database settings in your .env file. "
            f"Details: {exc}"
        ) from exc
    finally:
        server_engine.dispose()

    # Register every model with db.metadata before creating tables.
    from app import db

    import app.models  # noqa: F401  (import registers all mapped tables)

    target_engine = create_engine(
        Config.SQLALCHEMY_DATABASE_URI,
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
    )
    try:
        before = set(inspect(target_engine).get_table_names())
        expected = set(db.metadata.tables.keys())

        db.metadata.create_all(bind=target_engine, checkfirst=True)

        after = set(inspect(target_engine).get_table_names())
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Could not create the application tables. "
            "Confirm the database user can create tables in "
            f"'{database_name}'. Details: {exc}"
        ) from exc
    finally:
        target_engine.dispose()

    created_tables = sorted(after - before)
    still_missing = sorted(expected - after)
    database_note = (
        f"Database '{database_name}' was created."
        if created_database
        else f"Database '{database_name}' already exists."
    )
    if created_tables:
        table_note = "Created tables: " + ", ".join(created_tables) + "."
    else:
        table_note = "All expected application tables already exist."
    if still_missing:
        table_note += " Missing tables: " + ", ".join(still_missing) + "."

    return f"{database_note} {table_note}"


if __name__ == "__main__":
    try:
        print(initialize_database())
    except RuntimeError as exc:
        print(exc)
        sys.exit(1)
