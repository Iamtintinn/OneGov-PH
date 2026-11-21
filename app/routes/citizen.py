import re

from flask import Blueprint, abort, flash, redirect, render_template, request
from flask_login import current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.models.application import Application, ApplicationEvent, ApplicationRequirement
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
READY_FOR_PICKUP_STATUSES = frozenset({"ready_for_release"})

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
    summary = {
        "total": 0,
        "pending": 0,
        "in_progress": 0,
        "completed": 0,
        "ready_for_pickup": 0,
    }
    for status, count in rows:
        summary["total"] += count
        if status in PENDING_STATUSES:
            summary["pending"] += count
        elif status in IN_PROGRESS_STATUSES:
            summary["in_progress"] += count
        elif status in COMPLETED_STATUSES:
            summary["completed"] += count
        if status in READY_FOR_PICKUP_STATUSES:
            summary["ready_for_pickup"] += count
    return summary


def _confirmation_pdf_route_for(application):
    kind = ((application.service or None) and getattr(application.service, "service_name", "") or "")
    # map by spec kind via known service names handled in applications routes
    name = kind.lower()
    mapping = [
        ("passport", "citizen.passport_confirmation_pdf"),
        ("barangay clearance", "citizen.barangay_confirmation_pdf"),
        ("certificate of residency", "citizen.barangay_confirmation_pdf"),
        ("senior citizen", "citizen.senior_confirmation_pdf"),
        ("nbi clearance", "citizen.nbi_confirmation_pdf"),
        ("birth certificate", "citizen.birth_confirmation_pdf"),
        ("cenomar", "citizen.cenomar_confirmation_pdf"),
        ("philsys", "citizen.philsys_confirmation_pdf"),
        ("ss number", "citizen.sss_confirmation_pdf"),
    ]
    for needle, endpoint in mapping:
        if needle in name:
            return endpoint
    return None


def _payment_receipt_route_for(application):
    # generic recorded-payment receipt not in schema; service confirmation PDFs act as available confirmations/receipts
    if application.application_status == "draft":
        return None
    return _confirmation_pdf_route_for(application)


def _profile_completion(user):
    fields = [
        ("First name", bool(clean_text(user.first_name))),
        ("Last name", bool(clean_text(user.last_name))),
        ("Email", bool(clean_text(user.email))),
        ("Contact number", bool(clean_text(user.contact_number))),
        ("Address", bool(clean_text(user.address))),
        ("Password set", bool(user.password_hash)),
    ]
    complete = sum(1 for _, ok in fields if ok)
    percent = int(round((complete / len(fields)) * 100)) if fields else 0
    missing = [label for label, ok in fields if not ok]
    return {"percent": percent, "complete": complete, "total": len(fields), "missing": missing}


def _dashboard_service_groups():
    return [
        {
            "key": "dfa",
            "title": "DFA Passport",
            "department": "Department of Foreign Affairs",
            "description": "Apply for or track a passport application.",
            "url": url_for("citizen.services", q="passport"),
            "icon": "dfa",
        },
        {
            "key": "psa",
            "title": "PSA Birth Certificate",
            "department": "Philippine Statistics Authority",
            "description": "Request and monitor PSA birth certificate applications.",
            "url": url_for("citizen.services", q="birth certificate"),
            "icon": "psa",
        },
        {
            "key": "nbi",
            "title": "NBI Clearance",
            "department": "National Bureau of Investigation",
            "description": "Apply, pay, and track your NBI clearance request.",
            "url": url_for("citizen.services", q="NBI"),
            "icon": "nbi",
        },
        {
            "key": "philsys",
            "title": "PhilSys / National ID",
            "department": "Philippine Identification System",
            "description": "View PhilSys-related services and application status.",
            "url": url_for("citizen.services", q="PhilSys"),
            "icon": "id",
        },
        {
            "key": "sss",
            "title": "SSS Services",
            "department": "Social Security System",
            "description": "Access SSS number and MySSS application services.",
            "url": url_for("citizen.services", q="SSS"),
            "icon": "sss",
        },
        {
            "key": "police",
            "title": "Police Clearance",
            "department": "Philippine National Police",
            "description": "Check available police clearance services in the catalog.",
            "url": url_for("citizen.services", q="police"),
            "icon": "shield",
        },
        {
            "key": "lgu",
            "title": "Barangay / LGU Services",
            "department": "Local Government Unit",
            "description": "Barangay clearance, residency, senior ID, and local services.",
            "url": url_for("citizen.services", q="barangay"),
            "icon": "lgu",
        },
        {
            "key": "cedula",
            "title": "Cedula / Local Certificates",
            "department": "Local Government Unit",
            "description": "Find cedula and other local certificate services when available.",
            "url": url_for("citizen.services", q="certificate"),
            "icon": "cert",
        },
    ]


