"""Passport payment: Maya Checkout sandbox for online Maya, demo onsite/other methods."""

import secrets
from datetime import datetime

from flask import url_for
from sqlalchemy import update

from app import db
from app.models.application import Application
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.user import User
from app.services.application_forms import specification_for
from app.services.application_service import field_map, missing_documents
from app.services.maya_checkout import (
    MayaCheckoutError,
    create_checkout,
    map_maya_status,
    payment_status_from_payload,
    retrieve_payment_by_id,
    retrieve_payment_by_rrn,
)
from app.services.passport_scheduling import appointment_for, demo_fee
from app.services.tracking_service import add_event

ONLINE_METHODS = ("gcash", "maya", "online_banking")
METHOD_LABELS = {
    "gcash": "GCash",
    "maya": "Maya",
    "online_banking": "Online banking",
    "over_the_counter": "Pay onsite (demo)",
}


def _now():
    return datetime.now().replace(microsecond=0)


def _payment_reference():
    """Maya requestReferenceNumber max length is 36."""
    for _ in range(5):
        reference = f"OGPH-{_now():%y%m%d}-{secrets.token_hex(4).upper()}"
        taken = db.session.scalar(
            db.select(Payment.payment_id).where(Payment.payment_reference == reference)
        )
        if taken is None:
            return reference
    raise RuntimeError("A payment reference could not be created.")


def latest_payment(application):
    if not application.payments:
        return None
    return max(application.payments, key=lambda payment: payment.payment_id)


def payment_summary(application):
    answers = field_map(application)
    appointment = appointment_for(application)
    amount = demo_fee(answers.get("application_type"))
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
    processing_fee = 0
    return {
        "application_type": answers.get("application_type") or "",
        "appointment": appointment,
        "amount": amount,
        "amount_display": f"₱{amount:,.2f}",
        "application_fee": amount,
        "application_fee_display": f"₱{amount:,.2f}",
        "processing_fee": processing_fee,
        "processing_fee_display": f"₱{processing_fee:,.2f}",
        "payment": payment,
        "method_label": METHOD_LABELS.get(payment.payment_method) if payment else None,
        "status_label": status_label,
        "status_key": status_key,
        "provider_status": payment.provider_status if payment else None,
        "checkout_id": payment.provider_checkout_id if payment else None,
    }


