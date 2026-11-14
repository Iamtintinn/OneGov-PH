"""Watermarked demonstration confirmation PDF for CENOMAR. Not an official PSA document."""

import secrets
from pathlib import Path

from flask import current_app

from app.services.application_service import field_map, read_details, write_details
from app.services.cenomar_payment import payment_summary
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
    return f"DEMO-CENOMAR-{application.tracking_number}"


def ensure_confirmation_pdf(application):
    """Create or refresh the demonstration PDF and store its path on the application."""
    details = read_details(application)
    confirmation = dict(details.get("confirmation") or {})

    answers = field_map(application)
    summary = payment_summary(application)
    payment = latest_payment(application)
    conf_id = confirmation.get("confirmation_id") or f"DEMO-CENOMAR-{secrets.token_hex(4).upper()}"
    owner = summary.get("owner_name") or summary.get("applicant_name") or " ".join(
        part
        for part in (
            answers.get("owner_first_name"),
            answers.get("owner_middle_name"),
            answers.get("owner_last_name"),
        )
        if part
    ).strip() or application.tracking_number
    requester = summary.get("requester_name") or " ".join(
        part
        for part in (
            answers.get("first_name"),
            answers.get("middle_name"),
            answers.get("last_name"),
        )
        if part
    ).strip()

    relative = confirmation.get("pdf_path") or (
        f"{application.application_id}/cenomar-confirmation-{secrets.token_hex(4)}.pdf"
    )
    absolute = _upload_root() / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    watermark = "DEMONSTRATION ONLY – NOT AN OFFICIAL PSA CENOMAR"
    fee_lines = list(summary.get("fee_lines") or ())
    write_receipt_pdf(
        absolute,
        {
            "confirmation_id": conf_id,
            "tracking_number": application.tracking_number,
            "subtitle": "CENOMAR request confirmation",
            "watermark": watermark,
            "footer": (
                "OneGov PH is an independent portfolio demonstration. "
                "This is not an official PSA CENOMAR or receipt."
            ),
            "details": (
                ("Requester", requester),
                ("Certificate owner", owner),
                ("Who is named", answers.get("certificate_for") or ""),
                ("Date of birth", answers.get("owner_birth_date") or ""),
                ("Place of birth", answers.get("place_of_birth") or ""),
                ("Civil status", answers.get("owner_civil_status") or ""),
                ("Copies", summary.get("copies_display") or answers.get("copies") or "1"),
                ("Purpose", summary.get("purpose") or ""),
                (
                    "Date submitted",
                    application.submission_date.strftime("%d %b %Y, %I:%M %p")
                    if application.submission_date
                    else "",
                ),
            ),
            "fee_lines": fee_lines,
            "total_label": summary.get("total_label") or "TOTAL",
            "amount": summary.get("amount_display") or "₱365.00",
            "payment_rows": (
                (
                    "Payment method",
                    METHOD_LABELS.get(payment.payment_method, "") if payment else "",
                ),
                ("Payment status", summary.get("status_label") or "Not recorded"),
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