def _is_archived(application):
    try:
        details = application.application_details or {}
        if isinstance(details, str):
            import json as _json; details = _json.loads(details)
        return bool((details or {}).get("archived"))
    except Exception:
        return False


def _owned_applications(user_id, include_archived=False, archived_only=False):
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
    rows = db.session.scalars(query).unique().all()
    if archived_only:
        return [r for r in rows if _is_archived(r)]
    if include_archived:
        return rows
    return [r for r in rows if not _is_archived(r)]


def _owned_application_or_404(application_id, user_id, include_archived=True):
    query = db.select(Application).options(
        joinedload(Application.service).joinedload(Service.department),
        joinedload(Application.department),
        joinedload(Application.payments),
        joinedload(Application.requirements),
    ).where(Application.application_id == application_id)
    if _uses_department_scope():
        query = visible_application_query(query)
    else:
        query = query.where(Application.applicant_id == user_id)
    app_obj = db.session.scalar(query)
    if not app_obj:
        from flask import abort
        abort(404)
    if not include_archived and _is_archived(app_obj):
        from flask import abort
        abort(404)
    return app_obj


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
    applications_all = _owned_applications(current_user.user_id)
    applications = applications_all[:5]
    notices, unread = _citizen_notifications(current_user.user_id)
    payment_records = db.session.scalars(
        visible_payment_query(
            db.select(Payment)
            .options(joinedload(Payment.application).joinedload(Application.service))
            .join(Application, Payment.application_id == Application.application_id)
            .where(Application.applicant_id == current_user.user_id)
            .order_by(Payment.payment_id.desc())
        )
        if _uses_department_scope()
        else (
            db.select(Payment)
            .options(joinedload(Payment.application).joinedload(Application.service))
            .join(Application, Payment.application_id == Application.application_id)
            .where(Application.applicant_id == current_user.user_id)
            .order_by(Payment.payment_id.desc())
        )
    ).unique().all()

    from datetime import datetime, timedelta
    from collections import Counter, OrderedDict
    from decimal import Decimal

    from app.services.tracking_service import events_by_application as grouped_events
    from app.services.application_forms import specification_for
    from app.services.application_service import read_details

    recent_ids = [item.application_id for item in applications]
    event_map = grouped_events(recent_ids)
    recent_rows = []
    for app_item in applications:
        events = event_map.get(app_item.application_id, [])
        latest = events[0] if events else None
        recent_rows.append(
            {
                "application": app_item,
                "latest_event": latest,
                "progress": _application_progress(app_item),
                "timeline": events[:4],
            }
        )

    def _status_label(app_item):
        labels = dict(STATUS_LABELS)
        spec = specification_for(app_item.service, None)
        if spec and spec.get("status_labels"):
            labels.update(spec["status_labels"])
        return labels.get(app_item.application_status, app_item.application_status.replace("_", " ").title())

    documents = []
    for req in db.session.scalars(
        db.select(ApplicationRequirement)
        .join(Application, Application.application_id == ApplicationRequirement.application_id)
        .where(Application.applicant_id == current_user.user_id)
        .order_by(ApplicationRequirement.requirement_id.desc())
    ).all():
        if req.uploaded_file:
            documents.append(req)
    documents = documents[:8]

    payment_rows = []
    paid_total = Decimal("0.00")
    pending_payments = 0
    for pay in payment_records:
        if pay.payment_status == "paid":
            try:
                paid_total += Decimal(str(pay.amount or 0))
            except Exception:
                pass
        if pay.payment_status == "pending":
            pending_payments += 1
    for pay in payment_records[:6]:
        app_item = pay.application
        receipt_route = _payment_receipt_route_for(app_item) if app_item else None
        payment_rows.append(
            {
                "payment": pay,
                "application": app_item,
                "status_label": PAYMENT_STATUS_LABELS.get(pay.payment_status, pay.payment_status),
                "method_label": PAYMENT_METHOD_LABELS.get(pay.payment_method, (pay.payment_method or "").replace("_", " ").title()),
                "receipt_route": receipt_route,
            }
        )

    my_documents = []
    for app_item in applications_all:
        receipt_route = _payment_receipt_route_for(app_item)
        details = read_details(app_item)
        delivery = (details.get("delivery") or {}) if isinstance(details, dict) else {}
        delivery_status = None
        if isinstance(delivery, dict):
            delivery_status = delivery.get("delivery_status") or delivery.get("status") or delivery.get("fulfillment_status")
        my_documents.append(
            {
                "application": app_item,
                "confirmation_route": receipt_route,
                "delivery_status": delivery_status,
            }
        )

    status_palette = {
        "draft": "#94A3B8",
        "submitted": "#F59E0B",
        "under_review": "#F97316",
        "pending_documents": "#EF4444",
        "for_payment": "#EAB308",
        "paid": "#14B8A6",
        "scheduled": "#06B6D4",
        "processing": "#6366F1",
        "ready_for_release": "#8B5CF6",
        "completed": "#16A34A",
        "rejected": "#DC2626",
        "cancelled": "#64748B",
        "approved": "#0EA5E9",
        "for_biometrics": "#3B82F6",
        "with_hit": "#B91C1C",
    }
    status_counts = Counter(app.application_status for app in applications_all)
    total_apps = len(applications_all)
    status_chart = []
    for status, count in sorted(status_counts.items(), key=lambda x: (-x[1], x[0])):
        pct = round((count / total_apps) * 100, 1) if total_apps else 0
        status_chart.append(
            {
                "key": status,
                "label": STATUS_LABELS.get(status, status.replace("_", " ").title()),
                "count": count,
                "percent": pct,
                "color": status_palette.get(status, "#2563EB"),
            }
        )
    # donut gradient segments
    donut_segments = []
    cursor = 0.0
    for item in status_chart:
        start = cursor
        cursor += (item["count"] / total_apps * 100) if total_apps else 0
        donut_segments.append(f"{item['color']} {start:.2f}% {cursor:.2f}%")
    donut_gradient = "conic-gradient(" + ", ".join(donut_segments) + ")" if donut_segments else "conic-gradient(#E2E8F0 0% 100%)"

    # monthly submissions (last 6 months) from real submission dates
    now = datetime.utcnow()
    months = []
    for i in range(5, -1, -1):
        year = (now.year if now.month - i >= 1 else now.year - 1)
        month = ((now.month - i - 1) % 12) + 1
        if now.month - i <= 0:
            year = now.year - 1
        # simpler: step back by months
        m_index = now.month - 1 - i
        y = now.year + (m_index // 12)
        m = (m_index % 12) + 1
        months.append((y, m))
    month_counts = OrderedDict()
    month_labels = []
    import calendar
    for y, m in months:
        key = f"{y}-{m:02d}"
        month_labels.append(calendar.month_abbr[m])
        month_counts[key] = 0
    for app_item in applications_all:
        dt = getattr(app_item, "submission_date", None)
        if not dt:
            continue
        key = f"{dt.year}-{dt.month:02d}"
        if key in month_counts:
            month_counts[key] += 1
    monthly_values = list(month_counts.values())
    monthly_max = max(monthly_values) if monthly_values else 0
    monthly_chart = []
    for idx, key in enumerate(month_counts.keys()):
        val = month_counts[key]
        height = int((val / monthly_max) * 100) if monthly_max else 0
        monthly_chart.append({"label": month_labels[idx], "count": val, "height": height})

    summary = _application_counts(current_user.user_id)
    analytics = {
        "status_chart": status_chart,
        "donut_gradient": donut_gradient,
        "monthly_chart": monthly_chart,
        "monthly_max": monthly_max,
        "paid_total": f"{paid_total:.2f}",
        "pending_payments": pending_payments,
        "total_payments": len(payment_records),
        "total_apps": total_apps,
    }

    return render_template(
        "citizen/dashboard.html",
        service_query=service_query,
        services=services,
        applications=applications,
        applications_all=applications_all,
        summary=summary,
        status_labels=STATUS_LABELS,
        payment_method_labels=PAYMENT_METHOD_LABELS,
        payment_status_labels=PAYMENT_STATUS_LABELS,
        recent_rows=recent_rows,
        notifications=notices,
        profile_completion=_profile_completion(current_user),
        payment_rows=payment_rows,
        service_groups=_dashboard_service_groups(),
        uploaded_documents=documents,
        my_documents=my_documents[:8],
        status_label_for=_status_label,
        analytics=analytics,
    )


def _application_progress(application):
    status = application.application_status
    ordered = ["submitted", "under_review", "pending_documents", "for_payment", "paid", "scheduled", "processing", "ready_for_release", "completed"]
    if status in {"rejected", "cancelled", "draft"}:
        return {"percent": 5 if status == "draft" else 100, "label": STATUS_LABELS.get(status, status.title()), "terminal": status}
    if status in ordered:
        idx = ordered.index(status)
        percent = int(((idx + 1) / len(ordered)) * 100)
    elif status in IN_PROGRESS_STATUSES:
        percent = 70
    elif status in PENDING_STATUSES:
        percent = 35
    else:
        percent = 20
    return {"percent": max(10, min(percent, 100)), "label": STATUS_LABELS.get(status, status.replace("_", " ").title()), "terminal": None}


@citizen_bp.route("/citizen/notifications/<int:notification_id>/read", methods=["POST"])
@citizen_portal_required
def notification_read(notification_id):
    notice = db.session.scalar(
        db.select(Notification).where(
            Notification.notification_id == notification_id,
            Notification.user_id == current_user.user_id,
        )
    )
    if notice is None:
        abort(404)
    if notice.read_status != "read":
        notice.read_status = "read"
        db.session.commit()
    return redirect(request.form.get("next") or url_for("citizen.notifications"))


@citizen_bp.route("/citizen/notifications/read-all", methods=["POST"])
@citizen_portal_required
def notifications_read_all():
    notices = db.session.scalars(
        db.select(Notification).where(
            Notification.user_id == current_user.user_id,
            Notification.read_status == "unread",
        )
    ).all()
    for notice in notices:
        notice.read_status = "read"
    if notices:
        db.session.commit()
    return redirect(request.form.get("next") or url_for("citizen.notifications"))


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

    from app.routes.admin_portal import tracking_detail_data
    from app.services.application_forms import specification_for
    from app.services.application_service import field_map

    applicant = db.session.get(User, application.applicant_id)
    events = db.session.scalars(
        db.select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application.application_id)
        .order_by(ApplicationEvent.recorded_at.desc(), ApplicationEvent.tracking_id.desc())
    ).all()
    tracking = tracking_detail_data(application, applicant)
    answers = field_map(application)
    spec = specification_for(application.service, answers)

    confirmation_id = None
    confirmation_pdf_url = None
    confirmation_label = "Download receipt"
    if spec and application.application_status != "draft":
        kind = spec.get("kind")
        if kind == "passport":
            from app.services.passport_confirmation_pdf import confirmation_id_for

            confirmation_id = confirmation_id_for(application)
            if confirmation_id:
                confirmation_pdf_url = url_for("citizen.passport_confirmation_pdf", application_id=application.application_id)
                confirmation_label = "Download PDF confirmation"
        elif kind in {"barangay", "residency"}:
            from app.services.barangay_confirmation_pdf import confirmation_id_for

            confirmation_id = confirmation_id_for(application)
            if confirmation_id:
                confirmation_pdf_url = url_for("citizen.barangay_confirmation_pdf", application_id=application.application_id)
        elif kind == "senior":
            from app.services.senior_confirmation_pdf import confirmation_id_for

            confirmation_id = confirmation_id_for(application)
            if confirmation_id:
                confirmation_pdf_url = url_for("citizen.senior_confirmation_pdf", application_id=application.application_id)
        elif kind == "nbi":
            from app.services.nbi_confirmation_pdf import confirmation_id_for

            confirmation_id = confirmation_id_for(application)
            if confirmation_id:
                confirmation_pdf_url = url_for("citizen.nbi_confirmation_pdf", application_id=application.application_id)
        elif kind == "birth":
            from app.services.birth_confirmation_pdf import confirmation_id_for

            confirmation_id = confirmation_id_for(application)
            if confirmation_id:
                confirmation_pdf_url = url_for("citizen.birth_confirmation_pdf", application_id=application.application_id)
        elif kind == "cenomar":
            from app.services.cenomar_confirmation_pdf import confirmation_id_for

            confirmation_id = confirmation_id_for(application)
            if confirmation_id:
                confirmation_pdf_url = url_for("citizen.cenomar_confirmation_pdf", application_id=application.application_id)
        elif kind == "philsys":
            from app.services.philsys_confirmation_pdf import confirmation_id_for

            confirmation_id = confirmation_id_for(application)
            if confirmation_id:
                confirmation_pdf_url = url_for("citizen.philsys_confirmation_pdf", application_id=application.application_id)
        elif kind == "sss":
            from app.services.sss_confirmation_pdf import confirmation_id_for

            confirmation_id = confirmation_id_for(application)
            if confirmation_id:
                confirmation_pdf_url = url_for("citizen.sss_confirmation_pdf", application_id=application.application_id)

    return render_template(
        "applications/citizen_application_detail.html",
        application=application,
        applicant=applicant,
        fields=answers,
        events=events,
        status_labels=STATUS_LABELS,
        tracking=tracking,
        spec=spec,
        confirmation_id=confirmation_id,
        confirmation_pdf_url=confirmation_pdf_url,
        confirmation_label=confirmation_label,
    )


