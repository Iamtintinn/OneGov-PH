"""Watermarked demonstration confirmation PDF for Senior Citizen ID. Not an official OSCA document."""

import secrets
from pathlib import Path

from flask import current_app

from app.services.application_service import field_map, read_details, write_details
from app.services.receipt_pdf import write_receipt_pdf
from app.services.senior_payment import payment_summary
from app.services.senior_requirements import bring_requirements_for
from app.services.senior_scheduling import appointment_for


def _upload_root():
    root = Path(current_app.root_path) / "instance" / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def confirmation_id_for(application):
    details = read_details(application)
    confirmation = details.get("confirmation") or {}
    if confirmation.get("confirmation_id"):
        return confirmation["confirmation_id"]
    return f"DEMO-OSCA-{application.tracking_number}"


def ensure_confirmation_pdf(application):
    """Create or refresh the demonstration PDF and store its path on the application."""
    details = read_details(application)
    confirmation = dict(details.get("confirmation") or {})

    answers = field_map(application)
    summary = payment_summary(application)
    conf_id = confirmation.get("confirmation_id") or f"DEMO-OSCA-{secrets.token_hex(4).upper()}"
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
        f"{application.application_id}/senior-confirmation-{secrets.token_hex(4)}.pdf"
    )
    absolute = _upload_root() / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    watermark = "DEMONSTRATION ONLY – NOT AN OFFICIAL SENIOR CITIZEN ID"
    bring = bring_requirements_for(answers.get("application_type"))
    appointment = appointment_for(application) or {}
    appointment_rows = ()
    if appointment:
        appointment_rows = (
            ("Demonstration appointment", appointment.get("label") or ""),
            ("Location", appointment.get("location_label") or ""),
            ("Date", appointment.get("appointment_date") or ""),
            ("Time", appointment.get("appointment_time") or ""),
        )
    write_receipt_pdf(
        absolute,
        {
            "confirmation_id": conf_id,
            "tracking_number": application.tracking_number,
            "subtitle": "Senior Citizen ID request confirmation",
            "watermark": watermark,
            "footer": (
                "OneGov PH is an independent portfolio demonstration. "
                "This is not an official Senior Citizen ID or OSCA receipt."
            ),
            "details": (
                ("Applicant", full_name),
                ("Barangay", answers.get("barangay") or summary.get("barangay") or ""),
                ("City / municipality", answers.get("city") or summary.get("city") or ""),
                ("Province", answers.get("province") or ""),
                ("Complete address", answers.get("address") or ""),
                (
                    "Application type",
                    answers.get("application_type") or summary.get("application_type") or "",
                ),
                ("Citizenship status", answers.get("citizenship_status") or ""),
                ("Representative", answers.get("representative") or "No"),
                ("ID transfer", answers.get("id_transfer") or "No"),
                ("Contact number", answers.get("contact_number") or ""),
                ("Email", answers.get("email") or ""),
                (
                    "Date submitted",
                    application.submission_date.strftime("%d %b %Y, %I:%M %p")
                    if application.submission_date
                    else "",
                ),
            )
            + appointment_rows,
            "fee_lines": (
                {
                    "label": "New application fee",
                    "amount_display": summary.get("amount_display") or "₱0.00",
                },
            ),
            "total_label": "TOTAL",
            "amount": summary.get("amount_display") or "₱0.00",
            "payment_rows": (
                ("Payment required", summary.get("payment_required_label") or "No"),
                ("Payment status", summary.get("status_label") or "Not Applicable"),
            ),
            "bring_title": "Bring to the OSCA office (physical documents)",
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
