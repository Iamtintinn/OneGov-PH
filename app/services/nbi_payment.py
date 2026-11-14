"""NBI Clearance payment. Regular online total is ₱160.00 (₱130 clearance + ₱30 convenience fee)."""

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
from app.services.nbi_requirements import is_nbi_new_application, requires_nbi_schedule
from app.services.nbi_scheduling import appointment_for
from app.services.passport_payment import METHOD_LABELS, ONLINE_METHODS, latest_payment
from app.services.tracking_service import add_event

CLEARANCE_FEE = Decimal("130.00")
CONVENIENCE_FEE = Decimal("30.00")
TOTAL_FEE = CLEARANCE_FEE + CONVENIENCE_FEE


def _now():
    return datetime.now().replace(microsecond=0)


def _payment_reference():
    for _ in range(5):
        reference = f"OGPH-NBI-{_now():%y%m%d}-{secrets.token_hex(3).upper()}"
        taken = db.session.scalar(
            db.select(Payment.payment_id).where(Payment.payment_reference == reference)
        )
        if taken is None:
            return reference
    raise RuntimeError("A payment reference could not be created.")


def _is_reviewed(application):
    return bool(read_details(application).get("nbi_reviewed"))


def demo_fee():
    return TOTAL_FEE


def _needs_appointment(application):
    return requires_nbi_schedule(field_map(application).get("application_type"))


def payment_summary(application):
    answers = field_map(application)
    amount = demo_fee()
    payment = latest_payment(application)
    appointment = appointment_for(application) if _needs_appointment(application) else None
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
    full_name = " ".join(
        part
        for part in (
            answers.get("first_name"),
            answers.get("middle_name"),
            answers.get("last_name"),
        )
        if part
    ).strip()
    return {
        "service_kind": "nbi",
        "application_type": answers.get("application_type") or "",
        "full_name": full_name,
        "purpose": answers.get("purpose") or "",
        "appointment": appointment,
        "amount": amount,
        "amount_display": f"₱{amount:,.2f}",
        "application_fee": CLEARANCE_FEE,
        "application_fee_display": f"₱{CLEARANCE_FEE:,.2f}",
        "application_fee_label": "Regular NBI Clearance",
        "processing_fee": CONVENIENCE_FEE,
        "processing_fee_display": f"₱{CONVENIENCE_FEE:,.2f}",
        "processing_fee_label": "Online payment convenience fee",
        "total_label": "Regular online application total",
        "payment": payment,
        "method_label": METHOD_LABELS.get(payment.payment_method) if payment else None,
        "status_label": status_label,
        "status_key": status_key,
        "provider_status": payment.provider_status if payment else None,
        "checkout_id": payment.provider_checkout_id if payment else None,
    }


def finalize_nbi_application(application, user, new_status):
    """Leave draft after NBI review, appointment, and payment are recorded."""
    values = field_map(application)
    spec = specification_for(application.service, values) or {}
    if missing_documents(application, spec):
        return "Upload every required document before you continue."
    if not _is_reviewed(application):
        return "Review your application before payment."
    if _needs_appointment(application) and appointment_for(application) is None:
        return "Select a demonstration appointment before payment."
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
            "NBI clearance request and payment were saved for assistance and monitoring. "
            "NBI has not received this as an official filing, and OneGov PH has not marked it approved or completed."
        ),
        "draft",
        now,
    )
    notice = spec.get("submit_notice")
    db.session.add(
        Notification(
            user_id=user.user_id,
            notification_title="NBI clearance request received",
            notification_message=(
                notice.format(reference=application.tracking_number)
                if notice
                else (
                    f"Your NBI clearance request {application.tracking_number} was submitted in OneGov PH for monitoring. "
                    "It is not an official NBI registration."
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
    if _needs_appointment(application) and appointment_for(application) is None:
        return "Select a demonstration appointment before payment."
    existing = latest_payment(application)
    if application.application_status != "draft" and existing is not None:
        return None

    amount = demo_fee()
    now = _now()
    online_only = not is_nbi_new_application(field_map(application).get("application_type"))
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
            f"Your simulated NBI clearance payment of ₱{amount:,.2f} was recorded as paid. "
            "No real payment was collected."
        )
    elif choice == "onsite":
        if online_only:
            return "Onsite payment is not available for this NBI application type. Choose an online payment method."
        method = "over_the_counter"
        status = "pending"
        app_status = "submitted"
        title = "Onsite payment selected"
        message = (
            f"You chose to pay ₱{amount:,.2f} onsite for this NBI clearance request. "
            "No real payment was collected."
        )
    else:
        return "Choose an online payment method." if online_only else "Choose pay online or pay onsite."

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
    return finalize_nbi_application(application, user, app_status)


def start_maya_checkout(application, user):
    """Create a pending Maya payment row and a sandbox checkout session."""
    if not _is_reviewed(application):
        return None, "Review your application before payment."
    if _needs_appointment(application) and appointment_for(application) is None:
        return None, "Select a demonstration appointment before payment."
    if application.application_status != "draft":
        return None, "This application is no longer awaiting payment."

    existing = latest_payment(application)
    if existing is not None and existing.payment_status == "paid":
        return None, "This application is already paid."

    amount = demo_fee()
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
            item_name="OneGov PH NBI clearance fee (sandbox)",
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
