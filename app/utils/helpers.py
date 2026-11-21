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
    if role == User.ROLE_DEPARTMENT_SUPERVISOR:
        return "admin.dashboard"
    if role == User.ROLE_DEPARTMENT_STAFF:
        return "admin.department_dashboard"
    if role == User.ROLE_SYSTEM_ADMIN:
        return "admin.dashboard"
    return "auth.login"


def _record_user_session(user):
    try:
        from app import db
        from app.models.user_session import UserSession
        from app.services.citizen_settings_service import record_login_activity
        ua = (request.user_agent.string or "")[:500]
        ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "")[:64]
        sid = session.get("_id") or session.get("_user_id") or ""
        rec = UserSession(user_id=user.user_id, session_token=str(sid)[:255], ip_address=ip, user_agent=ua)
        db.session.add(rec)
        record_login_activity(user, "login", f"Signed in from {ip or 'unknown IP'}.")
        db.session.commit()
    except Exception:
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass


def establish_session(user):
    """Replace the anonymous browser session before storing the signed-in account."""
    session.clear()
    session.permanent = True
    login_user(user)
    _record_user_session(user)
