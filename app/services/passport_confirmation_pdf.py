"""Watermarked demonstration confirmation PDF. Not an official DFA document."""

import secrets
from pathlib import Path

from flask import current_app

from app.services.application_service import field_map, read_details, write_details
from app.services.passport_payment import METHOD_LABELS, latest_payment, payment_summary
from app.services.passport_requirements import bring_requirements_for, normalize_passport_type
from app.services.passport_scheduling import appointment_for
from app.services.receipt_pdf import write_receipt_pdf


def _upload_root():
    root = Path(current_app.root_path) / "instance" / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def confirmation_id_for(application):
    details = read_details(application)
    confirmation = details.get("confirmation") or {}
    if confirmation.get("confirmation_id"):
        return confirmation["confirmation_id"]
    return f"DEMO-CONF-{application.tracking_number}"


def ensure_confirmation_pdf(application):
    """Create or refresh the demonstration PDF and store its path on the application."""
    details = read_details(application)
    confirmation = dict(details.get("confirmation") or {})

    answers = field_map(application)
    appointment = appointment_for(application) or {}
    summary = payment_summary(application)
    payment = latest_payment(application)
    application_type = normalize_passport_type(answers.get("application_type"))
    bring = bring_requirements_for(application_type)
    conf_id = confirmation.get("confirmation_id") or f"DEMO-CONF-{secrets.token_hex(4).upper()}"
    full_name = " ".join(
        part
        for part in (
            answers.get("first_name"),
            answers.get("middle_name"),
            answers.get("last_name"),
        )
        if part
    ).strip() or application.tracking_number

    relative = confirmation.get("pdf_path") or (
        f"{application.application_id}/passport-confirmation-{secrets.token_hex(4)}.pdf"
    )
    absolute = _upload_root() / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    watermark = "DEMONSTRATION ONLY – NOT AN OFFICIAL DFA APPOINTMENT CONFIRMATION"
    write_receipt_pdf(
        absolute,
        {
            "confirmation_id": conf_id,
            "tracking_number": application.tracking_number,
            "subtitle": "Passport demonstration confirmation",
            "watermark": watermark,
            "footer": (
                "OneGov PH is an independent portfolio demonstration and is not affiliated with DFA. "
                "This is not an official DFA appointment confirmation. Confirm current DFA documentary requirements before your visit."
            ),
            "details": (
                ("Applicant", full_name),
                ("Application type", application_type or answers.get("application_type") or ""),
                ("Appointment location", appointment.get("location_label") or ""),
                ("Appointment date", appointment.get("appointment_date") or ""),
                ("Appointment time", appointment.get("appointment_time") or ""),
                (
                    "Date submitted",
                    application.submission_date.strftime("%d %b %Y, %I:%M %p")
                    if application.submission_date
                    else "",
                ),
            ),
            "fee_lines": (
                {
                    "label": "Demonstration passport fee",
                    "amount_display": summary.get("amount_display") or "₱1,150.00",
                },
            ),
            "total_label": "TOTAL",
            "amount": summary.get("amount_display") or "₱1,150.00",
            "payment_rows": (
                (
                    "Payment method",
                    METHOD_LABELS.get(payment.payment_method, "") if payment else "",
                ),
                ("Payment status", summary.get("status_label") or "Not recorded"),
                ("Payment reference", payment.payment_reference if payment else ""),
            ),
            "bring_title": "Bring to your appointment (physical documents)",
            "bring_note": bring.get("note"),
            "bring_items": bring.get("items") or (),
        },
    )
    confirmation.update(
        {
            "confirmation_id": conf_id,
            "pdf_path": relative,
            "watermark": watermark,
        }
    )
    details["confirmation"] = confirmation
    write_details(application, details)
    return confirmation


def absolute_confirmation_pdf(application):
    details = read_details(application)
    relative = (details.get("confirmation") or {}).get("pdf_path")
    if not relative:
        return None
    path = _upload_root() / relative
    return path if path.is_file() else None
