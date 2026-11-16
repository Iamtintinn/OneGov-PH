from functools import wraps

from flask import abort
from flask_login import current_user, login_required

from app.models.user import User


def role_required(*roles):
    """Allow only a signed-in website account whose role is in the given list."""

    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403, description="You do not have access to this page.")
            return view(*args, **kwargs)

        return wrapped

    return decorator


def citizen_portal_required(view):
    """Allow citizens and system administrators to use their own citizen portal."""
    return role_required(User.ROLE_CITIZEN, User.ROLE_SYSTEM_ADMIN)(view)