@citizen_bp.route("/citizen/applications/<int:application_id>/received", methods=["POST"])
@citizen_portal_required
def mark_application_received(application_id):
    from datetime import datetime
    from app.routes.admin_portal import ADMIN_PROCESSING_BY_KEY, _admin_tracking_state, _delivery_state, _save_admin_tracking, _log_admin_status_event

    query = visible_application_query(
        db.select(Application).where(Application.application_id == application_id)
    )
    if not _uses_department_scope():
        query = query.where(Application.applicant_id == current_user.user_id)
    application = db.session.scalars(query).unique().first()
    if application is None:
        abort(404)

    is_pickup = False
    try:
        from app.routes.admin_portal import tracking_detail_data
        tracking = tracking_detail_data(application, db.session.get(User, application.applicant_id), include_map=False)
        pf = tracking.get("passport_fulfillment") or {}
        is_pickup = any([
            pf.get("fulfillment_method") == "pickup",
            (tracking.get("senior_fulfillment") or {}).get("method") == "pickup",
            (tracking.get("nbi_fulfillment") or {}).get("method") == "pickup",
            (tracking.get("philsys_fulfillment") or {}).get("method") == "pickup",
            (tracking.get("sss_fulfillment") or {}).get("method") == "pickup",
        ])
    except Exception:
        is_pickup = False

    if not is_pickup:
        flash("This action is only available for pickup applications.", "warning")
        return redirect(url_for("citizen.application_detail", application_id=application_id))

    if application.application_status != "ready_for_release":
        flash("You can mark this application as received once it is Ready for Pickup.", "warning")
        return redirect(url_for("citizen.application_detail", application_id=application_id))

    if application.application_status == "completed":
        return redirect(url_for("citizen.application_detail", application_id=application_id))

    now = datetime.now().replace(microsecond=0)
    state = _admin_tracking_state(application)
    processing = state["processing"]
    target = ADMIN_PROCESSING_BY_KEY.get("completed") or {"key": "completed", "label": "Completed", "legacy_status": "completed"}
    entry = {
        "key": target["key"],
        "label": target["label"],
        "legacy_status": target["legacy_status"],
        "note": "Marked as received by citizen.",
        "updated_by": current_user.user_id,
        "updated_by_name": current_user.full_name,
        "recorded_at": now.isoformat(),
        "recorded_at_label": now.strftime("%d %b %Y, %I:%M %p"),
    }
    processing.update(entry)
    processing.setdefault("history", []).append(dict(entry))
    _save_admin_tracking(application, state)

    previous_status = application.application_status
    application.application_status = "completed"
    _log_admin_status_event(application, previous_status, "Citizen marked pickup application as received.")
    db.session.commit()
    flash("Application marked as received.", "success")
    return redirect(url_for("citizen.application_detail", application_id=application_id))


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


