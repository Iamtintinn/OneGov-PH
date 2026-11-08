from flask import Blueprint, render_template

from app.models.user import User
from app.utils.decorators import role_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/dashboard")
@role_required(User.ROLE_SYSTEM_ADMIN)
def dashboard():
    return render_template(
        "admin/dashboard.html",
        page_title="System administration",
        page_text="This section of the website is limited to system administrators.",
    )


@admin_bp.route("/department/dashboard")
@role_required(User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR)
def department_dashboard():
    return render_template(
        "admin/dashboard.html",
        page_title="Department workspace",
        page_text="Department pages stay limited to staff and supervisors of the assigned office.",
    )
