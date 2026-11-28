import re
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Config

_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def initialize_database():
    """Create the configured database when it is missing.

    Existing databases and tables are left unchanged. Application tables
    are not created.
    """
    url = make_url(Config.SQLALCHEMY_DATABASE_URI)
    database_name = url.database

    if not database_name or not _IDENTIFIER.fullmatch(database_name):
        raise RuntimeError(
            "The configured database name is missing or invalid. "
            "Check SQLALCHEMY_DATABASE_URI in config.py."
        )

    server_url = URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        query=url.query,
    )
    server_engine = create_engine(server_url)

    try:
        with server_engine.begin() as connection:
            existing = connection.execute(
                text(
                    "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                    "WHERE SCHEMA_NAME = :name"
                ),
                {"name": database_name},
            ).scalar()

            if existing:
                return (
                    f"Database '{database_name}' already exists. "
                    "No changes were made."
                )

            connection.execute(
                text(
                    f"CREATE DATABASE `{database_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Database initialization failed. Start MySQL in XAMPP and "
            "check the connection settings in config.py. "
            f"Details: {exc}"
        ) from exc
    finally:
        server_engine.dispose()

    return (
        f"Database '{database_name}' was created with character set "
        "utf8mb4 and collation utf8mb4_unicode_ci."
    )


if __name__ == "__main__":
    try:
        print(initialize_database())
    except RuntimeError as exc:
        print(exc)
        sys.exit(1)
