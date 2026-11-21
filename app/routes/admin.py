import re
import secrets
import string
from datetime import datetime, time, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app import db
from app.models.application import (
    APPLICATION_STATUSES,
    Application,
    ApplicationEvent,
    ApplicationRequirement,
)
from app.models.department import Department
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.service import Service
from app.models.user import AccountActivityLog, User
from app.services.application_service import absolute_upload, field_map
from app.utils.access import (
    is_department_admin,
    is_system_admin,
    managed_account_query,
    visible_application_query,
    visible_payment_query,
    visible_service_query,
)
from app.utils.decorators import admin_console_required, role_required
from app.services.audit_service import log_activity
from app.services.application_service import read_details, write_details
from app.utils.validators import (
    clean_text,
    normalize_contact_number,
    normalize_email,
    validate_name,
    validate_new_password,
)

admin_bp = Blueprint("admin", __name__)


@admin_bp.context_processor
def admin_navigation():
    from app.routes.citizen import portal_navigation_context

    return portal_navigation_context()

PENDING_STATUSES = ("submitted", "under_review", "pending_documents", "for_payment")
ACCOUNT_STATUSES = ("active", "inactive", "suspended")
CREATION_ROLES = (
    (User.ROLE_CITIZEN, "Citizen"),
    (User.ROLE_DEPARTMENT_ADMIN, "Department Administrator"),
    (User.ROLE_SYSTEM_ADMIN, "System Admin"),
)
CREATION_ROLE_LABELS = dict(CREATION_ROLES)
DEPARTMENT_ADMIN_PERMISSIONS = ("applications.review", "services.manage")
DEPARTMENT_ADMIN_DEPARTMENTS = User.DEPARTMENT_ADMIN_DEPARTMENTS
PERMISSION_OPTIONS = (
    ("applications.review", "Review applications"),
    ("services.manage", "Manage government services"),
)
STATUS_LABELS = {
    "draft": "Draft",
    "submitted": "Submitted",
    "under_review": "Under review",
    "pending_documents": "Corrections requested",
    "for_payment": "For payment",
    "paid": "Paid",
    "scheduled": "Scheduled",
    "processing": "Processing",
    "ready_for_release": "Ready for release",
    "completed": "Completed",
    "rejected": "Rejected",
    "cancelled": "Cancelled",
    "approved": "Approved",
    "for_biometrics": "For biometrics",
    "with_hit": "With hit",
}


def _record_account_activity(target, action, description):
    db.session.add(
        AccountActivityLog(
            target_user_id=target.user_id,
            actor_user_id=current_user.user_id,
            action=action,
            description=description[:500],
        )
    )
    try:
        log_activity(
            activity_type=str(action).replace("_"," ").title(),
            module="Accounts",
            description=description[:600],
            record_id=target.user_id,
            status="Success",
            department_id=getattr(target, "department_id", None),
        )
    except Exception:
        pass


def _log_application_event(application, previous_status, description):
    now = datetime.now().replace(microsecond=0)
    db.session.add(
        ApplicationEvent(
            application_id=application.application_id,
            previous_status=previous_status,
            new_status=application.application_status,
            update_description=description[:500],
            updated_by=current_user.user_id,
            recorded_at=now,
        )
    )
    db.session.add(
        Notification(
            user_id=application.applicant_id,
            notification_title="Application updated",
            notification_message=f"{application.tracking_number}: {description[:500]}",
            notification_type="application",
            read_status="unread",
            created_date=now,
        )
    )
    application.last_updated = now


def _require_permission(permission):
    if is_system_admin() or is_department_admin():
        return
    if (
        current_user.role != User.ROLE_DEPARTMENT_STAFF
        or permission not in set(current_user.admin_permissions or ())
        or not current_user.department_id
    ):
        abort(403)


def _is_archived_application(application):
    try:
        details = application.application_details or {}
        if isinstance(details, str):
            import json as _json; details = _json.loads(details)
        return bool((details or {}).get("archived"))
    except Exception:
        return False


def _application_query_for_current_admin():
    query = db.select(Application).options(
        joinedload(Application.service),
        joinedload(Application.department),
        joinedload(Application.requirements),
        joinedload(Application.payments),
    )
    if not is_system_admin():
        _require_permission("applications.review")
    return visible_application_query(query)


def _application_or_404(application_id):
    application = db.session.execute(
        _application_query_for_current_admin().where(Application.application_id == application_id)
    ).unique().scalar_one_or_none()
    if application is None:
        abort(404)
    return application


def _account_form_from_request(allow_admin_fields=True):
    first_name, first_error = validate_name(request.form.get("first_name"), "First name")
    middle_name, middle_error = validate_name(
        request.form.get("middle_name"), "Middle name", required=False
    )
    last_name, last_error = validate_name(request.form.get("last_name"), "Last name")
    email = normalize_email(request.form.get("email"))
    contact = normalize_contact_number(request.form.get("contact_number"))
    address = clean_text(request.form.get("address"))
    role = clean_text(request.form.get("role"))
    status = clean_text(request.form.get("account_status"))
    department_raw = clean_text(request.form.get("department_id"))
    permission_values = request.form.getlist("permissions")

    errors = {
        key: message
        for key, message in (
            ("first_name", first_error),
            ("middle_name", middle_error),
            ("last_name", last_error),
        )
        if message
    }
    if not email or len(email) > 255 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        errors["email"] = "Enter a valid email address."
    if contact and (not contact.lstrip("+").isdigit() or not 10 <= len(contact.lstrip("+")) <= 15):
        errors["contact_number"] = "Enter a valid contact number."
    if len(address) > 500:
        errors["address"] = "Use no more than 500 characters."
    if not allow_admin_fields:
        role = User.ROLE_CITIZEN
        department_raw = ""
        permission_values = []
    elif role not in User.ROLES:
        errors["role"] = "Choose a valid account role."
    if status not in ACCOUNT_STATUSES:
        errors["account_status"] = "Choose a valid account status."
    if any(value not in {key for key, _label in PERMISSION_OPTIONS} for value in permission_values):
        errors["permissions"] = "Choose valid permissions."

    department_id = None
    if department_raw:
        if not department_raw.isdigit():
            errors["department_id"] = "Choose a valid department."
        else:
            department_id = int(department_raw)
            department = db.session.get(Department, department_id)
            if department is None or department.department_status != "active":
                errors["department_id"] = "Choose an existing department."
    if role in {User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR} and department_id is None:
        errors["department_id"] = "Assign department staff to a department."
    if role not in {User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR}:
        department_id = None
        permission_values = []

    return {
        "first_name": first_name or "",
        "middle_name": middle_name or "",
        "last_name": last_name or "",
        "email": email,
        "contact_number": contact,
        "address": address,
        "role": role,
        "account_status": status,
        "department_id": department_id,
        "admin_permissions": sorted(set(permission_values)),
    }, errors