def _filter_applications(applications, term="", status=""):
    term = " ".join((term or "").split()).casefold()
    status = clean_text(status)
    filtered = []
    for application in applications:
        if status and application.application_status != status:
            continue
        if term:
            haystack = " ".join([
                application.tracking_number or "",
                application.service.service_name if application.service else "",
                application.department.department_name if application.department else "",
                STATUS_LABELS.get(application.application_status, application.application_status or ""),
            ]).casefold()
            if term not in haystack:
                continue
        filtered.append(application)
    return filtered



@citizen_bp.route("/citizen/applications/<int:application_id>/delete", methods=["POST"])
@citizen_portal_required
def delete_application(application_id):
    application = _owned_application_or_404(application_id, current_user.user_id)
    from datetime import datetime as _dt
    details = application.application_details if isinstance(application.application_details, dict) else read_details(application)
    now = _dt.now().replace(microsecond=0).isoformat()
    details["archived"] = {"archived_at": now, "archived_by": current_user.user_id, "previous_status": application.application_status}
    write_details(application, details, commit=False)
    try:
        from app.services.audit_service import log_activity
        log_activity(activity_type="Application Archived", module="Applications", description=f"Citizen archived application {application.tracking_number}", record_id=application.tracking_number, previous_value={"status": application.application_status}, new_value={"archived": True}, status="Success", user=current_user)
    except Exception:
        pass
    db.session.commit()
    flash(f"Application {application.tracking_number} was moved to Archive.", "success")
    return redirect(request.referrer or url_for("citizen.applications"))


