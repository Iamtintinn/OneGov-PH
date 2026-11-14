"""PhilSys National ID payment step. Registration is free; this step records the free confirmation."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import update

from app import db
from app.models.application import Application
from app.models.notification import Notification
from app.services.application_forms import specification_for
from app.services.application_service import field_map, missing_documents, read_details, write_details
from app.services.philsys_scheduling import appointment_for
from app.services.tracking_service import add_event


REGISTRATION_FEE = Decimal("0.00")


def _now():
    return datetime.now().replace(microsecond=0)


def _is_reviewed(application):
    return bool(read_details(application).get("philsys_reviewed"))


def fee_configuration(application=None):
    return {
        "registration_fee": REGISTRATION_FEE,
        "registration_fee_display": f"₱{REGISTRATION_FEE:,.2f}",
        "payment_required": False,
        "payment_required_label": "No",
        "payment_status": "not_applicable",
        "payment_status_label": "Not Applicable",
        "note": (
            "PhilSys National ID registration is free. "
            "OneGov PH does not collect a fee and does not issue a National ID."
        ),
    }


def payment_summary(application):
    answers = field_map(application)
    config = fee_configuration(application)
    amount = REGISTRATION_FEE
    full_name = " ".join(
        part
        for part in (
            answers.get("first_name"),
            answers.get("middle_name"),
            answers.get("last_name"),
        )
        if part
    ).strip()
    appointment = appointment_for(application)
    return {
        "service_kind": "philsys",
        "applicant_name": full_name,
        "citizenship": answers.get("citizenship") or "",
        "appointment": appointment,
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


def finalize_philsys_application(application, user, new_status="submitted"):
    """Leave draft after review, schedule, and free payment confirmation."""
    values = field_map(application)
    spec = specification_for(application.service, values) or {}
    if missing_documents(application, spec):
        return "Upload every required document before you continue."
    if not _is_reviewed(application):
        return "Review your application before payment."
    if appointment_for(application) is None:
        return "Select a demonstration appointment before payment."
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
            "National ID preparation, demonstration appointment, and free payment step were saved. "
            "The person is not registered with PhilSys, and no National ID has been issued."
        ),
        "draft",
        now,
    )
    notice = spec.get("submit_notice")
    db.session.add(
        Notification(
            user_id=user.user_id,
            notification_title="National ID preparation received",
            notification_message=(
                notice.format(reference=application.tracking_number)
                if notice
                else (
                    f"Your National ID preparation {application.tracking_number} was submitted in OneGov PH. "
                    "No payment was collected. This is not PhilSys registration."
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
        "application_type": "philsys",
    }
    write_details(application, details)
    db.session.commit()
    application.application_status = new_status
    application.submission_date = now
    application.last_updated = now
    return None


def confirm_free_application(application, user):
    """Confirm the free registration payment step and finalize."""
    if not _is_reviewed(application):
        return "Review your application before payment."
    if appointment_for(application) is None:
        return "Select a demonstration appointment before payment."
    if application.application_status != "draft":
        return None
    return finalize_philsys_application(application, user, "submitted")
