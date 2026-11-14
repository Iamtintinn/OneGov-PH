"""Watermarked demonstration confirmation PDF for NBI clearance monitoring. Not an official NBI document."""

import secrets
from pathlib import Path

from flask import current_app

from app.services.application_service import field_map, read_details, write_details
from app.services.nbi_payment import payment_summary
from app.services.nbi_requirements import bring_requirements_for, is_nbi_new_application
from app.services.nbi_scheduling import appointment_for
from app.services.passport_payment import METHOD_LABELS, latest_payment
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
    return f"DEMO-NBI-{application.tracking_number}"


def ensure_confirmation_pdf(application):
    """Create or refresh the demonstration PDF and store its path on the application."""
    details = read_details(application)
    confirmation = dict(details.get("confirmation") or {})

    answers = field_map(application)
    summary = payment_summary(application)
    payment = latest_payment(application)
    application_type = answers.get("application_type") or ""
    is_new = is_nbi_new_application(application_type)
    appointment = appointment_for(application) if is_new else {}
    appointment = appointment or {}
    bring = bring_requirements_for(application_type) if is_new else {"items": (), "note": None}
    conf_id = confirmation.get("confirmation_id") or f"DEMO-NBI-{secrets.token_hex(4).upper()}"
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
        f"{application.application_id}/nbi-confirmation-{secrets.token_hex(4)}.pdf"
    )
    absolute = _upload_root() / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    watermark = "DEMONSTRATION ONLY – NOT AN OFFICIAL NBI CLEARANCE"
    details_rows = (
        ("Applicant", full_name),
        ("Application type", application_type or summary.get("application_type") or ""),
        ("Complete address", answers.get("address") or ""),
        ("Purpose of clearance", answers.get("purpose") or ""),
        ("Contact number", answers.get("contact_number") or ""),
        ("Email", answers.get("email") or ""),
        (
            "Date submitted",
            application.submission_date.strftime("%d %b %Y, %I:%M %p")
            if application.submission_date
            else "",
        ),
    )
    if is_new and appointment:
        details_rows = details_rows + (
            ("Demonstration appointment", appointment.get("label") or ""),
            ("Appointment location", appointment.get("location_label") or ""),
            ("Appointment date", appointment.get("appointment_date") or ""),
            ("Appointment time", appointment.get("appointment_time") or ""),
        )
    write_receipt_pdf(
        absolute,
        {
            "confirmation_id": conf_id,
            "tracking_number": application.tracking_number,
            "subtitle": "NBI clearance request confirmation",
            "watermark": watermark,
            "footer": (
                "OneGov PH is an independent portfolio demonstration. "
                "This is not an official NBI clearance or NBI receipt."
            ),
            "details": details_rows,
            "bring_title": "Bring to the NBI Clearance Center (physical documents)" if is_new else None,
            "bring_note": bring.get("note") if is_new else None,
            "bring_items": bring.get("items") or () if is_new else (),
            "fee_lines": (
                {
                    "label": summary.get("application_fee_label") or "Regular NBI Clearance",
                    "amount_display": summary.get("application_fee_display") or "₱130.00",
                },
                {
                    "label": summary.get("processing_fee_label")
                    or "Online payment convenience fee",
                    "amount_display": summary.get("processing_fee_display") or "₱30.00",
                },
            ),
            "total_label": "TOTAL",
            "amount": summary.get("amount_display") or "₱160.00",
            "payment_rows": (
                (
                    "Payment method",
                    METHOD_LABELS.get(payment.payment_method)
                    if payment
                    else summary.get("method_label") or "",
                ),
                ("Payment status", summary.get("status_label") or ""),
                ("Payment reference", payment.payment_reference if payment else ""),
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