def _generate_temporary_password():
    alphabet = string.ascii_letters + string.digits + "!@#%"
    characters = [
        secrets.choice(string.ascii_letters),
        secrets.choice(string.digits),
        secrets.choice("!@#%"),
    ]
    characters.extend(secrets.choice(alphabet) for _ in range(21))
    secrets.SystemRandom().shuffle(characters)
    return "".join(characters)


def _creation_form_values():
    return {
        "first_name": "",
        "middle_name": "",
        "last_name": "",
        "email": "",
        "contact_number": "",
        "address": "",
        "role": User.ROLE_CITIZEN,
        "department_id": "",
        "password_mode": "generate",
        "confirm_create": "",
    }


def _creation_form_from_request(department_ids, allowed_roles=CREATION_ROLES):
    first_name, first_error = validate_name(request.form.get("first_name"), "First name")
    middle_name, middle_error = validate_name(
        request.form.get("middle_name"), "Middle name", required=False
    )
    last_name, last_error = validate_name(request.form.get("last_name"), "Last name")
    email = normalize_email(request.form.get("email"))
    contact_number = normalize_contact_number(request.form.get("contact_number"))
    address = clean_text(request.form.get("address"))
    role = clean_text(request.form.get("role"))
    department_raw = clean_text(request.form.get("department_id"))
    password_mode = clean_text(request.form.get("password_mode"))
    custom_password = request.form.get("password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    errors = {
        key: message
        for key, message in (
            ("first_name", first_error),
            ("middle_name", middle_error),
            ("last_name", last_error),
        )
        if message
    }
    if not email or len(email) > 255 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        errors["email"] = "Enter a valid email address."
    if not contact_number:
        errors["contact_number"] = "Contact number is required."
    elif not 10 <= len(contact_number.lstrip("+")) <= 15:
        errors["contact_number"] = "Enter a valid contact number."
    if len(address) > 500:
        errors["address"] = "Use no more than 500 characters."
    if role not in dict(allowed_roles):
        errors["role"] = "Choose a valid account role."

    department_id = None
    if role == User.ROLE_DEPARTMENT_ADMIN:
        if not department_raw.isdigit() or int(department_raw) not in department_ids:
            errors["department_id"] = "Choose an active department."
        else:
            department_id = int(department_raw)

    if password_mode not in {"generate", "custom"}:
        errors["password_mode"] = "Choose how the temporary password will be set."
    elif password_mode == "custom":
        errors.update(validate_new_password(custom_password, confirm_password))

    if clean_text(request.form.get("confirm_create")).lower() not in {"yes", "on", "true", "1"}:
        errors["confirm_create"] = "Confirm that you want to create this account."

    return {
        "first_name": first_name or "",
        "middle_name": middle_name or "",
        "last_name": last_name or "",
        "email": email,
        "contact_number": contact_number,
        "address": address,
        "role": role,
        "department_id": department_raw,
        "password_mode": password_mode,
        "temporary_password": custom_password if password_mode == "custom" else "",
        "department": department_id,
    }, errors


def _record_account_form(user, form, action):
    required_password_change = user.must_change_password
    user.set_name(form["first_name"], form["last_name"], form["middle_name"])
    user.email = form["email"]
    user.contact_number = form["contact_number"] or None
    user.address = form["address"] or None
    user.role = form["role"]
    user.account_status = form["account_status"]
    user.department_id = form["department_id"]
    user.admin_permissions = form["admin_permissions"]
    if required_password_change:
        user.require_password_change()
    _record_account_activity(
        user,
        action,
        f"Account profile updated by {current_user.full_name}; role {user.role}, status {user.account_status}.",
    )


def _account_form_values(user=None):
    permissions = list(user.admin_permissions or ()) if user else []
    permissions = [value for value in permissions if value != User.TEMPORARY_PASSWORD_FLAG]
    return {
        "first_name": user.first_name if user else "",
        "middle_name": user.middle_name if user else "",
        "last_name": user.last_name if user else "",
        "email": user.email if user else "",
        "contact_number": user.contact_number if user else "",
        "address": user.address if user else "",
        "role": user.role if user else User.ROLE_DEPARTMENT_STAFF,
        "account_status": user.account_status if user else "active",
        "department_id": str(user.department_id or "") if user else "",
        "permissions": permissions,
    }


