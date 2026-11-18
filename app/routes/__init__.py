from app.routes.admin import admin_bp
from app.routes.auth import auth_bp
from app.routes.citizen import citizen_bp
from app.routes.admin_portal import admin_portal_bp
from app.routes.routing import routing_bp
from app.routes.webhooks import webhooks_bp


def register_blueprints(application):
    application.register_blueprint(auth_bp)
    application.register_blueprint(citizen_bp)
    application.register_blueprint(admin_bp)
    application.register_blueprint(admin_portal_bp)
    application.register_blueprint(routing_bp)
    application.register_blueprint(webhooks_bp)
