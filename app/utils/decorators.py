from functools import wraps

from flask import abort
from flask_login import current_user, login_required

from app.models.user import User
from app.utils.access import is_department_admin, is_system_admin
from app.utils.portal import in_admin_portal


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


def admin_console_required(view):
    """Allow system administrators and department administrators in the unified console."""

    @login_required
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not (is_system_admin() or is_department_admin()):
            abort(403, description="You do not have access to the admin console.")
        return view(*args, **kwargs)

    return wrapped


def citizen_portal_required(view):
    """Allow citizens and administrators to use the portal views available to them."""

    @login_required
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user.role in {User.ROLE_CITIZEN, User.ROLE_SYSTEM_ADMIN}:
            return view(*args, **kwargs)
        if is_department_admin() and in_admin_portal():
            return view(*args, **kwargs)
        abort(403, description="You do not have access to this page.")

    return wrapped
