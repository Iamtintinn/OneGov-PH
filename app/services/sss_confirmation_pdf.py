"""Watermarked demonstration confirmation PDF for SSS assistance. Not an official SSS registration or SS Number."""

import secrets
from pathlib import Path

from flask import current_app

from app.services.application_service import field_map, read_details, write_details
from app.services.receipt_pdf import write_receipt_pdf
from app.services.sss_payment import payment_summary


def _upload_root():
    root = Path(current_app.root_path) / "instance" / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def confirmation_id_for(application):
    details = read_details(application)
    confirmation = details.get("confirmation") or {}
    if confirmation.get("confirmation_id"):
        return confirmation["confirmation_id"]
    return f"DEMO-SSS-{application.tracking_number}"


def ensure_confirmation_pdf(application):
    """Create or refresh the demonstration PDF and store its path on the application."""
    details = read_details(application)
    confirmation = dict(details.get("confirmation") or {})

    answers = field_map(application)
    summary = payment_summary(application)
    conf_id = confirmation.get("confirmation_id") or f"DEMO-SSS-{secrets.token_hex(4).upper()}"
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
            "tracking_number": application.tracking_number,
            "subtitle": "SSS assistance confirmation",
            "watermark": watermark,
            "footer": (
                "OneGov PH is an independent portfolio demonstration. "
                "This is not an official SSS registration, receipt, or SS Number."
            ),
            "details": (
                ("Applicant", full_name),
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
