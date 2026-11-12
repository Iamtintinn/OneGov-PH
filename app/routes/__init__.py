from app.routes.admin import admin_bp
from app.routes.auth import auth_bp
from app.routes.citizen import citizen_bp
from app.routes.webhooks import webhooks_bp


def register_blueprints(application):
    application.register_blueprint(auth_bp)
    application.register_blueprint(citizen_bp)
    application.register_blueprint(admin_bp)
    application.register_blueprint(webhooks_bp)
