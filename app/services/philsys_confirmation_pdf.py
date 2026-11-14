"""Watermarked demonstration confirmation PDF for PhilSys preparation. Not an official National ID."""

import secrets
from pathlib import Path

from flask import current_app

from app.services.application_service import field_map, read_details, write_details
from app.services.philsys_payment import payment_summary
from app.services.philsys_scheduling import appointment_for
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
    return f"DEMO-PHILSYS-{application.tracking_number}"


def absolute_confirmation_pdf(application):
    details = read_details(application)
    confirmation = details.get("confirmation") or {}
    relative = confirmation.get("pdf_path")
    if not relative:
        return None
    path = _upload_root() / relative
    return path if path.is_file() else None


def ensure_confirmation_pdf(application):
    """Create or refresh the demonstration PDF and store its path on the application."""
    details = read_details(application)
    confirmation = dict(details.get("confirmation") or {})

    answers = field_map(application)
    summary = payment_summary(application)
    appointment = appointment_for(application) or {}
    conf_id = confirmation.get("confirmation_id") or f"DEMO-PHILSYS-{secrets.token_hex(4).upper()}"
    full_name = summary.get("applicant_name") or " ".join(
        part
        for part in (
            answers.get("first_name"),
            answers.get("middle_name"),
            answers.get("last_name"),
        )
        if part
    ).strip() or application.tracking_number

    relative = confirmation.get("pdf_path") or (
        f"{application.application_id}/philsys-confirmation-{secrets.token_hex(4)}.pdf"
    )
    absolute = _upload_root() / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    watermark = "DEMONSTRATION ONLY – NOT AN OFFICIAL NATIONAL ID"
    write_receipt_pdf(
        absolute,
        {
            "confirmation_id": conf_id,
            "tracking_number": application.tracking_number,
            "subtitle": "PhilSys National ID preparation confirmation",
            "watermark": watermark,
            "footer": (
                "OneGov PH is an independent portfolio demonstration. "
                "This is not an official PhilSys registration or National ID."
            ),
            "details": (
                ("Applicant", full_name),
                ("Citizenship", answers.get("citizenship") or ""),
                ("Date of birth", answers.get("date_of_birth") or ""),
                ("Place of birth", answers.get("place_of_birth") or ""),
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
                    "label": "PhilSys registration fee",
                    "amount_display": summary.get("amount_display") or "₱0.00",
                },
            ),
            "total_label": "TOTAL",
            "amount": summary.get("amount_display") or "₱0.00",
            "payment_rows": (
                ("Payment required", summary.get("payment_required_label") or "No"),
                ("Payment status", summary.get("status_label") or "Not Applicable"),
            ),
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
    return absolute
