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
from app.utils.decorators import role_required
from app.utils.validators import clean_text, normalize_email, normalize_contact_number, validate_name

admin_bp = Blueprint("admin", __name__)


@admin_bp.context_processor
def admin_navigation():
    from app.routes.citizen import portal_navigation_context

    return portal_navigation_context()

PENDING_STATUSES = ("submitted", "under_review", "pending_documents", "for_payment")
ACCOUNT_STATUSES = ("active", "inactive", "suspended")
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
    if current_user.role == User.ROLE_SYSTEM_ADMIN:
        return
    if (
        current_user.role not in {User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR}
        or permission not in set(current_user.admin_permissions or ())
        or not current_user.department_id
    ):
        abort(403)


def _application_query_for_current_admin():
    query = db.select(Application).options(
        joinedload(Application.service),
        joinedload(Application.department),
        joinedload(Application.requirements),
        joinedload(Application.payments),
    )
    if current_user.role != User.ROLE_SYSTEM_ADMIN:
        _require_permission("applications.review")
        query = query.where(Application.assigned_department_id == current_user.department_id)
    return query


def _application_or_404(application_id):
    application = db.session.execute(
        _application_query_for_current_admin().where(Application.application_id == application_id)
    ).unique().scalar_one_or_none()
    if application is None:
        abort(404)
    return application


def _account_form_from_request():
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
    if role not in User.ROLES:
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


def _record_account_form(user, form, action):
    user.set_name(form["first_name"], form["last_name"], form["middle_name"])
    user.email = form["email"]
    user.contact_number = form["contact_number"] or None
    user.address = form["address"] or None
    user.role = form["role"]
    user.account_status = form["account_status"]
    user.department_id = form["department_id"]
    user.admin_permissions = form["admin_permissions"]
    _record_account_activity(
        user,
        action,
        f"Account profile updated by {current_user.full_name}; role {user.role}, status {user.account_status}.",
    )


def _account_form_values(user=None):
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
        "permissions": list(user.admin_permissions or ()) if user else [],
    }


@admin_bp.route("/admin/dashboard")
@role_required(User.ROLE_SYSTEM_ADMIN)
def dashboard():
    now = datetime.now()
    start = datetime.combine(now.date() - timedelta(days=6), time.min)
    weekly_rows = db.session.execute(
        db.select(func.date(Application.submission_date), func.count(Application.application_id))
        .where(Application.submission_date >= start, Application.application_status != "draft")
        .group_by(func.date(Application.submission_date))
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
        db.select(ApplicationEvent)
        .options(joinedload(ApplicationEvent.application).joinedload(Application.service))
        .order_by(ApplicationEvent.recorded_at.desc(), ApplicationEvent.tracking_id.desc())
        .limit(8)
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
        db.select(Service, func.count(Application.application_id))
        .outerjoin(Application, Application.service_id == Service.service_id)
        .group_by(Service.service_id)
        .order_by(Service.service_name)
    ).all()
    return render_template(
        "admin/dashboard.html",
        page_title="Admin dashboard",
        total_citizens=db.session.scalar(
            db.select(func.count(User.user_id)).where(User.role == User.ROLE_CITIZEN)
        )
        or 0,
        total_services=db.session.scalar(db.select(func.count(Service.service_id))) or 0,
        total_applications=db.session.scalar(db.select(func.count(Application.application_id))) or 0,
        pending_applications=db.session.scalar(
            db.select(func.count(Application.application_id)).where(
                Application.application_status.in_(PENDING_STATUSES)
            )
        )
        or 0,
        completed_applications=db.session.scalar(
            db.select(func.count(Application.application_id)).where(
                Application.application_status == "completed"
            )
        )
        or 0,
        total_payments=db.session.scalar(db.select(func.count(Payment.payment_id))) or 0,
        paid_amount=db.session.scalar(
            db.select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.payment_status == "paid")
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
    query = (
        db.select(Service, func.count(Application.application_id))
        .outerjoin(Application, Application.service_id == Service.service_id)
        .group_by(Service.service_id)
        .order_by(Service.service_name)
    )
    if current_user.role != User.ROLE_SYSTEM_ADMIN:
        query = query.where(Service.department_id == current_user.department_id)
    service_rows = db.session.execute(query).all()
    return render_template("admin/manage_services.html", service_rows=service_rows)


@admin_bp.route("/admin/services/<int:service_id>/status", methods=["POST"])
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR)
def service_status(service_id):
    _require_permission("services.manage")
    service = db.session.get(Service, service_id)
    if service is None:
        abort(404)
    if current_user.role != User.ROLE_SYSTEM_ADMIN and service.department_id != current_user.department_id:
        abort(404)
    target_status = clean_text(request.form.get("service_status"))
    if target_status not in {"active", "inactive"}:
        abort(400, description="Choose a valid service status.")
    service.service_status = target_status
    db.session.commit()
    flash(f"{service.service_name} is now {target_status}.", "success")
    return redirect(url_for("admin.services"))


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
    service_id = int(service_raw) if service_raw.isdigit() else None
    if service_id:
        query = query.where(Application.service_id == service_id)
    rows = db.session.scalars(query.order_by(Application.submission_date.desc()).limit(200)).unique().all()
    applicants = {
        user.user_id: user
        for user in db.session.scalars(
            db.select(User).where(User.user_id.in_({item.applicant_id for item in rows}))
        ).all()
    } if rows else {}
    return render_template(
        "admin/manage_applications.html",
        applications=rows,
        applicants=applicants,
        services=db.session.scalars(db.select(Service).order_by(Service.service_name)).all(),
        statuses=APPLICATION_STATUSES,
        status_labels=STATUS_LABELS,
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
        tracking_detail_data,
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
        tracking=tracking_detail_data(application, applicant),
        processing_statuses=ADMIN_PROCESSING_STATUSES,
        delivery_statuses=DELIVERY_STATUSES,
    )


