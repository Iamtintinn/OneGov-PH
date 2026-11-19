import re

from flask import Blueprint, abort, flash, redirect, render_template, request
from flask_login import current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.models.application import Application
from app.models.department import Department
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.service import Service
from app.models.user import User
from app.utils.access import (
    is_department_admin,
    visible_application_query,
    visible_notification_query,
    visible_payment_query,
    visible_service_query,
)
from app.utils.decorators import citizen_portal_required
from app.utils.portal import in_admin_portal, portal_url_for as url_for
from app.utils.validators import (
    clean_text,
    normalize_contact_number,
    validate_name,
    validate_new_password,
)

PENDING_STATUSES = frozenset({
    "submitted",
    "under_review",
    "pending_documents",
    "for_payment",
    "with_hit",
})
IN_PROGRESS_STATUSES = frozenset({
    "approved",
    "paid",
    "scheduled",
    "processing",
    "for_biometrics",
    "ready_for_release",
})
COMPLETED_STATUSES = frozenset({"completed"})

PAYMENT_METHOD_LABELS = {
    "gcash": "GCash",
    "maya": "Maya",
    "bank_transfer": "Bank transfer",
    "over_the_counter": "Over the counter",
    "online_banking": "Online banking",
}
PAYMENT_STATUS_LABELS = {
    "pending": "Pending",
    "paid": "Paid",
    "failed": "Failed",
    "refunded": "Refunded",
    "cancelled": "Cancelled",
}

