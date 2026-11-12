"""Watermarked demonstration confirmation PDF. Not an official DFA document."""

import io
import secrets
from pathlib import Path

from flask import current_app

from app.services.application_service import field_map, read_details, write_details
from app.services.passport_payment import METHOD_LABELS, latest_payment, payment_summary
from app.services.passport_scheduling import appointment_for


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
    """Create the demonstration PDF once and store its path on the application."""
    details = read_details(application)
    confirmation = dict(details.get("confirmation") or {})
    if confirmation.get("pdf_path"):
        path = _upload_root() / confirmation["pdf_path"]
        if path.is_file():
            return confirmation

    answers = field_map(application)
    appointment = appointment_for(application) or {}
    summary = payment_summary(application)
    payment = latest_payment(application)
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

    folder = _upload_root() / str(application.application_id)
    folder.mkdir(parents=True, exist_ok=True)
    relative = f"{application.application_id}/passport-confirmation-{secrets.token_hex(4)}.pdf"
    absolute = _upload_root() / relative
    _write_pdf(
        absolute,
        {
            "full_name": full_name,
            "confirmation_id": conf_id,
            "tracking_number": application.tracking_number,
            "application_type": answers.get("application_type") or "",
            "location": appointment.get("location_label") or "",
            "date": appointment.get("appointment_date") or "",
            "time": appointment.get("appointment_time") or "",
            "payment_reference": payment.payment_reference if payment else "",
            "payment_status": summary.get("status_label") or "Not recorded",
            "payment_method": METHOD_LABELS.get(payment.payment_method, "") if payment else "",
            "amount": summary.get("amount_display") or "",
        },
    )
    confirmation.update(
        {
            "confirmation_id": conf_id,
            "pdf_path": relative,
            "watermark": "DEMONSTRATION ONLY – NOT AN OFFICIAL DFA APPOINTMENT CONFIRMATION",
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


def _write_pdf(path, data):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    qr_image = _qr_image(data["confirmation_id"])
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFillColorRGB(0.9, 0.9, 0.9)
    pdf.saveState()
    pdf.translate(width / 2, height / 2)
    pdf.rotate(45)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(0, 0, "DEMONSTRATION ONLY – NOT AN OFFICIAL DFA APPOINTMENT CONFIRMATION")
    pdf.restoreState()

    pdf.setFillColorRGB(0.09, 0.2, 0.34)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(25 * mm, height - 25 * mm, "OneGov PH")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(25 * mm, height - 32 * mm, "Passport demonstration confirmation")

    pdf.setFillColorRGB(0.47, 0.12, 0.23)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(
        25 * mm,
        height - 42 * mm,
        "DEMONSTRATION ONLY – NOT AN OFFICIAL DFA APPOINTMENT CONFIRMATION",
    )

    pdf.setFillColorRGB(0.15, 0.2, 0.27)
    lines = [
        ("Applicant", data["full_name"]),
        ("Confirmation ID", data["confirmation_id"]),
        ("Application reference", data["tracking_number"]),
        ("Application type", data["application_type"]),
        ("Appointment location", data["location"]),
        ("Appointment date", data["date"]),
        ("Appointment time", data["time"]),
        ("Payment reference", data["payment_reference"]),
        ("Payment method", data["payment_method"]),
        ("Payment status", data["payment_status"]),
        ("Demonstration fee", data["amount"]),
    ]
    y = height - 58 * mm
    for label, value in lines:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(25 * mm, y, label)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(75 * mm, y, str(value or "—"))
        y -= 8 * mm

    if qr_image is not None:
        pdf.drawImage(qr_image, width - 55 * mm, 30 * mm, width=30 * mm, height=30 * mm, mask="auto")
        pdf.setFont("Helvetica", 8)
        pdf.drawCentredString(width - 40 * mm, 25 * mm, "Demo confirmation QR")

    pdf.setFont("Helvetica", 8)
    pdf.drawString(
        25 * mm,
        18 * mm,
        "OneGov PH is an independent portfolio demonstration and is not affiliated with DFA.",
    )
    pdf.showPage()
    pdf.save()
    path.write_bytes(buffer.getvalue())


def _qr_image(payload):
    try:
        import qrcode
        from reportlab.lib.utils import ImageReader
    except ImportError:
        return None
    image = qrcode.make(payload)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    stream.seek(0)
    return ImageReader(stream)