@admin_bp.route("/admin/dashboard")
@admin_console_required
def dashboard():
    now = datetime.now()
    start = datetime.combine(now.date() - timedelta(days=6), time.min)
    weekly_rows = db.session.execute(
        visible_application_query(
            db.select(func.date(Application.submission_date), func.count(Application.application_id))
            .where(Application.submission_date >= start, Application.application_status != "draft")
            .group_by(func.date(Application.submission_date))
        )
    ).all()
    weekly_counts = {str(day): count for day, count in weekly_rows}
    weekly_activity = [
        {
            "label": (now.date() - timedelta(days=offset)).strftime("%a"),
            "date": now.date() - timedelta(days=offset),
            "count": weekly_counts.get((now.date() - timedelta(days=offset)).isoformat(), 0),
        }
        for offset in range(6, -1, -1)
    ]
    max_daily = max((item["count"] for item in weekly_activity), default=0) or 1

    recent_events = db.session.scalars(
        visible_application_query(
            db.select(ApplicationEvent)
            .join(Application, ApplicationEvent.application_id == Application.application_id)
            .options(joinedload(ApplicationEvent.application).joinedload(Application.service))
            .order_by(ApplicationEvent.recorded_at.desc(), ApplicationEvent.tracking_id.desc())
            .limit(8)
        )
    ).unique().all()
    activity_user_ids = {event.updated_by for event in recent_events if event.updated_by}
    activity_users = (
        {
            user.user_id: user.full_name
            for user in db.session.scalars(
                db.select(User).where(User.user_id.in_(activity_user_ids))
            ).all()
        }
        if activity_user_ids
        else {}
    )
    service_rows = db.session.execute(
        visible_service_query(
            db.select(Service, func.count(Application.application_id))
            .outerjoin(Application, Application.service_id == Service.service_id)
            .group_by(Service.service_id)
            .order_by(Service.service_name)
        )
    ).all()
    return render_template(
        "admin/dashboard.html",
        page_title="Admin dashboard",
        total_citizens=db.session.scalar(
            managed_account_query(
                db.select(func.count(User.user_id)).where(User.role == User.ROLE_CITIZEN)
            )
        )
        or 0,
        total_services=db.session.scalar(
            visible_service_query(db.select(func.count(Service.service_id)))
        )
        or 0,
        total_applications=db.session.scalar(
            visible_application_query(db.select(func.count(Application.application_id)))
        )
        or 0,
        pending_applications=db.session.scalar(
            visible_application_query(
                db.select(func.count(Application.application_id)).where(
                    Application.application_status.in_(PENDING_STATUSES)
                )
            )
        )
        or 0,
        completed_applications=db.session.scalar(
            visible_application_query(
                db.select(func.count(Application.application_id)).where(
                    Application.application_status == "completed"
                )
            )
        )
        or 0,
        total_payments=db.session.scalar(
            visible_payment_query(db.select(func.count(Payment.payment_id)))
        )
        or 0,
        paid_amount=db.session.scalar(
            visible_payment_query(
                db.select(func.coalesce(func.sum(Payment.amount), 0)).where(
                    Payment.payment_status == "paid"
                )
            )
        )
        or 0,
        weekly_activity=weekly_activity,
        max_daily=max_daily,
        recent_events=recent_events,
        activity_users=activity_users,
        service_rows=service_rows,
        status_labels=STATUS_LABELS,
        current_date=now,
    )


@admin_bp.route("/admin/services")
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR)
def services():
    _require_permission("services.manage")
    search = clean_text(request.args.get("q"))[:80]
    query = (
        db.select(Service, func.count(Application.application_id))
        .outerjoin(Application, Application.service_id == Service.service_id)
        .group_by(Service.service_id)
        .order_by(Service.service_name)
    )
    query = visible_service_query(query)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Service.service_name.ilike(pattern),
                Service.description.ilike(pattern),
                Service.department.has(Department.department_name.ilike(pattern)),
            )
        )
    service_rows = db.session.execute(query).all()
    return render_template("admin/manage_services.html", service_rows=service_rows, search=search)


@admin_bp.route("/admin/services/<int:service_id>/status", methods=["POST"])
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR)
def service_status(service_id):
    _require_permission("services.manage")
    service = db.session.scalar(
        visible_service_query(db.select(Service).where(Service.service_id == service_id))
    )
    if service is None:
        abort(404)
    target_status = clean_text(request.form.get("service_status"))
    if target_status not in {"active", "inactive"}:
        abort(400, description="Choose a valid service status.")
    service.service_status = target_status
    db.session.commit()
    flash(f"{service.service_name} is now {target_status}.", "success")
    return redirect(url_for("admin.services"))




@admin_bp.route("/admin/applications/<int:application_id>/delete", methods=["POST"])
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_SUPERVISOR)
def delete_application(application_id):
    application = _application_or_404(application_id)
    details = application.application_details if isinstance(application.application_details, dict) else read_details(application)
    from datetime import datetime as _dt
    details["archived"] = {"archived_at": _dt.now().replace(microsecond=0).isoformat(), "archived_by": current_user.user_id, "previous_status": application.application_status}
    write_details(application, details, commit=False)
    try:
        log_activity(activity_type="Application Archived", module="Applications", description=f"Admin archived application {application.tracking_number}", record_id=application.tracking_number, previous_value={"status": application.application_status}, new_value={"archived": True}, status="Success", department_id=application.assigned_department_id)
    except Exception:
        pass
    db.session.commit()
    flash(f"Application {application.tracking_number} was moved to Archive.", "success")
    next_url = request.referrer
    if next_url and "/admin/" in next_url:
        return redirect(next_url)
    return redirect(url_for("admin.applications"))


@admin_bp.route("/admin/applications/<int:application_id>/delete-permanent", methods=["POST"])
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_SUPERVISOR)
def delete_application_permanent(application_id):
    application = _application_or_404(application_id)
    details = application.application_details if isinstance(application.application_details, dict) else read_details(application)
    if not details.get("archived"):
        flash("Only archived applications can be permanently deleted.", "warning")
        return redirect(request.referrer or url_for("admin.archive"))
    tracking = application.tracking_number
    dept_id = application.assigned_department_id
    for table in ["application_tracking", "application_requirements", "payments"]:
        try:
            db.session.execute(db.text(f"DELETE FROM {table} WHERE application_id=:id"), {"id": application_id})
        except Exception:
            db.session.rollback()
    try:
        log_activity(activity_type="Application Deleted Permanently", module="Applications", description=f"Admin permanently deleted application {tracking}", record_id=tracking, previous_value={"application_id": application_id}, status="Success", department_id=dept_id)
    except Exception:
        pass
    db.session.delete(application)
    db.session.commit()
    flash(f"Application {tracking} was permanently deleted.", "success")
    return redirect(request.referrer or url_for("admin.archive"))