STATUS_LABELS = {
    "draft": "Draft",
    "submitted": "Pending",
    "under_review": "Under review",
    "pending_documents": "Documents required",
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

citizen_bp = Blueprint("citizen", __name__)


def _search_pattern(term):
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _uses_department_scope():
    return in_admin_portal() and is_department_admin()


def _application_counts(user_id):
    query = db.select(Application.application_status, func.count()).group_by(
        Application.application_status
    )
    if _uses_department_scope():
        query = visible_application_query(query)
    else:
        query = query.where(Application.applicant_id == user_id)
    rows = db.session.execute(query).all()
    summary = {"total": 0, "pending": 0, "in_progress": 0, "completed": 0}
    for status, count in rows:
        summary["total"] += count
        if status in PENDING_STATUSES:
            summary["pending"] += count
        elif status in IN_PROGRESS_STATUSES:
            summary["in_progress"] += count
        elif status in COMPLETED_STATUSES:
            summary["completed"] += count
    return summary


def _owned_applications(user_id):
    query = (
        db.select(Application)
        .options(
            joinedload(Application.service).joinedload(Service.department),
            joinedload(Application.department),
            joinedload(Application.payments),
        )
        .order_by(Application.submission_date.desc(), Application.application_id.desc())
    )
    if _uses_department_scope():
        query = visible_application_query(query)
    else:
        query = query.where(Application.applicant_id == user_id)
    return db.session.scalars(query).unique().all()


def _service_category(value):
    category = (value or "").strip().lower()
    if category not in {"id", "clearance", "certificate"}:
        return ""
    return category


def _service_text(service):
    department = service.department.department_name if service.department is not None else ""
    return f"{service.service_name} {service.description or ''} {department}".casefold()


def _is_government_id(service):
    text = _service_text(service)
    if "clearance" in text:
        return False
    return (
        "passport" in text
        or "national id" in text
        or "identification" in text
        or re.search(r"\bid\b", text) is not None
        or re.search(r"\bsss\b", text) is not None
    )


def _is_clearance(service):
    return "clearance" in _service_text(service)


def _is_certificate(service):
    if _is_government_id(service) or _is_clearance(service):
        return False
    return "certificate" in _service_text(service)


def _active_services(term="", category=""):
    category = _service_category(category)
    services_query = (
        db.select(Service)
        .join(Service.department)
        .where(
            Service.service_status == "active",
            Department.department_status == "active",
        )
        .order_by(Department.department_name, Service.service_name)
    )
    if term:
        pattern = _search_pattern(term)
        services_query = services_query.where(
            db.or_(
                Service.service_name.like(pattern, escape="\\"),
                Service.description.like(pattern, escape="\\"),
                Department.department_name.like(pattern, escape="\\"),
            )
        )
    services = db.session.scalars(visible_service_query(services_query)).all()
    if category == "id":
        return [service for service in services if _is_government_id(service)]
    if category == "clearance":
        return [service for service in services if _is_clearance(service)]
    if category == "certificate":
        return [service for service in services if _is_certificate(service)]
    return services


def _password_errors(password, confirm_password):
    return validate_new_password(password, confirm_password)


def _citizen_notifications(user_id):
    notices_query = (
        db.select(Notification)
        .order_by(Notification.created_date.desc(), Notification.notification_id.desc())
        .limit(6)
    )
    unread_query = (
        db.select(func.count())
        .select_from(Notification)
        .where(Notification.read_status == "unread")
    )
    if _uses_department_scope():
        notices_query = visible_notification_query(notices_query)
        unread_query = visible_notification_query(unread_query)
    else:
        notices_query = notices_query.where(Notification.user_id == user_id)
        unread_query = unread_query.where(Notification.user_id == user_id)
    notices = db.session.scalars(notices_query).all()
    unread = db.session.scalar(unread_query)
    return notices, unread or 0


def portal_navigation_context():
    if not current_user.is_authenticated:
        return {}
    if current_user.role not in {User.ROLE_CITIZEN, User.ROLE_SYSTEM_ADMIN}:
        if not (in_admin_portal() and is_department_admin()):
            return {}
    notices, unread = _citizen_notifications(current_user.user_id)
    from app.services.application_forms import applicable_service_names, specification_for

    def status_labels_for(service, application=None):
        labels = dict(STATUS_LABELS)
        values = None
        if application is not None:
            from app.services.application_service import field_map

            values = field_map(application)
        spec = specification_for(service, values) if service is not None else None
        if spec and spec.get("status_labels"):
            labels.update(spec["status_labels"])
        if application is not None:
            from app.services.passport_admin import (
                current_status_key,
                is_passport_application,
                status_label,
            )

            if is_passport_application(application) and current_status_key(application):
                label = status_label(application)
                if label:
                    labels[application.application_status] = label
        return labels

    def beneficiary_rows(value):
        from app.services.application_forms import parse_beneficiaries

        return parse_beneficiaries(value)

    def show_saved_answer(spec, rows, key):
        from app.services.application_forms import field_is_visible

        if not spec:
            return True
        answers = {row.get("key"): row.get("value") or "" for row in rows}
        match = next((item for item in spec.get("fields") or [] if item.get("key") == key), None)
        if match is None:
            return True
        return field_is_visible(match, answers)

    return {
        "nav_notifications": notices,
        "unread_notification_count": unread,
        "applicable_service_names": applicable_service_names(),
        "status_labels_for": status_labels_for,
        "beneficiary_rows": beneficiary_rows,
        "show_saved_answer": show_saved_answer,
    }


@citizen_bp.context_processor
def citizen_navigation():
    return portal_navigation_context()


@citizen_bp.route("/citizen/dashboard")
@citizen_portal_required
def dashboard():
    service_query = " ".join((request.args.get("q") or "").split())[:80]
    services = _active_services(service_query)
    applications = _owned_applications(current_user.user_id)[:5]
    return render_template(
        "citizen/dashboard.html",
        service_query=service_query,
        services=services,
        applications=applications,
        summary=_application_counts(current_user.user_id),
        status_labels=STATUS_LABELS,
    )


@citizen_bp.route("/citizen/applications/<int:application_id>")
@citizen_portal_required
def application_detail(application_id):
    query = visible_application_query(
        db.select(Application)
        .options(
            joinedload(Application.service).joinedload(Service.department),
            joinedload(Application.department),
            joinedload(Application.requirements),
            joinedload(Application.payments),
        )
        .where(Application.application_id == application_id)
    )
    if not _uses_department_scope():
        query = query.where(Application.applicant_id == current_user.user_id)
    application = db.session.scalars(query).unique().first()
    if application is None:
        abort(404)
    from app.services.application_forms import specification_for
    from app.services.application_service import document_rules, field_map, read_checklist, read_fields

    answers = field_map(application)
    spec = specification_for(application.service, answers)
    documents = [] if spec is None or spec.get("checklist") else document_rules(spec, answers)
    passport_appointment = None
    passport_summary = None
    passport_physical = None
    passport_confirmation_id = None
    barangay_summary = None
    barangay_confirmation_id = None
    senior_delivery = None
    senior_delivery_address = ""
    senior_admin_confirmation = None
    nbi_delivery = None
    nbi_delivery_address = ""
    if spec and spec.get("kind") == "passport":
        from app.services.passport_admin import summary as physical_summary
        from app.services.passport_confirmation_pdf import confirmation_id_for
        from app.services.passport_payment import payment_summary
        from app.services.passport_scheduling import appointment_for

        passport_appointment = appointment_for(application)
        passport_summary = payment_summary(application)
        passport_physical = physical_summary(application)
        if application.application_status != "draft":
            passport_confirmation_id = confirmation_id_for(application)
    elif spec and spec.get("kind") in {"barangay", "residency"}:
        from app.services.barangay_confirmation_pdf import confirmation_id_for
        from app.services.barangay_payment import payment_summary

        barangay_summary = payment_summary(application)
        if application.application_status != "draft":
            barangay_confirmation_id = confirmation_id_for(application)
    elif spec and spec.get("kind") == "senior":
        from app.services.senior_admin import summary as senior_confirmation_summary
        from app.services.senior_confirmation_pdf import confirmation_id_for
        from app.services.senior_delivery import delivery_address, delivery_for
        from app.services.senior_payment import payment_summary

        barangay_summary = payment_summary(application)
        senior_delivery = delivery_for(application)
        senior_delivery_address = delivery_address(senior_delivery) if senior_delivery else ""
        senior_admin_confirmation = senior_confirmation_summary(application)
        if application.application_status != "draft":
            barangay_confirmation_id = confirmation_id_for(application)
    elif spec and spec.get("kind") == "nbi":
        from app.services.nbi_confirmation_pdf import confirmation_id_for
        from app.services.nbi_delivery import delivery_address, delivery_for
        from app.services.nbi_payment import payment_summary

        barangay_summary = payment_summary(application)
        nbi_delivery = delivery_for(application)
        nbi_delivery_address = delivery_address(nbi_delivery) if nbi_delivery else ""
        if application.application_status != "draft":
            barangay_confirmation_id = confirmation_id_for(application)
    elif spec and spec.get("kind") == "birth":
        from app.services.birth_confirmation_pdf import confirmation_id_for
        from app.services.birth_payment import payment_summary

        barangay_summary = payment_summary(application)
        if application.application_status != "draft":
            barangay_confirmation_id = confirmation_id_for(application)
    elif spec and spec.get("kind") == "cenomar":
        from app.services.cenomar_confirmation_pdf import confirmation_id_for
        from app.services.cenomar_payment import payment_summary

        barangay_summary = payment_summary(application)
        if application.application_status != "draft":
            barangay_confirmation_id = confirmation_id_for(application)
    elif spec and spec.get("kind") == "philsys":
        from app.services.philsys_confirmation_pdf import confirmation_id_for
        from app.services.philsys_payment import payment_summary

        barangay_summary = payment_summary(application)
        if application.application_status != "draft":
            barangay_confirmation_id = confirmation_id_for(application)
    elif spec and spec.get("kind") == "sss":
        from app.services.sss_confirmation_pdf import confirmation_id_for
        from app.services.sss_payment import payment_summary

        barangay_summary = payment_summary(application)
        if application.application_status != "draft":
            barangay_confirmation_id = confirmation_id_for(application)
    return render_template(
        "applications/application_details.html",
        application=application,
        status_labels=STATUS_LABELS,
        payment_status_labels=PAYMENT_STATUS_LABELS,
        spec=spec,
        detail_fields=read_fields(application),
        detail_documents=documents,
        detail_checklist=read_checklist(application) if spec and (spec.get("checklist") or spec.get("kind") in ("philsys", "passport")) else [],
        requirements={item.requirement_name: item for item in application.requirements},
        passport_appointment=passport_appointment,
        passport_summary=passport_summary,
        passport_physical=passport_physical,
        passport_confirmation_id=passport_confirmation_id,
        barangay_summary=barangay_summary,
        barangay_confirmation_id=barangay_confirmation_id,
        senior_delivery=senior_delivery,
        senior_delivery_address=senior_delivery_address,
        senior_admin_confirmation=senior_admin_confirmation,
        nbi_delivery=nbi_delivery,
        nbi_delivery_address=nbi_delivery_address,
    )


@citizen_bp.route("/citizen/services")
@citizen_portal_required
def services():
    service_query = " ".join((request.args.get("q") or "").split())[:80]
    service_category = _service_category(request.args.get("category"))
    catalog = _active_services(service_query, "")
    category_counts = {
        "all": len(catalog),
        "id": sum(1 for service in catalog if _is_government_id(service)),
        "clearance": sum(1 for service in catalog if _is_clearance(service)),
        "certificate": sum(1 for service in catalog if _is_certificate(service)),
    }
    return render_template(
        "citizen/services.html",
        service_query=service_query,
        service_category=service_category,
        services=_active_services(service_query, service_category),
        category_counts=category_counts,
    )


@citizen_bp.route("/citizen/applications")
@citizen_portal_required
def applications():
    return render_template(
        "citizen/application_history.html",
        applications=_owned_applications(current_user.user_id),
        status_labels=STATUS_LABELS,
        payment_status_labels=PAYMENT_STATUS_LABELS,
    )


@citizen_bp.route("/citizen/tracking")
@citizen_portal_required
def tracking():
    applications = _owned_applications(current_user.user_id)
    from app.services.tracking_service import events_by_application as group_events

    events_by_application = group_events([item.application_id for item in applications])
    return render_template(
        "applications/track_application.html",
        applications=applications,
        events_by_application=events_by_application,
        status_labels=STATUS_LABELS,
        payment_status_labels=PAYMENT_STATUS_LABELS,
    )


@citizen_bp.route("/citizen/payments")
@citizen_portal_required
def payments():
    query = (
        db.select(Payment)
        .options(joinedload(Payment.application).joinedload(Application.service))
        .order_by(Payment.payment_id.desc())
    )
    if _uses_department_scope():
        query = visible_payment_query(query)
    else:
        query = query.join(Application, Payment.application_id == Application.application_id).where(
            Application.applicant_id == current_user.user_id
        )
    records = db.session.scalars(query).unique().all()
    return render_template(
        "payments/payment_history.html",
        payments=records,
        payment_method_labels=PAYMENT_METHOD_LABELS,
        payment_status_labels=PAYMENT_STATUS_LABELS,
    )


@citizen_bp.route("/citizen/notifications")
@citizen_portal_required
def notifications():
    query = db.select(Notification).order_by(
        Notification.created_date.desc(), Notification.notification_id.desc()
    )
    if _uses_department_scope():
        query = visible_notification_query(query)
    else:
        query = query.where(Notification.user_id == current_user.user_id)
    notices = db.session.scalars(query).all()
    return render_template("citizen/notifications.html", notifications=notices)


@citizen_bp.route("/citizen/profile", methods=["GET", "POST"])
@citizen_portal_required
def profile():
    errors = {}
    if request.method == "POST":
        first_name, first_error = validate_name(request.form.get("first_name"), "First name")
        middle_name, middle_error = validate_name(
            request.form.get("middle_name"), "Middle name", required=False
        )
        last_name, last_error = validate_name(request.form.get("last_name"), "Last name")
        contact_number = normalize_contact_number(request.form.get("contact_number"))
        contact_digits = contact_number[1:] if contact_number.startswith("+") else contact_number
        address = clean_text(request.form.get("address"))
        if first_error:
            errors["first_name"] = first_error
        if middle_error:
            errors["middle_name"] = middle_error
        if last_error:
            errors["last_name"] = last_error
        if not contact_number:
            errors["contact_number"] = "Contact number is required."
        elif not contact_digits.isdigit() or not 10 <= len(contact_digits) <= 15:
            errors["contact_number"] = "Enter a valid contact number."
        if len(address) > 500:
            errors["address"] = "Address must be 500 characters or fewer."
        if not errors:
            current_user.set_name(first_name, last_name, middle_name or None)
            current_user.contact_number = contact_number
            current_user.address = address or None
            db.session.commit()
            flash("Your profile has been updated.", "success")
            return redirect(url_for("citizen.profile"))
    return render_template("citizen/profile.html", errors=errors)


@citizen_bp.route("/citizen/settings", methods=["GET", "POST"])
@citizen_portal_required
def settings():
    errors = {}
    if request.method == "POST":
        current_password = request.form.get("current_password") or ""
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""
        if not current_user.check_password(current_password):
            errors["current_password"] = "Current password is incorrect."
        errors.update(_password_errors(password, confirm_password))
        if not errors:
            current_user.set_password(password)
            db.session.commit()
            flash("Your password has been updated.", "success")
            return redirect(url_for("citizen.settings"))
    return render_template("citizen/settings.html", errors=errors)


from app.routes.applications import register as register_application_routes

register_application_routes(citizen_bp)
