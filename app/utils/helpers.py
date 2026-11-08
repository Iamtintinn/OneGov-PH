import hmac
import secrets

from flask import abort, request, session
from flask_login import login_user

from app.models.user import User


def generate_csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def validate_csrf():
    sent = request.form.get("csrf_token", "")
    stored = session.get("_csrf_token", "")
    if not stored or not sent or not hmac.compare_digest(stored, sent):
        abort(400, description="The form expired. Refresh the page and submit it again.")


def home_endpoint_for_role(role):
    if role == User.ROLE_CITIZEN:
        return "citizen.dashboard"
    if role in (User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR):
        return "admin.department_dashboard"
    if role == User.ROLE_SYSTEM_ADMIN:
        return "admin.dashboard"
    return "auth.login"


def establish_session(user):
    """Replace the anonymous browser session before storing the signed-in account."""
    session.clear()
    session.permanent = True
    login_user(user)