@citizen_bp.route("/citizen/drafts")
@citizen_portal_required
def drafts():
    rows = db.session.scalars(
        db.select(Application)
        .options(joinedload(Application.service).joinedload(Service.department), joinedload(Application.department), joinedload(Application.payments))
        .where(Application.applicant_id == current_user.user_id, Application.application_status == "draft")
        .order_by(Application.last_updated.desc(), Application.application_id.desc())
    ).unique().all()
    rows = [r for r in rows if not _is_archived(r)]
    q = (request.args.get("q") or "")[:80]
    filtered = _filter_applications(rows, q, "")
    return render_template("citizen/drafts.html", applications=filtered, total_count=len(rows), filtered_count=len(filtered), q=q, status_labels=STATUS_LABELS, payment_status_labels=PAYMENT_STATUS_LABELS)


@citizen_bp.route("/citizen/archive")
@citizen_portal_required
def archive():
    all_apps = _owned_applications(current_user.user_id, archived_only=True)
    q = (request.args.get("q") or "")[:80]
    status = clean_text(request.args.get("status"))
    filtered = _filter_applications(all_apps, q, status)
    status_options = [(key, label) for key, label in STATUS_LABELS.items() if key != "draft"]
    return render_template("citizen/archive.html", applications=filtered, total_count=len(all_apps), filtered_count=len(filtered), q=q, selected_status=status, status_options=status_options, status_labels=STATUS_LABELS, payment_status_labels=PAYMENT_STATUS_LABELS)


