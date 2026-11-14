"""Shared OneGov PH demonstration receipt PDF layout."""

import io


def wrap_text(pdf, text, font, size, max_width):
    words = str(text or "—").split()
    if not words:
        return ["—"]
    lines = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if pdf.stringWidth(trial, font, size) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or ["—"]


def qr_image(payload):
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


def write_receipt_pdf(path, data):
    """
    Write a demonstration receipt PDF.

    Expected keys:
      subtitle, watermark, footer, confirmation_id, tracking_number
      details: list of (label, value)
      fee_lines: optional list of {label, amount_display}
      total_label, amount
      payment_rows: optional list of (label, value) under fees
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    qr = qr_image(data["confirmation_id"])
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 20 * mm
    right = width - 20 * mm
    content_width = right - left

    # Watermark
    pdf.setFillColorRGB(0.93, 0.93, 0.94)
    pdf.saveState()
    pdf.translate(width / 2, height / 2)
    pdf.rotate(38)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawCentredString(0, 0, data.get("watermark") or "DEMONSTRATION ONLY")
    pdf.restoreState()

    # Header
    pdf.setFillColorRGB(0.09, 0.2, 0.34)
    pdf.rect(0, height - 36 * mm, width, 36 * mm, fill=1, stroke=0)
    pdf.setFillColorRGB(0.47, 0.12, 0.23)
    pdf.rect(0, height - 38 * mm, width, 2 * mm, fill=1, stroke=0)

    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(left, height - 18 * mm, "OneGov PH")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, height - 26 * mm, data.get("subtitle") or "Request confirmation")

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawRightString(right, height - 18 * mm, "Confirmation")
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(right, height - 26 * mm, data.get("confirmation_id") or "—")
    pdf.setFont("Helvetica", 8)
    pdf.drawRightString(right, height - 32 * mm, data.get("tracking_number") or "—")

    y = height - 50 * mm

    def section_title(title):
        nonlocal y
        pdf.setFillColorRGB(0.09, 0.2, 0.34)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(left, y, title)
        y -= 2.2 * mm
        pdf.setStrokeColorRGB(0.88, 0.9, 0.93)
        pdf.setLineWidth(0.8)
        pdf.line(left, y, right, y)
        y -= 6 * mm

    def detail_row(label, value):
        nonlocal y
        label_width = 48 * mm
        value_width = content_width - label_width - 2 * mm
        value_lines = wrap_text(pdf, value, "Helvetica", 9.5, value_width)
        pdf.setFillColorRGB(0.42, 0.48, 0.55)
        pdf.setFont("Helvetica", 8)
        pdf.drawString(left, y, str(label or "").upper())
        pdf.setFillColorRGB(0.12, 0.16, 0.22)
        pdf.setFont("Helvetica", 9.5)
        text_y = y
        for line in value_lines:
            pdf.drawString(left + label_width, text_y, line)
            text_y -= 4.3 * mm
        y = min(y - 6.8 * mm, text_y - 0.8 * mm)

    section_title("Request details")
    for label, value in data.get("details") or ():
        detail_row(label, value)

    y -= 2 * mm
    section_title("Payment summary")

    fee_lines = list(data.get("fee_lines") or ())
    amount_x = right
    label_max = content_width - 40 * mm

    if fee_lines:
        for line in fee_lines:
            label_lines = wrap_text(pdf, line.get("label") or "", "Helvetica", 9, label_max)
            pdf.setFillColorRGB(0.18, 0.22, 0.28)
            pdf.setFont("Helvetica", 9)
            text_y = y
            for part in label_lines:
                pdf.drawString(left, text_y, part)
                text_y -= 3.7 * mm
            pdf.setFont("Helvetica-Bold", 9.5)
            pdf.drawRightString(amount_x, y, str(line.get("amount_display") or "—"))
            y = min(y - 7.2 * mm, text_y - 0.6 * mm)

        y -= 1 * mm
        pdf.setStrokeColorRGB(0.09, 0.2, 0.34)
        pdf.setLineWidth(1)
        pdf.line(left, y + 3.5 * mm, right, y + 3.5 * mm)

        pdf.setFillColorRGB(0.09, 0.2, 0.34)
        pdf.setFont("Helvetica-Bold", 10)
        total_label = str(data.get("total_label") or "TOTAL")
        total_lines = wrap_text(pdf, total_label, "Helvetica-Bold", 9.5, label_max)
        pdf.drawString(left, y, total_lines[0])
        pdf.drawRightString(amount_x, y, str(data.get("amount") or "—"))
        y -= 9 * mm
    else:
        detail_row("Amount", data.get("amount") or "—")

    for label, value in data.get("payment_rows") or ():
        cleaned = str(value or "").replace(" (demo)", "").replace("(demo)", "").strip()
        detail_row(label, cleaned)

    bring_items = list(data.get("bring_items") or ())
    if bring_items:
        if y < 55 * mm:
            pdf.showPage()
            y = height - 25 * mm
        y -= 2 * mm
        section_title(data.get("bring_title") or "Bring to your appointment")
        if data.get("bring_note"):
            note_lines = wrap_text(pdf, data.get("bring_note"), "Helvetica-Oblique", 8.5, content_width)
            pdf.setFillColorRGB(0.47, 0.12, 0.23)
            pdf.setFont("Helvetica-Oblique", 8.5)
            for line in note_lines:
                if y < 28 * mm:
                    pdf.showPage()
                    y = height - 25 * mm
                pdf.drawString(left, y, line)
                y -= 4 * mm
            y -= 1.5 * mm
        pdf.setFillColorRGB(0.12, 0.16, 0.22)
        pdf.setFont("Helvetica", 9)
        for index, item in enumerate(bring_items, start=1):
            item_lines = wrap_text(pdf, f"{index}. {item}", "Helvetica", 9, content_width - 2 * mm)
            for line in item_lines:
                if y < 28 * mm:
                    pdf.showPage()
                    y = height - 25 * mm
                    pdf.setFillColorRGB(0.12, 0.16, 0.22)
                    pdf.setFont("Helvetica", 9)
                pdf.drawString(left, y, line)
                y -= 4.2 * mm
            y -= 0.8 * mm

    if qr is not None:
        pdf.drawImage(qr, right - 30 * mm, 22 * mm, width=28 * mm, height=28 * mm, mask="auto")
        pdf.setFillColorRGB(0.35, 0.4, 0.48)
        pdf.setFont("Helvetica", 7)
        pdf.drawCentredString(right - 16 * mm, 18 * mm, "Demo QR")

    pdf.setFillColorRGB(0.4, 0.45, 0.52)
    pdf.setFont("Helvetica", 7.5)
    footer_width = content_width - (36 * mm if qr is not None else 0)
    footer_lines = wrap_text(pdf, data.get("footer") or "", "Helvetica", 7.5, footer_width)
    footer_y = 14 * mm
    for part in footer_lines:
        pdf.drawString(left, footer_y, part)
        footer_y -= 3.2 * mm

    pdf.showPage()
    pdf.save()
    path.write_bytes(buffer.getvalue())
