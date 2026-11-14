"""SSS assistance payment step. SS Number registration has no processing fee in OneGov PH."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import update

from app import db
from app.models.application import Application
from app.models.notification import Notification
from app.services.application_forms import specification_for
from app.services.application_service import field_map, missing_documents, read_details, write_details
from app.services.tracking_service import add_event


NEW_APPLICATION_FEE = Decimal("0.00")


def _now():
    return datetime.now().replace(microsecond=0)


def _is_reviewed(application):
    return bool(read_details(application).get("sss_reviewed"))


def fee_configuration(application=None):
    """Feature configuration shown on the payment step."""
    return {
        "new_application_fee": NEW_APPLICATION_FEE,
        "new_application_fee_display": f"₱{NEW_APPLICATION_FEE:,.2f}",
        "payment_required": False,
        "payment_required_label": "No",
        "payment_status": "not_applicable",
        "payment_status_label": "Not Applicable",
        "official_receipt": "Not issued — no payment collected",
        "note": (
            "SS Number registration has no processing fee in OneGov PH. "
            "OneGov PH does not collect a payment and does not issue an SS Number."
        ),
    }


def payment_summary(application):
    answers = field_map(application)
    config = fee_configuration(application)
    amount = NEW_APPLICATION_FEE
    full_name = " ".join(
        part
        for part in (
            answers.get("first_name"),
            answers.get("middle_name"),
            answers.get("last_name"),
        )
        if part
    ).strip()
    return {
        "service_kind": "sss",
        "application_type": "SSS assistance",
        "full_name": full_name,
        "barangay": answers.get("barangay") or "",
        "city": answers.get("city") or "",
        "has_primary_id": answers.get("has_primary_id") or "",
        "amount": amount,
        "amount_display": f"₱{amount:,.2f}",
        "application_fee": amount,
        "application_fee_display": f"₱{amount:,.2f}",
        "processing_fee": Decimal("0.00"),
        "processing_fee_display": "₱0.00",
        "payment": None,
        "method_label": None,
        "status_label": config["payment_status_label"],
        "status_key": "not_applicable",
        "payment_required": False,
        "payment_required_label": config["payment_required_label"],
        "fee_configuration": config,
        "provider_status": None,
        "checkout_id": None,
    }


def finalize_sss_application(application, user, new_status="submitted"):
    """Leave draft after review when no payment is required."""
    values = field_map(application)
    spec = specification_for(application.service, values) or {}
    if missing_documents(application, spec):
        return "Upload every required document before you continue."
    if not _is_reviewed(application):
        return "Review your application before payment."
    if application.application_status != "draft":
        return None
    now = _now()
    updated = db.session.execute(
        update(Application)
        .where(
            Application.application_id == application.application_id,
            Application.applicant_id == user.user_id,
            Application.application_status == "draft",
        )
        .values(
            application_status=new_status,
            submission_date=now,
            last_updated=now,
        )
    )
    if updated.rowcount != 1:
        db.session.rollback()
        return None
    add_event(
        application,
        user.user_id,
        new_status,
        spec.get("submit_event")
        or (
            "SSS request saved for assistance and tracking. "
            "No payment was required. "
            "SSS has not received this as an official filing, and OneGov PH has not issued an SS Number."
        ),
        "draft",
        now,
    )
    notice = spec.get("submit_notice")
    db.session.add(
        Notification(
            user_id=user.user_id,
            notification_title="SSS request received",
            notification_message=(
                notice.format(reference=application.tracking_number)
                if notice
                else (
                    f"Your SSS request {application.tracking_number} was submitted in OneGov PH. "
                    "No payment was collected. OneGov PH has not issued an SS Number."
                )
            ),
            notification_type="application",
            read_status="unread",
            created_date=now,
        )
    )
    details = read_details(application)
    details["payment"] = {
        "required": False,
        "status": "not_applicable",
        "amount": "0.00",
        "application_type": "sss",
    }
    write_details(application, details)
    db.session.commit()
    application.application_status = new_status
    application.submission_date = now
    application.last_updated = now
    return None


def confirm_free_application(application, user):
    """Confirm the free new-application payment step and finalize."""
    if not _is_reviewed(application):
        return "Review your application before payment."
    if application.application_status != "draft":
        return None
    return finalize_sss_application(application, user, "submitted")
