from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.models.application import Application
from app.models.department import Department
from app.models.service import Service
from app.utils.helpers import home_endpoint_for_role

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for(home_endpoint_for_role(current_user.role)))

    tracking_number = (request.args.get("tracking") or "").strip().upper()
    tracking_result = None
    tracking_error = None
    if tracking_number:
        app_row = db.session.scalar(
            db.select(Application)
            .where(Application.tracking_number == tracking_number)
            .order_by(Application.application_id.desc())
        )
        if app_row and app_row.application_status != "draft":
            tracking_result = {
                "tracking_number": app_row.tracking_number,
                "status": (app_row.application_status or "").replace("_", " ").title(),
                "service": app_row.service.service_name if app_row.service else "Government service",
                "updated": app_row.last_updated.strftime("%d %b %Y") if app_row.last_updated else "—",
            }
        else:
            tracking_error = "No application found for that reference number. Please check the number and try again."

    services = db.session.scalars(
        db.select(Service)
        .join(Department, Service.department_id == Department.department_id)
        .where(Service.service_status == "active", Department.department_status == "active")
        .order_by(Service.service_name.asc())
    ).all()

    return render_template(
        "public/landing.html",
        tracking_number=tracking_number,
        tracking_result=tracking_result,
        tracking_error=tracking_error,
        services=services,
    )