@admin_bp.route("/admin/applications/<int:application_id>/update", methods=["POST"])
@role_required(User.ROLE_SYSTEM_ADMIN, User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR)
def update_application(application_id):
    application = _application_or_404(application_id)
    target_status = clean_text(request.form.get("application_status"))
    remarks = clean_text(request.form.get("remarks"))
    if target_status not in APPLICATION_STATUSES or target_status == "draft":
        abort(400, description="Choose a valid application status.")
    if len(remarks) > 500:
        flash("Remarks must be 500 characters or fewer.", "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))
    if target_status in {"rejected", "pending_documents"} and not remarks:
        flash("Add a reason when rejecting an application or requesting corrections.", "warning")
        return redirect(url_for("admin.application_detail", application_id=application_id))

    previous_status = application.application_status
    application.application_status = target_status
    description = f"Status changed to {STATUS_LABELS[target_status]}."
    if remarks:
        description += f" Remarks: {remarks}"
    _log_application_event(application, previous_status, description)
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
@role_required(User.ROLE_SYSTEM_ADMIN)
def accounts():
    query = db.select(User).options(joinedload(User.department))
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
        roles=User.ROLES,
        role_labels=User.ROLE_LABELS,
        account_statuses=ACCOUNT_STATUSES,
        selected_role=role,
        selected_status=status,
        search=search,
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
@role_required(User.ROLE_SYSTEM_ADMIN)
def account_detail(user_id):
    account = db.session.scalar(
        db.select(User).options(joinedload(User.department)).where(User.user_id == user_id)
    )
    if account is None:
        abort(404)
    departments = db.session.scalars(
        db.select(Department).where(Department.department_status == "active").order_by(
            Department.department_name
        )
    ).all()
    form = _account_form_values(account)
    errors = {}
    temporary_password = None
    if request.method == "POST":
        action = clean_text(request.form.get("action"))
        if action == "update":
            form, errors = _account_form_from_request()
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
            _record_account_activity(
                account,
                "password_reset",
                f"Password reset by {current_user.full_name}; temporary password issued.",
            )
            db.session.commit()
            flash("Password reset. Share the temporary password securely; it is shown only once.", "success")
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
        db.select(Application)
        .options(joinedload(Application.service), joinedload(Application.payments))
        .where(Application.applicant_id == account.user_id)
        .order_by(Application.submission_date.desc())
        .limit(50)
    ).unique().all()
    return render_template(
        "admin/account_form.html",
        heading="Account profile",
        form=form,
        errors=errors,
        departments=departments,
        roles=User.ROLES,
        role_labels=User.ROLE_LABELS,
        account_statuses=ACCOUNT_STATUSES,
        permission_options=PERMISSION_OPTIONS,
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
