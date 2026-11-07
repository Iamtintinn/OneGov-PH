from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from config import Config
from database.init_db import initialize_database

BASE_DIR = Path(__file__).resolve().parent

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    application = Flask(
        "onegov_ph",
        template_folder=str(BASE_DIR / "app" / "templates"),
        static_folder=str(BASE_DIR / "app" / "static"),
    )
    application.config.from_object(Config)

    db.init_app(application)
    login_manager.init_app(application)

    try:
        status_message = initialize_database()
    except RuntimeError as exc:
        application.logger.error("%s", exc)
        raise

    application.logger.info(status_message)
    print(status_message)

    _check_database_connection(application)
    return application


def _check_database_connection(application):
    """Confirm MySQL is reachable without creating or changing tables."""
    with application.app_context():
        try:
            with db.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            application.logger.info("Connected to the OneGov PH database.")
        except SQLAlchemyError as exc:
            application.logger.error("Database connection failed: %s", exc)
            raise RuntimeError(
                "Could not connect to the OneGov PH MySQL database. "
                "Start MySQL in XAMPP and confirm the onegov_ph database is available."
            ) from exc


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