@admin_bp.route("/admin/drafts")
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR)
def drafts():
    q = clean_text(request.args.get("q"))
    query = _application_query_for_current_admin().where(Application.application_status == "draft")
    if q:
        pattern = f"%{q}%"
        query = query.join(User, User.user_id == Application.applicant_id).where(or_(Application.tracking_number.ilike(pattern), User.full_name.ilike(pattern)))
    rows = [r for r in db.session.scalars(query.order_by(Application.last_updated.desc()).limit(200)).unique().all() if not _is_archived_application(r)]
    applicants = {u.user_id: u for u in db.session.scalars(db.select(User).where(User.user_id.in_({i.applicant_id for i in rows}))).all()} if rows else {}
    return render_template("admin/drafts.html", applications=rows, applicants=applicants, search=q or "", status_labels=STATUS_LABELS)


@admin_bp.route("/admin/archive")
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR)
def archive():
    q = clean_text(request.args.get("q"))
    status = clean_text(request.args.get("status"))
    query = _application_query_for_current_admin()
    if q:
        pattern = f"%{q}%"
        query = query.join(User, User.user_id == Application.applicant_id).where(or_(Application.tracking_number.ilike(pattern), User.full_name.ilike(pattern)))
    if status in APPLICATION_STATUSES:
        query = query.where(Application.application_status == status)
    rows = [r for r in db.session.scalars(query.order_by(Application.submission_date.desc()).limit(300)).unique().all() if _is_archived_application(r)]
    applicants = {u.user_id: u for u in db.session.scalars(db.select(User).where(User.user_id.in_({i.applicant_id for i in rows}))).all()} if rows else {}
    return render_template("admin/archive.html", applications=rows, applicants=applicants, search=q or "", selected_status=status, statuses=APPLICATION_STATUSES, status_labels=STATUS_LABELS)


@admin_bp.route("/admin/applications/<int:application_id>/archive", methods=["POST"])
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_SUPERVISOR)
def archive_application(application_id):
    application = _application_or_404(application_id)
    details = application.application_details if isinstance(application.application_details, dict) else read_details(application)
    from datetime import datetime as _dt
    details["archived"] = {"archived_at": _dt.now().replace(microsecond=0).isoformat(), "archived_by": current_user.user_id, "previous_status": application.application_status}
    write_details(application, details, commit=False)
    try:
        log_activity(activity_type="Application Archived", module="Applications", description=f"Admin archived application {application.tracking_number}", record_id=application.tracking_number, new_value={"archived": True}, status="Success", department_id=application.assigned_department_id)
    except Exception:
        pass
    db.session.commit()
    flash(f"Application {application.tracking_number} moved to Archive.", "success")
    return redirect(request.referrer or url_for("admin.applications"))


@admin_bp.route("/admin/applications/<int:application_id>/restore", methods=["POST"])
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_SUPERVISOR)
def restore_application(application_id):
    application = _application_or_404(application_id)
    details = application.application_details if isinstance(application.application_details, dict) else read_details(application)
    if details.get("archived"):
        details.pop("archived", None)
        write_details(application, details, commit=False)
        try:
            log_activity(activity_type="Application Restored", module="Applications", description=f"Admin restored application {application.tracking_number}", record_id=application.tracking_number, new_value={"archived": False}, status="Success", department_id=application.assigned_department_id)
        except Exception:
            pass
        db.session.commit()
        flash(f"Application {application.tracking_number} restored.", "success")
    return redirect(request.referrer or url_for("admin.archive"))
@admin_bp.route("/admin/applications")
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR)
def applications():
    query = _application_query_for_current_admin()
    search = clean_text(request.args.get("q"))
    status = clean_text(request.args.get("status"))
    service_raw = clean_text(request.args.get("service"))
    if search:
        pattern = f"%{search}%"
        query = query.join(User, User.user_id == Application.applicant_id).where(
            or_(Application.tracking_number.ilike(pattern), User.full_name.ilike(pattern))
        )
    if status in APPLICATION_STATUSES:
        query = query.where(Application.application_status == status)
    else:
        query = query.where(Application.application_status != "draft")
    service_id = int(service_raw) if service_raw.isdigit() else None
    if service_id:
        query = query.where(Application.service_id == service_id)
    rows = [r for r in db.session.scalars(query.order_by(Application.submission_date.desc()).limit(200)).unique().all() if not _is_archived_application(r)]
    applicants = {
        user.user_id: user
        for user in db.session.scalars(
            db.select(User).where(User.user_id.in_({item.applicant_id for item in rows}))
        ).all()
    } if rows else {}
    from app.routes.admin_portal import tracking_detail_data

    row_statuses = {}
    for item in rows:
        delivery = tracking_detail_data(
            item, applicants.get(item.applicant_id), include_map=False
        )["delivery"]
        if delivery["status"]:
            row_statuses[item.application_id] = {
                "label": delivery["label"],
                "status": delivery["status"],
                "courier_name": delivery["courier_name"],
            }
    return render_template(
        "admin/manage_applications.html",
        applications=rows,
        applicants=applicants,
        services=db.session.scalars(
            visible_service_query(db.select(Service).order_by(Service.service_name))
        ).all(),
        statuses=APPLICATION_STATUSES,
        status_labels=STATUS_LABELS,
        row_statuses=row_statuses,
        selected_status=status,
        selected_service=service_raw,
        search=search,
    )


