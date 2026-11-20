"""Watermarked demonstration confirmation PDF for SSS assistance. Not an official SSS registration or SS Number."""

import secrets
from pathlib import Path

from flask import current_app

from app.services.application_service import field_map, read_details, write_details
from app.services.receipt_pdf import write_receipt_pdf
from app.services.sss_payment import payment_summary
from app.services.sss_requirements import bring_requirements_for
from app.services.sss_scheduling import appointment_for


def _upload_root():
    root = Path(current_app.root_path) / "instance" / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def confirmation_id_for(application):
    return application.tracking_number


def ensure_confirmation_pdf(application):
    """Create or refresh the demonstration PDF and store its path on the application."""
    details = read_details(application)
    confirmation = dict(details.get("confirmation") or {})

    answers = field_map(application)
    summary = payment_summary(application)
    bring = bring_requirements_for(answers.get("application_type"))
    bring_items = list(bring.get("items") or ())
    appointment = appointment_for(application)
    bring_lead = None
    if bring_items and appointment:
        location_label = (appointment.get("location_label") or "").strip()
        address = (appointment.get("address") or "").strip()
        place = " — ".join(part for part in (location_label, address) if part)
        if place:
            when = " ".join(
                part
                for part in (
                    (appointment.get("appointment_date") or "").strip(),
                    (appointment.get("appointment_time") or "").strip(),
                )
                if part
            ).strip()
            bring_lead = f"Appointment location (demonstration): {place}"
            if when:
                bring_lead = f"{bring_lead} on {when}"
    has_bring_items = bool(bring_items or bring_lead)
    conf_id = application.tracking_number
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
        f"{application.application_id}/sss-confirmation-{secrets.token_hex(4)}.pdf"
    )
    absolute = _upload_root() / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    watermark = "DEMONSTRATION ONLY – NOT AN OFFICIAL SS NUMBER"
    write_receipt_pdf(
        absolute,
        {
            "confirmation_id": conf_id,
            "show_tracking_number": False,
            "subtitle": "SSS assistance confirmation",
            "watermark": watermark,
            "footer": (
                "OneGov PH is an independent portfolio demonstration. "
                "This is not an official SSS registration, receipt, or SS Number."
            ),
            "details": (
                ("Applicant", full_name),
                ("Application type", answers.get("application_type") or ""),
                ("Date of birth", answers.get("date_of_birth") or ""),
                ("Sex", answers.get("sex") or ""),
                ("Civil status", answers.get("civil_status") or ""),
                ("Complete address", answers.get("address") or answers.get("complete_address") or ""),
                ("Primary ID available", answers.get("has_primary_id") or ""),
                ("Contact number", answers.get("contact_number") or answers.get("mobile_number") or ""),
                ("Email", answers.get("email") or ""),
                (
                    "Date submitted",
                    application.submission_date.strftime("%d %b %Y, %I:%M %p")
                    if application.submission_date
                    else "",
                ),
            ),
            "bring_title": "Requirements and information to prepare" if has_bring_items else None,
            "bring_note": bring.get("note") if has_bring_items else None,
            "bring_lead": bring_lead,
            "bring_items": tuple(bring_items),
            "fee_lines": (
                {
                    "label": "SSS processing fee",
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
    return confirmation


def absolute_confirmation_pdf(application):
    details = read_details(application)
    relative = (details.get("confirmation") or {}).get("pdf_path")
    if not relative:
        return None
    path = _upload_root() / relative
    return path if path.is_file() else None