@citizen_bp.route("/citizen/applications/<int:application_id>/restore", methods=["POST"])
@citizen_portal_required
def restore_application(application_id):
    application = _owned_application_or_404(application_id, current_user.user_id)
    details = application.application_details if isinstance(application.application_details, dict) else read_details(application)
    if details.get("archived"):
        details.pop("archived", None)
        write_details(application, details, commit=False)
        try:
            from app.services.audit_service import log_activity
            log_activity(activity_type="Application Restored", module="Applications", description=f"Citizen restored application {application.tracking_number}", record_id=application.tracking_number, new_value={"archived": False}, status="Success", user=current_user)
        except Exception:
            pass
        db.session.commit()
        flash(f"Application {application.tracking_number} was restored.", "success")
    return redirect(request.referrer or url_for("citizen.archive"))


@citizen_bp.route("/citizen/applications/<int:application_id>/delete-permanent", methods=["POST"])
@citizen_portal_required
def delete_application_permanent(application_id):
    application = _owned_application_or_404(application_id, current_user.user_id)
    details = application.application_details if isinstance(application.application_details, dict) else read_details(application)
    if not details.get("archived"):
        flash("Only archived applications can be permanently deleted.", "warning")
        return redirect(request.referrer or url_for("citizen.archive"))
    tracking = application.tracking_number
    for table in ["application_tracking", "application_requirements", "payments"]:
        try:
            db.session.execute(db.text(f"DELETE FROM {table} WHERE application_id=:id"), {"id": application_id})
        except Exception:
            db.session.rollback()
    try:
        from app.services.audit_service import log_activity
        log_activity(activity_type="Application Deleted Permanently", module="Applications", description=f"Citizen permanently deleted application {tracking}", record_id=tracking, previous_value={"application_id": application_id}, status="Success", user=current_user)
    except Exception:
        pass
    db.session.delete(application)
    db.session.commit()
    flash(f"Application {tracking} was permanently deleted.", "success")
    return redirect(request.referrer or url_for("citizen.archive"))