@admin_bp.route("/admin/applications/<int:application_id>")
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR)
def application_detail(application_id):
    application = _application_or_404(application_id)
    applicant = db.session.get(User, application.applicant_id)
    events = db.session.scalars(
        db.select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application.application_id)
        .order_by(ApplicationEvent.recorded_at.desc(), ApplicationEvent.tracking_id.desc())
    ).all()
    actors = {
        user.user_id: user.full_name
        for user in db.session.scalars(
            db.select(User).where(
                User.user_id.in_({event.updated_by for event in events if event.updated_by})
            )
        ).all()
    } if events else {}
    from app.routes.admin_portal import (
        ADMIN_PROCESSING_STATUSES,
        DELIVERY_STATUSES,
        PASSPORT_PROCESSING_STATUSES,
        tracking_detail_data,
    )
    from app.services.application_forms import specification_for
    from app.services.passport_delivery import PICKUP
    from app.services.senior_admin import summary as senior_confirmation_summary

    tracking = tracking_detail_data(application, applicant)
    passport = tracking["passport_fulfillment"]
    senior_confirmation = senior_confirmation_summary(application)
    processing_statuses = ADMIN_PROCESSING_STATUSES
    spec_options = (tracking.get("spec") or {}).get("admin_status_options") if isinstance(tracking.get("spec"), dict) else None
    if not spec_options:
        spec_options = (specification_for(application.service, field_map(application)) or {}).get("admin_status_options")
    if spec_options:
        processing_statuses = tuple(
            (item.get("key"), item.get("label"), item.get("legacy_status"))
            for item in spec_options
            if item.get("key") and item.get("label") and item.get("legacy_status")
        ) or ADMIN_PROCESSING_STATUSES
    is_pickup = bool(
        (passport and passport["fulfillment_method"] == PICKUP)
        or (senior_confirmation and senior_confirmation["fulfillment_method"] == PICKUP)
        or (tracking["nbi_fulfillment"] and tracking["nbi_fulfillment"]["method"] == "pickup")
        or (tracking.get("philsys_fulfillment") and tracking["philsys_fulfillment"]["method"] == "pickup")
        or (tracking.get("sss_fulfillment") and tracking["sss_fulfillment"]["method"] == "pickup")
    )
    if is_pickup:
        processing_statuses = tuple(
            (
                key,
                "Ready for Pickup" if key == "ready_for_dispatch" else label,
                legacy,
            )
            for key, label, legacy in processing_statuses
        )
    if passport:
        processing_statuses = processing_statuses + tuple(
            item for item in PASSPORT_PROCESSING_STATUSES if item[0] != "rejected"
        )

    return render_template(
        "admin/application_detail.html",
        application=application,
        applicant=applicant,
        fields=field_map(application),
        events=events,
        actors=actors,
        statuses=APPLICATION_STATUSES,
        status_labels=STATUS_LABELS,
        tracking=tracking,
        processing_statuses=processing_statuses,
        delivery_statuses=DELIVERY_STATUSES,
        senior_confirmation=senior_confirmation,
    )


