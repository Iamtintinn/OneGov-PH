"""Watermarked demonstration confirmation PDF for PhilSys preparation. Not an official National ID."""

import secrets
from pathlib import Path

from flask import current_app

from app.services.application_service import field_map, read_details, write_details
from app.services.philsys_delivery import (
    DELIVERY,
    PICKUP,
    delivery_address,
    delivery_for,
    fulfillment_method,
)
from app.services.philsys_payment import payment_summary
from app.services.philsys_requirements import bring_requirements_for
from app.services.philsys_scheduling import appointment_for
from app.services.receipt_pdf import write_receipt_pdf


def _upload_root():
    root = Path(current_app.root_path) / "instance" / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def confirmation_id_for(application):
    return application.tracking_number


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
    delivery = delivery_for(application)
    method = fulfillment_method(application)
    conf_id = application.tracking_number
    full_name = summary.get("applicant_name") or " ".join(
        part
        for part in (
            answers.get("first_name"),
            answers.get("middle_name"),
            answers.get("last_name"),
        )
        if part
    ).strip() or application.tracking_number
    bring = bring_requirements_for(answers.get("application_type"))
    has_bring_items = bool(bring.get("items"))

    relative = confirmation.get("pdf_path") or (
        f"{application.application_id}/philsys-confirmation-{secrets.token_hex(4)}.pdf"
    )
    absolute = _upload_root() / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    watermark = "DEMONSTRATION ONLY – NOT AN OFFICIAL NATIONAL ID"
    details_rows = (
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
    )
    if method == DELIVERY:
        details_rows = details_rows + (
            ("Fulfillment", "Home delivery"),
            ("Delivery address", delivery_address(delivery)),
            ("Recipient", (delivery or {}).get("recipient_name") or ""),
        )
    elif method == PICKUP:
        details_rows = details_rows + (
            ("Fulfillment", "Pickup at PSA PhilSys registration center"),
            ("Pickup location", (delivery or {}).get("pickup_location") or ""),
        )
    write_receipt_pdf(
        absolute,
        {
            "confirmation_id": conf_id,
            "show_tracking_number": False,
            "subtitle": "PhilSys National ID preparation confirmation",
            "watermark": watermark,
            "footer": (
                "OneGov PH is an independent portfolio demonstration. "
                "This is not an official PhilSys registration or National ID."
            ),
            "details": details_rows,
            "bring_title": "Bring to the PSA Registration Center (physical documents)" if has_bring_items else None,
            "bring_note": bring.get("note") if has_bring_items else None,
            "bring_items": bring.get("items") or (),
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