@citizen_bp.route("/citizen/applications")
@citizen_portal_required
def applications():
    all_apps = _owned_applications(current_user.user_id)
    q = (request.args.get("q") or "")[:80]
    status = clean_text(request.args.get("status"))
    filtered = _filter_applications(all_apps, q, status)
    status_options = [(key, label) for key, label in STATUS_LABELS.items() if key != "draft"]
    return render_template(
        "citizen/application_history.html",
        applications=filtered,
        total_count=len(all_apps),
        filtered_count=len(filtered),
        q=q,
        selected_status=status,
        status_options=status_options,
        status_labels=STATUS_LABELS,
        payment_status_labels=PAYMENT_STATUS_LABELS,
    )


@citizen_bp.route("/citizen/tracking")
@citizen_portal_required
def tracking():
    all_apps = _owned_applications(current_user.user_id)
    q = (request.args.get("q") or "")[:80]
    status = clean_text(request.args.get("status"))
    filtered = _filter_applications(all_apps, q, status)
    from app.services.tracking_service import events_by_application as group_events

    events_by_application = group_events([item.application_id for item in filtered])
    status_options = [(key, label) for key, label in STATUS_LABELS.items() if key != "draft"]
    return render_template(
        "applications/track_application.html",
        applications=filtered,
        total_count=len(all_apps),
        filtered_count=len(filtered),
        q=q,
        selected_status=status,
        status_options=status_options,
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


@citizen_bp.route("/citizen/profile", methods=["GET"])
@citizen_portal_required
def profile():
    from sqlalchemy import desc
    from app.services.citizen_settings_service import profile_picture_url
    apps = _owned_applications(current_user.user_id)
    stats = {
        "total": len(apps),
        "pending": sum(1 for a in apps if a.application_status in PENDING_STATUSES),
        "processing": sum(1 for a in apps if a.application_status in IN_PROGRESS_STATUSES),
        "completed": sum(1 for a in apps if a.application_status in COMPLETED_STATUSES),
    }
    docs = []
    seen = set()
    for a in apps:
        name = (a.service.service_name if a.service else "Government service")
        if name in seen:
            continue
        seen.add(name)
        docs.append({
            "name": name,
            "department": a.service.department.department_name if a.service and a.service.department else "—",
            "status": STATUS_LABELS.get(a.application_status, a.application_status),
            "date": a.submission_date or a.last_updated,
        })
    events = db.session.scalars(
        db.select(ApplicationEvent)
        .options(joinedload(ApplicationEvent.application).joinedload(Application.service))
        .join(Application, ApplicationEvent.application_id == Application.application_id)
        .where(Application.applicant_id == current_user.user_id)
        .order_by(desc(ApplicationEvent.recorded_at))
        .limit(10)
    ).unique().all()
    activities = []
    for ev in events:
        app_obj = ev.application
        svc = app_obj.service.service_name if app_obj and app_obj.service else "Application"
        status_key = ev.new_status or ev.previous_status or "activity"
        label = STATUS_LABELS.get(status_key, str(status_key).replace("_", " ").title())
        activities.append({
            "label": label,
            "description": ev.update_description or svc,
            "service": svc,
            "date": ev.recorded_at,
        })
    return render_template(
        "citizen/profile.html",
        profile_picture_url=profile_picture_url(current_user),
        stats=stats,
        documents=docs[:8],
        activities=activities,
    )


@citizen_bp.route("/citizen/settings", methods=["GET", "POST"])
@citizen_portal_required
def settings():
    return redirect(url_for("citizen_settings.index"))


from app.routes.applications import register as _register_application_routes
_register_application_routes(citizen_bp, base="/citizen", wrap=citizen_portal_required)