@admin_bp.route("/admin/applications/<int:application_id>/physical-requirements", methods=["POST"])
@admin_console_required
def confirm_physical_requirements(application_id):
    application = _application_or_404(application_id)
    from app.services.passport_admin import confirm, is_confirmed, is_passport_application

    if not is_passport_application(application):
        abort(400, description="Physical requirements are only confirmed for passport applications.")
    if is_confirmed(application):
        flash("Physical requirements are already confirmed for this application.", "info")
        return redirect(url_for("admin.application_detail", application_id=application_id))

    record = confirm(application, current_user)
    if record is None:
        flash("The applicant must choose pickup or home delivery before confirmation.", "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))

    description = "Confirmed submitted documents and completed physical requirements."
    if record.get("pickup_id"):
        description += f" Pickup ID {record['pickup_id']} is scheduled for {record['pickup_date_label']}."
    _log_application_event(application, application.application_status, description)
    db.session.commit()
    flash("Documents and physical requirements confirmed.", "success")
    return redirect(url_for("admin.application_detail", application_id=application_id))


@admin_bp.route("/admin/applications/<int:application_id>/senior-confirmation", methods=["POST"])
@admin_console_required
def confirm_senior_requirements(application_id):
    application = _application_or_404(application_id)
    from app.services.senior_admin import confirm, is_confirmed, is_senior_application

    if not is_senior_application(application):
        abort(400, description="Confirmation is only available for Senior Citizen ID applications.")
    if is_confirmed(application):
        flash("Documents and physical appearance are already confirmed for this application.", "info")
        return redirect(url_for("admin.application_detail", application_id=application_id))

    physical_appearance = request.form.get("physical_appearance") in {"1", "on", "true", "yes"}
    remarks = clean_text(request.form.get("remarks"))
    record, error = confirm(application, current_user, physical_appearance, remarks)
    if error:
        flash(error, "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))

    description = "Confirmed submitted documents or completed physical appearance."
    if record.get("pickup_id"):
        description += f" Pickup ID {record['pickup_id']} is scheduled for {record['pickup_date_label']}."
    _log_application_event(application, application.application_status, description)
    db.session.commit()
    flash("Senior Citizen ID documents and physical appearance confirmed.", "success")
    return redirect(url_for("admin.application_detail", application_id=application_id))


@admin_bp.route("/admin/applications/<int:application_id>/nbi-requirements", methods=["POST"])
@admin_console_required
def confirm_nbi_requirements(application_id):
    application = _application_or_404(application_id)
    from app.services.nbi_admin import confirm, is_confirmed, is_nbi_application, schedule_recorded

    if not is_nbi_application(application):
        abort(400, description="Physical requirements are only confirmed for NBI applications.")
    if not schedule_recorded(application):
        flash("The applicant must have a recorded appointment schedule before confirmation.", "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))
    if is_confirmed(application):
        flash("Physical requirements are already confirmed for this application.", "info")
        return redirect(url_for("admin.application_detail", application_id=application_id))

    record, error = confirm(application, current_user)
    if error:
        flash(error, "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))

    description = "Confirmed submitted documents and completed physical requirements."
    if record.get("pickup_id"):
        description += f" Pickup ID {record['pickup_id']} is scheduled for {record['pickup_date_label']}."
    _log_application_event(application, application.application_status, description)
    db.session.commit()
    flash("NBI documents and physical requirements confirmed.", "success")
    return redirect(url_for("admin.application_detail", application_id=application_id))


@admin_bp.route("/admin/applications/<int:application_id>/philsys-requirements", methods=["POST"])
@admin_console_required
def confirm_philsys_requirements(application_id):
    application = _application_or_404(application_id)
    from app.services.philsys_admin import confirm, is_confirmed, is_philsys_application, schedule_recorded

    if not is_philsys_application(application):
        abort(400, description="Physical requirements are only confirmed for PhilSys applications.")
    if not schedule_recorded(application):
        flash("The applicant must have a recorded appointment schedule before confirmation.", "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))
    if is_confirmed(application):
        flash("Physical requirements are already confirmed for this application.", "info")
        return redirect(url_for("admin.application_detail", application_id=application_id))

    record, error = confirm(application, current_user)
    if error:
        flash(error, "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))

    description = "Confirmed submitted documents and completed physical requirements."
    if record.get("pickup_id"):
        description += f" Pickup ID {record['pickup_id']} is scheduled for {record['pickup_date_label']}."
    _log_application_event(application, application.application_status, description)
    db.session.commit()
    flash("PhilSys documents and physical requirements confirmed.", "success")
    return redirect(url_for("admin.application_detail", application_id=application_id))


@admin_bp.route("/admin/applications/<int:application_id>/sss-requirements", methods=["POST"])
@admin_console_required
def confirm_sss_requirements(application_id):
    application = _application_or_404(application_id)
    from app.services.sss_admin import confirm, is_confirmed, is_sss_application, schedule_recorded

    if not is_sss_application(application):
        abort(400, description="Physical requirements are only confirmed for SSS applications.")
    if not schedule_recorded(application):
        flash("The applicant must have a recorded appointment schedule before confirmation.", "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))
    if is_confirmed(application):
        flash("Physical requirements are already confirmed for this application.", "info")
        return redirect(url_for("admin.application_detail", application_id=application_id))

    record, error = confirm(application, current_user)
    if error:
        flash(error, "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))

    description = "Confirmed submitted documents and completed physical requirements."
    if record.get("pickup_id"):
        description += f" Pickup ID {record['pickup_id']} is scheduled for {record['pickup_date_label']}."
    _log_application_event(application, application.application_status, description)
    db.session.commit()
    flash("SSS documents and physical requirements confirmed.", "success")
    return redirect(url_for("admin.application_detail", application_id=application_id))


@admin_bp.route("/admin/applications/<int:application_id>/update", methods=["POST"])
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR)
def update_application(application_id):
    application = _application_or_404(application_id)
    target_key = clean_text(request.form.get("application_status"))
    remarks = clean_text(request.form.get("remarks"))
    from app.services.nbi_admin import gate_message as nbi_gate_message
    from app.services.passport_admin import (
        gate_message,
        is_passport_application,
        resolve_status_update,
    )
    from app.services.philsys_admin import gate_message as philsys_gate_message
    from app.services.senior_admin import (
        gate_message as senior_gate_message,
        is_senior_application,
        resolve_status_update as resolve_senior_status_update,
    )
    from app.services.sss_admin import gate_message as sss_gate_message

    passport_application = is_passport_application(application)
    senior_application = is_senior_application(application)
    target_status = target_key
    display_label = STATUS_LABELS.get(target_status, target_status)
    spec_status_key = ""
    if passport_application:
        passport_status, passport_label = resolve_status_update(application, target_key)
        if passport_status:
            spec_status_key = target_key
            target_status = passport_status
            display_label = passport_label
        elif target_key not in APPLICATION_STATUSES:
            abort(400, description="Choose a valid application status.")
    elif senior_application:
        senior_status, senior_label = resolve_senior_status_update(application, target_key)
        if senior_status:
            spec_status_key = target_key
            target_status = senior_status
            display_label = senior_label
        elif target_key not in APPLICATION_STATUSES:
            abort(400, description="Choose a valid application status.")
    if target_status not in APPLICATION_STATUSES or target_status == "draft":
        abort(400, description="Choose a valid application status.")
    if len(remarks) > 500:
        flash("Remarks must be 500 characters or fewer.", "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))
    if target_status in {"rejected", "pending_documents"} and not remarks:
        flash("Add a reason when rejecting an application or requesting corrections.", "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))

    confirmation_gate = (
        gate_message(application)
        or senior_gate_message(application)
        or nbi_gate_message(application)
        or philsys_gate_message(application)
        or sss_gate_message(application)
    )
    if confirmation_gate:
        flash(confirmation_gate, "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))

    previous_status = application.application_status
    application.application_status = target_status
    if spec_status_key:
        details = read_details(application)
        status_key_field = "passport_status_key" if passport_application else "senior_status_key"
        details[status_key_field] = spec_status_key
        write_details(application, details, commit=False)
    description = f"Status changed to {display_label}."
    if remarks:
        description += f" Remarks: {remarks}"
    _log_application_event(application, previous_status, description)
    try:
        log_activity(activity_type="Application Status Updated", module="Applications", description=f"{application.tracking_number}: {STATUS_LABELS.get(previous_status, previous_status)} -> {display_label}", record_id=application.tracking_number, previous_value={"status": STATUS_LABELS.get(previous_status, previous_status)}, new_value={"status": display_label, "remarks": remarks}, status="Success", department_id=application.assigned_department_id)
    except Exception:
        pass
    db.session.commit()
    flash("Application status and remarks were saved.", "success")
    return redirect(url_for("admin.application_detail", application_id=application_id))


@admin_bp.route(
    "/admin/applications/<int:application_id>/requirements/<int:requirement_id>",
    methods=["POST"],
)
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR)
def update_requirement(application_id, requirement_id):
    application = _application_or_404(application_id)
    requirement = next(
        (item for item in application.requirements if item.requirement_id == requirement_id),
        None,
    )
    if requirement is None:
        abort(404)
    verification_status = clean_text(request.form.get("verification_status"))
    remarks = clean_text(request.form.get("remarks"))
    if verification_status not in {"pending", "verified", "rejected"}:
        abort(400, description="Choose a valid document review status.")
    if len(remarks) > 500:
        flash("Document remarks must be 500 characters or fewer.", "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))
    if verification_status == "rejected" and not remarks:
        flash("Explain why the document was rejected.", "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))
    requirement.verification_status = verification_status
    requirement.remarks = remarks or requirement.remarks
    description = (
        f"Document “{requirement.requirement_name}” marked {verification_status}."
        + (f" Remarks: {remarks}" if remarks else "")
    )
    _log_application_event(application, application.application_status, description)
    db.session.commit()
    flash("Document review was saved.", "success")
    return redirect(url_for("admin.application_detail", application_id=application_id))


@admin_bp.route(
    "/admin/applications/<int:application_id>/requirements/<int:requirement_id>/file"
)
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR)
def application_document(application_id, requirement_id):
    application = _application_or_404(application_id)
    requirement = next(
        (item for item in application.requirements if item.requirement_id == requirement_id),
        None,
    )
    path = absolute_upload(requirement.uploaded_file) if requirement else None
    if path is None:
        abort(404)
    return send_file(path, as_attachment=False, download_name=requirement.remarks or path.name)


@admin_bp.route("/admin/accounts")
@admin_console_required
def accounts():
    query = managed_account_query(db.select(User).options(joinedload(User.department)))
    search = clean_text(request.args.get("q"))
    role = clean_text(request.args.get("role"))
    status = clean_text(request.args.get("status"))
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.contact_number.ilike(pattern),
            )
        )
    if role in User.ROLES:
        query = query.where(User.role == role)
    if status in ACCOUNT_STATUSES:
        query = query.where(User.account_status == status)
    users = db.session.scalars(query.order_by(User.date_registered.desc()).limit(300)).unique().all()
    return render_template(
        "admin/manage_users.html",
        users=users,
        roles=(User.ROLE_CITIZEN,) if is_department_admin() else User.ROLES,
        role_labels=User.ROLE_LABELS,
        account_statuses=ACCOUNT_STATUSES,
        selected_role=role if not is_department_admin() else "",
        selected_status=status,
        search=search,
    )


@admin_bp.route("/admin/account-creation", methods=["GET", "POST"])
@role_required(User.ROLE_SYSTEM_ADMIN)
def account_creation():
    creation_roles = CREATION_ROLES
    departments = db.session.scalars(
        db.select(Department)
        .where(
            Department.department_status == "active",
            Department.department_name.in_(DEPARTMENT_ADMIN_DEPARTMENTS),
        )
        .order_by(Department.department_name)
    ).all()
    department_ids = {department.department_id for department in departments}
    form = _creation_form_values()
    errors = {}
    temporary_password = None
    created_account = None
    if request.method == "POST":
        form, errors = _creation_form_from_request(department_ids, creation_roles)
        if not errors:
            duplicate = db.session.scalar(
                db.select(User.user_id).where(User.email == form["email"])
            )
            if duplicate is not None:
                errors["email"] = "An account with this email already exists."
        if not errors:
            temporary_password = form["temporary_password"] or _generate_temporary_password()
            account = User(
                email=form["email"],
                contact_number=form["contact_number"],
                address=form["address"] or None,
                role=form["role"],
                account_status="active",
                email_verification_status="unverified",
                department_id=form["department"],
            )
            account.set_name(form["first_name"], form["last_name"], form["middle_name"])
            account.set_password(temporary_password)
            account.require_password_change()
            if form["role"] == User.ROLE_DEPARTMENT_ADMIN:
                account.admin_permissions = {
                    permission: True for permission in DEPARTMENT_ADMIN_PERMISSIONS
                }
                account.require_password_change()
            db.session.add(account)
            try:
                db.session.flush()
                _record_account_activity(
                    account,
                    "account_created",
                    f"Account created by {current_user.full_name} with role {CREATION_ROLE_LABELS[account.role]}"
                    + (
                        f" for {account.department.department_name}."
                        if account.department
                        else "."
                    ),
                )
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                temporary_password = None
                errors["email"] = "An account with this email already exists."
            else:
                created_account = account
                flash("Account created. Share the credentials shown below securely.", "success")
                form = _creation_form_values()
    return render_template(
        "admin/account_creation.html",
        form=form,
        errors=errors,
        departments=departments,
        roles=creation_roles,
        role_labels=CREATION_ROLE_LABELS,
        temporary_password=temporary_password,
        created_account=created_account,
    )


@admin_bp.route("/admin/accounts/new", methods=["GET", "POST"])
@role_required(User.ROLE_SYSTEM_ADMIN)
def create_account():
    departments = db.session.scalars(
        db.select(Department).where(Department.department_status == "active").order_by(
            Department.department_name
        )
    ).all()
    form = _account_form_values()
    errors = {}
    temporary_password = None
    if request.method == "POST":
        form, errors = _account_form_from_request()
        if not errors:
            temporary_password = "".join(
                secrets.choice(string.ascii_letters + string.digits + "!@#%")
                for _ in range(24)
            )
            account = User(
                email=form["email"],
                contact_number=form["contact_number"] or None,
                address=form["address"] or None,
                role=form["role"],
                account_status=form["account_status"],
                email_verification_status="unverified",
                department_id=form["department_id"],
                admin_permissions=form["admin_permissions"],
            )
            account.set_name(form["first_name"], form["last_name"], form["middle_name"])
            account.set_password(temporary_password)
            account.require_password_change()
            db.session.add(account)
            try:
                db.session.flush()
                _record_account_activity(
                    account,
                    "account_created",
                    f"Account created by {current_user.full_name} with role {account.role}.",
                )
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                temporary_password = None
                errors["email"] = "An account with this email already exists."
            else:
                flash("Account created. Share the temporary password securely; it is shown only once.", "success")
    return render_template(
        "admin/account_form.html",
        heading="Create account",
        form=form,
        errors=errors,
        departments=departments,
        roles=User.ROLES,
        role_labels=User.ROLE_LABELS,
        account_statuses=ACCOUNT_STATUSES,
        permission_options=PERMISSION_OPTIONS,
        temporary_password=temporary_password,
        account=None,
    )


@admin_bp.route("/admin/accounts/<int:user_id>", methods=["GET", "POST"])
@admin_console_required
def account_detail(user_id):
    account = db.session.scalar(
        managed_account_query(
            db.select(User).options(joinedload(User.department)).where(User.user_id == user_id)
        )
    )
    if account is None:
        abort(404)
    departments = (
        db.session.scalars(
            db.select(Department).where(Department.department_status == "active").order_by(
                Department.department_name
            )
        ).all()
        if is_system_admin()
        else []
    )
    form = _account_form_values(account)
    errors = {}
    temporary_password = None
    if request.method == "POST":
        action = clean_text(request.form.get("action"))
        if action == "update":
            form, errors = _account_form_from_request(allow_admin_fields=is_system_admin())
            if not errors and account.user_id == current_user.user_id and (
                form["role"] != User.ROLE_SYSTEM_ADMIN or form["account_status"] != "active"
            ):
                errors["role"] = "You cannot disable or remove your own administrator access."
            if (
                not errors
                and account.role == User.ROLE_SYSTEM_ADMIN
                and account.account_status == "active"
                and (form["role"] != User.ROLE_SYSTEM_ADMIN or form["account_status"] != "active")
                and (db.session.scalar(
                    db.select(func.count(User.user_id)).where(
                        User.role == User.ROLE_SYSTEM_ADMIN,
                        User.account_status == "active",
                    )
                ) or 0) <= 1
            ):
                errors["role"] = "At least one active system administrator must remain."
            if not errors:
                _record_account_form(account, form, "account_updated")
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    errors["email"] = "An account with this email already exists."
                else:
                    flash("Account profile updated.", "success")
                    form = _account_form_values(account)
        elif action == "reset_password":
            temporary_password = "".join(
                secrets.choice(string.ascii_letters + string.digits + "!@#%")
                for _ in range(24)
            )
            account.set_password(temporary_password)
            account.require_password_change()
            _record_account_activity(
                account,
                "password_reset",
                f"Password reset by {current_user.full_name}; temporary password issued.",
            )
            db.session.commit()
            flash("Password reset. Share the temporary password securely; it is shown only once.", "success")
        elif action == "deactivate":
            if account.account_status != "active":
                flash("Account is already not active.", "info")
            elif account.user_id == current_user.user_id:
                flash("You cannot deactivate your own account.", "warning")
            elif (
                account.role == User.ROLE_SYSTEM_ADMIN
                and (db.session.scalar(
                    db.select(func.count(User.user_id)).where(
                        User.role == User.ROLE_SYSTEM_ADMIN,
                        User.account_status == "active",
                    )
                ) or 0) <= 1
            ):
                flash("At least one active system administrator must remain.", "warning")
            else:
                account.account_status = "inactive"
                _record_account_activity(
                    account,
                    "account_deactivated",
                    f"Account deactivated by {current_user.full_name}.",
                )
                db.session.commit()
                flash("User account deactivated.", "success")
                form = _account_form_values(account)
                if clean_text(request.form.get("next")) == "accounts":
                    return redirect(url_for("admin.accounts"))
        else:
            abort(400, description="Choose a valid account action.")

    activity = db.session.scalars(
        db.select(AccountActivityLog)
        .options(joinedload(AccountActivityLog.actor_user))
        .where(AccountActivityLog.target_user_id == account.user_id)
        .order_by(AccountActivityLog.recorded_at.desc(), AccountActivityLog.activity_id.desc())
        .limit(50)
    ).all()
    account_applications = db.session.scalars(
        visible_application_query(
            db.select(Application)
            .options(joinedload(Application.service), joinedload(Application.payments))
            .where(Application.applicant_id == account.user_id)
            .order_by(Application.submission_date.desc())
            .limit(50)
        )
    ).unique().all()
    return render_template(
        "admin/account_form.html",
        heading="Account profile",
        form=form,
        errors=errors,
        departments=departments,
        roles=(User.ROLE_CITIZEN,) if is_department_admin() else User.ROLES,
        role_labels=User.ROLE_LABELS,
        account_statuses=ACCOUNT_STATUSES,
        permission_options=PERMISSION_OPTIONS,
        allow_admin_fields=not is_department_admin(),
        temporary_password=temporary_password,
        account=account,
        activity=activity,
        account_applications=account_applications,
        status_labels=STATUS_LABELS,
    )


@admin_bp.route("/department/dashboard")
@role_required(User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR)
def department_dashboard():
    if "applications.review" in set(current_user.admin_permissions or ()) and current_user.department_id:
        return redirect(url_for("admin.applications"))
    if "services.manage" in set(current_user.admin_permissions or ()) and current_user.department_id:
        return redirect(url_for("admin.services"))
    abort(403)