def finalize_passport_application(application, user, new_status):
    """Leave draft after appointment and payment are recorded."""
    values = field_map(application)
    spec = specification_for(application.service, values)
    if missing_documents(application, spec):
        return "Upload every required document before you continue."
    if appointment_for(application) is None:
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
            "Passport demonstration appointment and payment were saved. "
            "This is not an official DFA filing."
        ),
        "draft",
        now,
    )
    notice = spec.get("submit_notice")
    db.session.add(
        Notification(
            user_id=user.user_id,
            notification_title="Appointment confirmed (demo)",
            notification_message=(
                notice.format(reference=application.tracking_number)
                if notice
                else (
                    f"Your passport demonstration request {application.tracking_number} was saved. "
                    "This is not an official DFA appointment."
                )
            ),
            notification_type="appointment",
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
    """
    Record onsite or non-Maya simulated online payment and finalize the draft.
    Maya online payments use start_maya_checkout instead.
    """
    if appointment_for(application) is None:
        return "Select a demonstration appointment before payment."
    existing = latest_payment(application)
    if application.application_status != "draft" and existing is not None:
        return None

    amount = demo_fee(field_map(application).get("application_type"))
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
            f"Your simulated passport payment of ₱{amount:,.2f} was recorded as paid. "
            "No real payment was collected."
        )
    elif choice == "onsite":
        method = "over_the_counter"
        status = "pending"
        app_status = "scheduled"
        title = "Onsite payment selected"
        message = (
            f"You chose to pay ₱{amount:,.2f} onsite for this passport demonstration. "
            "No real payment was collected."
        )
    else:
        return "Choose pay online or pay onsite."

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
    return finalize_passport_application(application, user, app_status)


def start_maya_checkout(application, user):
    """
    Create a pending Maya payment row and a sandbox checkout session.
    Returns (redirect_url, error_message).
    """
    if appointment_for(application) is None:
        return None, "Select a demonstration appointment before payment."
    if application.application_status != "draft":
        return None, "This application is no longer awaiting payment."

    existing = latest_payment(application)
    if existing is not None and existing.payment_status == "paid":
        return None, "This application is already paid."

    amount = demo_fee(field_map(application).get("application_type"))
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

    redirect_urls = {
        "success": url_for(
            "citizen.apply_maya_result",
            application_id=application.application_id,
            outcome="success",
            _external=True,
        ),
        "failure": url_for(
            "citizen.apply_maya_result",
            application_id=application.application_id,
            outcome="failure",
            _external=True,
        ),
        "cancel": url_for(
            "citizen.apply_maya_result",
            application_id=application.application_id,
            outcome="cancel",
            _external=True,
        ),
    }
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
            item_name="OneGov PH passport application fee (sandbox)",
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


def _apply_verified_status(payment, application, local_status, maya_status, source):
    """
    Update payment from a server-side Maya verification.
    Idempotent: paid stays paid; failed/cancelled do not overwrite paid.
    """
    now = _now()
    payment.provider_status = maya_status or payment.provider_status

    if payment.payment_status == "paid":
        db.session.commit()
        return "paid", None

    if local_status is None:
        db.session.commit()
        return payment.payment_status, None

    if local_status == "paid":
        payment.payment_status = "paid"
        payment.transaction_date = now
        user_id = application.applicant_id
        db.session.add(
            Notification(
                user_id=user_id,
                notification_title="Maya payment successful",
                notification_message=(
                    f"Maya sandbox payment {payment.payment_reference} was verified as paid "
                    f"(₱{float(payment.amount):,.2f}). Source: {source}."
                ),
                notification_type="payment",
                read_status="unread",
                created_date=now,
            )
        )
        db.session.commit()
        user = db.session.get(User, user_id)
        if user is not None and application.application_status == "draft":
            finalize_passport_application(application, user, "paid")
        return "paid", None

    if local_status in {"failed", "cancelled"}:
        payment.payment_status = local_status
        payment.transaction_date = None
        db.session.add(
            Notification(
                user_id=application.applicant_id,
                notification_title=f"Maya payment {local_status}",
                notification_message=(
                    f"Maya sandbox payment {payment.payment_reference} is {local_status} "
                    f"({maya_status or 'no status'}). Source: {source}."
                ),
                notification_type="payment",
                read_status="unread",
                created_date=now,
            )
        )
        db.session.commit()
        return local_status, None

    db.session.commit()
    return payment.payment_status, None


def verify_maya_payment(payment, application, *, source="api"):
    """
    Server-side verification via Maya Retrieve Payment APIs.
    Never mark paid from redirect alone — always call this.
    """
    payload = None
    try:
        if payment.provider_checkout_id:
            payload = retrieve_payment_by_id(payment.provider_checkout_id)
        else:
            payload = retrieve_payment_by_rrn(payment.payment_reference)
    except MayaCheckoutError as exc:
        return payment.payment_status, str(exc)

    checkout_id = str(payload.get("id") or payload.get("checkoutId") or "").strip()
    if checkout_id and not payment.provider_checkout_id:
        payment.provider_checkout_id = checkout_id

    maya_status = payment_status_from_payload(payload)
    local_status = map_maya_status(maya_status)
    return _apply_verified_status(payment, application, local_status, maya_status, source)


def process_maya_webhook(payload):
    """
    Handle Maya webhook JSON (Get Payment equivalent).
    Always re-verify with Retrieve Payment when a checkout id is present.
    """
    if not isinstance(payload, dict):
        return False, "Invalid webhook payload."

    checkout_id = str(payload.get("id") or payload.get("checkoutId") or "").strip()
    reference = str(payload.get("requestReferenceNumber") or "").strip()
    payment = None
    if checkout_id:
        payment = db.session.scalar(
            db.select(Payment).where(Payment.provider_checkout_id == checkout_id)
        )
    if payment is None and reference:
        payment = db.session.scalar(
            db.select(Payment).where(Payment.payment_reference == reference)
        )
    if payment is None:
        return False, "Payment not found for webhook."

    application = db.session.get(Application, payment.application_id)
    if application is None:
        return False, "Application not found for webhook."

    # Prefer authoritative retrieve; fall back to payload status if retrieve fails.
    status, error = verify_maya_payment(payment, application, source="webhook")
    if error and checkout_id:
        maya_status = payment_status_from_payload(payload)
        local_status = map_maya_status(maya_status)
        status, _ = _apply_verified_status(
            payment, application, local_status, maya_status, "webhook-payload"
        )
        return True, status
    if error:
        return False, error
    return True, status
