"""Watermarked demonstration confirmation PDF for barangay clearance / residency. Not an official local document."""

import secrets
from pathlib import Path

from flask import current_app

from app.services.application_forms import specification_for
from app.services.application_service import field_map, read_details, write_details
from app.services.barangay_payment import payment_summary
from app.services.passport_payment import METHOD_LABELS, latest_payment
from app.services.receipt_pdf import write_receipt_pdf


def _upload_root():
    root = Path(current_app.root_path) / "instance" / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _kind(application):
    return (specification_for(application.service, field_map(application)) or {}).get("kind") or "barangay"


def confirmation_id_for(application):
    details = read_details(application)
    confirmation = details.get("confirmation") or {}
    if confirmation.get("confirmation_id"):
        return confirmation["confirmation_id"]
    prefix = "DEMO-RES" if _kind(application) == "residency" else "DEMO-BRGY"
    return f"{prefix}-{application.tracking_number}"


def ensure_confirmation_pdf(application):
    """Create or refresh the demonstration PDF and store its path on the application."""
    details = read_details(application)
    confirmation = dict(details.get("confirmation") or {})

    kind = _kind(application)
    answers = field_map(application)
    summary = payment_summary(application)
    payment = latest_payment(application)
    prefix = "DEMO-RES" if kind == "residency" else "DEMO-BRGY"
    conf_id = confirmation.get("confirmation_id") or f"{prefix}-{secrets.token_hex(4).upper()}"
    full_name = " ".join(
        part
        for part in (
            answers.get("first_name"),
            answers.get("middle_name"),
            answers.get("last_name"),
        )
        if part
    ).strip() or application.tracking_number

    file_slug = "residency-confirmation" if kind == "residency" else "barangay-confirmation"
    relative = confirmation.get("pdf_path") or (
        f"{application.application_id}/{file_slug}-{secrets.token_hex(4)}.pdf"
    )
    absolute = _upload_root() / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    watermark = (
        "DEMONSTRATION ONLY – NOT AN OFFICIAL CERTIFICATE OF RESIDENCY"
        if kind == "residency"
        else "DEMONSTRATION ONLY – NOT AN OFFICIAL BARANGAY CLEARANCE"
    )
    years_label = "Length of residency" if kind == "residency" else "Years residing"
    years_value = answers.get("years_residing") or answers.get("length_of_residency") or ""
    purpose_value = (
        answers.get("application_type")
        or answers.get("purpose")
        or summary.get("purpose")
        or ""
    )
    appointment_rows = ()
    if kind in {"barangay", "residency"}:
        from app.services.barangay_scheduling import appointment_for

        appointment = appointment_for(application) or {}
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
            "subtitle": (
                "Certificate of residency request confirmation"
                if kind == "residency"
                else "Barangay clearance request confirmation"
            ),
            "watermark": watermark,
            "footer": (
                "OneGov PH is an independent portfolio demonstration. This is not an official certificate of residency."
                if kind == "residency"
                else "OneGov PH is an independent portfolio demonstration. This is not an official barangay clearance."
            ),
            "details": (
                ("Applicant", full_name),
                ("Barangay", answers.get("barangay") or summary.get("barangay") or ""),
                ("City / municipality", answers.get("city") or summary.get("city") or ""),
                ("Complete address", answers.get("address") or ""),
                (years_label, years_value),
                ("Application type / purpose", purpose_value),
                ("Additional notes", answers.get("purpose_notes") or ""),
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
                    "label": "Processing fee",
                    "amount_display": summary.get("amount_display") or "₱50.00",
                },
            ),
            "total_label": "TOTAL",
            "amount": summary.get("amount_display") or "₱50.00",
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
