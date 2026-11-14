"""Birth certificate demonstration payment. Total is ₱365.00."""

import secrets
from datetime import datetime
from decimal import Decimal

from sqlalchemy import update

from app import db
from app.models.application import Application
from app.models.notification import Notification
from app.models.payment import Payment
from app.services.application_forms import specification_for
from app.services.application_service import field_map, missing_documents, read_details
from app.services.maya_checkout import MayaCheckoutError, create_checkout
from app.services.passport_payment import METHOD_LABELS, ONLINE_METHODS, latest_payment
from app.services.tracking_service import add_event

PSA_DOCUMENT_FEE = Decimal("155.00")
PROCESSING_FEE = Decimal("160.00")
COURIER_FEE = Decimal("50.00")
TOTAL_FEE = PSA_DOCUMENT_FEE + PROCESSING_FEE + COURIER_FEE


def _now():
    return datetime.now().replace(microsecond=0)


def _payment_reference():
    for _ in range(5):
        reference = f"OGPH-BIRTH-{_now():%y%m%d}-{secrets.token_hex(3).upper()}"
        taken = db.session.scalar(
            db.select(Payment.payment_id).where(Payment.payment_reference == reference)
        )
        if taken is None:
            return reference
    raise RuntimeError("A payment reference could not be created.")


def _is_reviewed(application):
    return bool(read_details(application).get("birth_reviewed"))


def _copy_count(application):
    raw = (field_map(application).get("copies") or "1").strip()
    try:
        copies = int(raw)
    except ValueError:
        copies = 1
    return max(1, min(copies, 5))


def demo_fee(application=None):
    copies = _copy_count(application) if application is not None else 1
    return TOTAL_FEE * copies


def payment_summary(application):
    answers = field_map(application)
    copies = _copy_count(application)
    psa_fee = PSA_DOCUMENT_FEE * copies
    processing_fee = PROCESSING_FEE * copies
    courier_fee = COURIER_FEE * copies
    amount = demo_fee(application)
    payment = latest_payment(application)
    status_label = None
    status_key = None
    if payment:
        status_key = payment.payment_status
        if payment.payment_status == "paid":
            status_label = "Paid"
        elif payment.payment_status == "pending" and payment.payment_method == "over_the_counter":
            status_label = "Pending"
            status_key = "pending"
        elif payment.payment_status == "pending":
            status_label = "Processing"
            status_key = "processing"
        elif payment.payment_status == "failed":
            status_label = "Failed"
        elif payment.payment_status == "cancelled":
            status_label = "Cancelled"
        else:
            status_label = payment.payment_status.replace("_", " ").title()
    owner_name = " ".join(
        part
        for part in (
            answers.get("owner_first_name"),
            answers.get("owner_middle_name"),
            answers.get("owner_last_name"),
        )
        if part
    ).strip()
    def _label(name, unit):
        if copies > 1:
            return f"{name} ({copies} × ₱{unit:,.2f})"
        return name

    return {
        "service_kind": "birth",
        "application_type": answers.get("application_type") or "",
        "certificate_for": answers.get("certificate_for") or "",
        "owner_name": owner_name,
        "copies": copies,
        "copies_display": str(copies),
        "amount": amount,
        "amount_display": f"₱{amount:,.2f}",
        "application_fee": psa_fee,
        "application_fee_display": f"₱{psa_fee:,.2f}",
        "application_fee_label": _label("PSA Document Fee", PSA_DOCUMENT_FEE),
        "processing_fee": processing_fee,
        "processing_fee_display": f"₱{processing_fee:,.2f}",
        "processing_fee_label": _label("Processing, Convenience & Service Fees", PROCESSING_FEE),
        "courier_fee": courier_fee,
        "courier_fee_display": f"₱{courier_fee:,.2f}",
        "courier_fee_label": _label("Courier / Delivery Fee", COURIER_FEE),
        "total_label": "TOTAL" if copies == 1 else f"TOTAL ({copies} × ₱{TOTAL_FEE:,.2f})",
        "fee_lines": (
            {
                "label": _label("PSA Document Fee", PSA_DOCUMENT_FEE),
                "amount_display": f"₱{psa_fee:,.2f}",
            },
            {
                "label": _label("Processing, Convenience & Service Fees", PROCESSING_FEE),
                "amount_display": f"₱{processing_fee:,.2f}",
            },
            {
                "label": _label("Courier / Delivery Fee", COURIER_FEE),
                "amount_display": f"₱{courier_fee:,.2f}",
            },
        ),
        "payment": payment,
        "method_label": METHOD_LABELS.get(payment.payment_method) if payment else None,
        "status_label": status_label,
        "status_key": status_key,
        "provider_status": payment.provider_status if payment else None,
        "checkout_id": payment.provider_checkout_id if payment else None,
    }


