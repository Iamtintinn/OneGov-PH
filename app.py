from pathlib import Path

from flask import Flask, render_template, request
from flask_login import LoginManager
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import db
from config import Config
from database.init_db import initialize_database

BASE_DIR = Path(__file__).resolve().parent

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to continue."
login_manager.login_message_category = "warning"
login_manager.session_protection = "basic"


def create_app():
    application = Flask(
        "onegov_ph",
        template_folder=str(BASE_DIR / "app" / "templates"),
        static_folder=str(BASE_DIR / "app" / "static"),
    )
    application.config.from_object(Config)

    db.init_app(application)
    login_manager.init_app(application)

    from app.models import User
    from app.routes import register_blueprints
    from app.utils.helpers import generate_csrf_token, validate_csrf

    @login_manager.user_loader
    def load_user(user_id):
        if user_id is None or not str(user_id).isdigit():
            return None
        account = db.session.get(User, int(user_id))
        if account is None or account.account_status != "active":
            return None
        return account

    @application.before_request
    def protect_post_requests():
        if request.method == "POST":
            validate_csrf()

    @application.context_processor
    def inject_csrf():
        return {"csrf_token": generate_csrf_token}

    @application.errorhandler(400)
    def bad_request(error):
        return render_template("errors/400.html", message=error.description), 400

    @application.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html", message=error.description), 403

    register_blueprints(application)

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
    # Port 5000 is taken on macOS by AirPlay Receiver (Control Center).
    # Browsers that open it get HTTP 403: "Access to localhost was denied".
    app.run(debug=True, host="127.0.0.1", port=5001)