def finalize_birth_application(application, user, new_status):
    """Leave draft after birth certificate review and payment are recorded."""
    values = field_map(application)
    spec = specification_for(application.service, values) or {}
    if missing_documents(application, spec):
        return "Upload every required document before you continue."
    if not _is_reviewed(application):
        return "Review your application before payment."
    if application.application_status != "draft":
        return None
    now = _now()
    updated = db.session.execute(
        update(Application)
        .where(
            Application.application_id == application.application_id,
            Application.applicant_id == user.user_id,
            Application.application_status == "draft",
        )
        .values(
            application_status=new_status,
            submission_date=now,
            last_updated=now,
        )
    )
    if updated.rowcount != 1:
        db.session.rollback()
        return None
    add_event(
        application,
        user.user_id,
        new_status,
        spec.get("submit_event")
        or (
            "Birth certificate request and payment were saved for assistance and tracking. "
            "PSA has not reviewed it, and OneGov PH has not marked it approved or completed."
        ),
        "draft",
        now,
    )
    notice = spec.get("submit_notice")
    db.session.add(
        Notification(
            user_id=user.user_id,
            notification_title="Birth certificate request received",
            notification_message=(
                notice.format(reference=application.tracking_number)
                if notice
                else (
                    f"Your Birth Certificate request {application.tracking_number} was submitted in OneGov PH. "
                    "It is not an official PSA filing."
                )
            ),
            notification_type="application",
            read_status="unread",
            created_date=now,
        )
    )
    db.session.commit()
    application.application_status = new_status
    application.submission_date = now
    application.last_updated = now
    return None


def record_demo_payment(application, user, choice, online_method=None):
    """Record onsite or non-Maya simulated online payment and finalize the draft."""
    if not _is_reviewed(application):
        return "Review your application before payment."
    existing = latest_payment(application)
    if application.application_status != "draft" and existing is not None:
        return None

    amount = demo_fee(application)
    now = _now()
    if choice == "online":
        method = str(online_method or "").strip()
        if method == "maya":
            return "Use Pay Now to open Maya Checkout sandbox."
        if method not in ONLINE_METHODS:
            return "Select an online payment method."
        status = "paid"
        app_status = "paid"
        title = "Demonstration payment successful"
        message = (
            f"Your simulated birth certificate payment of ₱{amount:,.2f} was recorded as paid. "
            "No real payment was collected."
        )
    elif choice == "onsite":
        return "Onsite payment is not available for birth certificate requests. Choose an online payment method."
    else:
        return "Choose an online payment method."

    if existing is not None:
        existing.amount = amount
        existing.payment_method = method
        existing.payment_status = status
        existing.transaction_date = now if status == "paid" else None
        existing.provider_checkout_id = None
        existing.provider_status = None
        if not str(existing.payment_reference).startswith(("DEMO-PAY-", "OGPH-")):
            existing.payment_reference = _payment_reference()
    else:
        db.session.add(
            Payment(
                application_id=application.application_id,
                amount=amount,
                payment_reference=_payment_reference(),
                payment_method=method,
                payment_status=status,
                transaction_date=now if status == "paid" else None,
            )
        )
    db.session.add(
        Notification(
            user_id=user.user_id,
            notification_title=title,
            notification_message=message,
            notification_type="payment",
            read_status="unread",
            created_date=now,
        )
    )
    db.session.commit()
    return finalize_birth_application(application, user, app_status)


def start_maya_checkout(application, user):
    """Create a pending Maya payment row and a sandbox checkout session."""
    if not _is_reviewed(application):
        return None, "Review your application before payment."
    if application.application_status != "draft":
        return None, "This application is no longer awaiting payment."

    existing = latest_payment(application)
    if existing is not None and existing.payment_status == "paid":
        return None, "This application is already paid."

    amount = demo_fee(application)
    now = _now()
    if existing is not None and existing.payment_method == "maya" and existing.payment_status == "pending":
        payment = existing
        payment.amount = amount
        if not payment.payment_reference:
            payment.payment_reference = _payment_reference()
    elif existing is not None and existing.payment_status in {"failed", "cancelled"}:
        payment = existing
        payment.amount = amount
        payment.payment_method = "maya"
        payment.payment_status = "pending"
        payment.transaction_date = None
        payment.provider_checkout_id = None
        payment.provider_status = None
        payment.payment_reference = _payment_reference()
    elif existing is None:
        payment = Payment(
            application_id=application.application_id,
            amount=amount,
            payment_reference=_payment_reference(),
            payment_method="maya",
            payment_status="pending",
            transaction_date=None,
        )
        db.session.add(payment)
    else:
        return None, "A payment record already exists for this application."

    db.session.flush()

    from app.services.maya_checkout import build_redirect_urls

    try:
        redirect_urls = build_redirect_urls(
            application_id=application.application_id,
            payment_reference=payment.payment_reference,
        )
    except MayaCheckoutError as exc:
        db.session.rollback()
        return None, str(exc)
    buyer = {
        "firstName": (user.first_name or "Citizen")[:100],
        "lastName": (user.last_name or "Applicant")[:100],
        "contact": {},
    }
    if user.email:
        buyer["contact"]["email"] = user.email[:100]
    if getattr(user, "contact_number", None):
        buyer["contact"]["phone"] = str(user.contact_number)[:40]

    try:
        checkout = create_checkout(
            amount=float(amount),
            request_reference_number=payment.payment_reference,
            redirect_urls=redirect_urls,
            buyer=buyer,
            item_name="OneGov PH birth certificate fee (sandbox)",
        )
    except MayaCheckoutError as exc:
        db.session.rollback()
        return None, str(exc)

    payment.provider_checkout_id = checkout["checkoutId"]
    payment.provider_status = "PENDING_PAYMENT"
    payment.payment_method = "maya"
    payment.payment_status = "pending"
    payment.transaction_date = None
    db.session.add(
        Notification(
            user_id=user.user_id,
            notification_title="Maya Checkout started",
            notification_message=(
                f"Sandbox Maya checkout was created for ₱{amount:,.2f} "
                f"(ref {payment.payment_reference}). Complete payment on Maya’s page."
            ),
            notification_type="payment",
            read_status="unread",
            created_date=now,
        )
    )
    db.session.commit()
    return checkout["redirectUrl"], None
