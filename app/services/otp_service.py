"""Email OTP generation, delivery, and verification for authentication."""

import os
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage

import requests
from dotenv import load_dotenv
from flask import current_app
from sqlalchemy.exc import IntegrityError, ProgrammingError
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models.email_otp import EmailOtp

_otp_table_ready = False


def _now():
    return datetime.utcnow()


def _conf_str(name, default=""):
    try:
        load_dotenv(override=True)
    except Exception:
        pass
    val = os.getenv(name)
    if val is None or str(val).strip() == "":
        try:
            val = current_app.config.get(name, default)
        except Exception:
            val = default
    if val is None:
        val = default
    return str(val).strip()


def _conf_int(name, default):
    raw = _conf_str(name, str(default))
    try:
        return int(raw)
    except Exception:
        return int(default)


def _ensure_otp_table():
    global _otp_table_ready
    if _otp_table_ready:
        return True
    try:
        EmailOtp.__table__.create(bind=db.engine, checkfirst=True)
        _otp_table_ready = True
        return True
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        try:
            current_app.logger.exception("Could not ensure email_otps table")
        except Exception:
            pass
        return False


def generate_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(code):
    return generate_password_hash(str(code))


def verify_code_hash(code_hash, code):
    if not code_hash or code is None:
        return False
    return check_password_hash(code_hash, str(code).strip())


def _settings():
    expiry_minutes = _conf_int("OTP_EXPIRY_MINUTES", 5)
    max_attempts = _conf_int("OTP_MAX_ATTEMPTS", 5)
    cooldown = _conf_int("OTP_RESEND_COOLDOWN_SECONDS", 60)
    return max(1, expiry_minutes), max(1, max_attempts), max(1, cooldown)


def _sender():
    email = _conf_str("BREVO_SENDER_EMAIL", "transportationsupervisor399@gmail.com") or "transportationsupervisor399@gmail.com"
    name = _conf_str("BREVO_SENDER_NAME", "OneGov PH") or "OneGov PH"
    return {"email": email, "name": name}


def _brevo_detail(detail):
    if isinstance(detail, dict):
        for key in ("message", "code", "detail"):
            value = detail.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:180]
    if isinstance(detail, str) and detail.strip():
        return detail.strip()[:180]
    return ""


def _send_via_brevo_api(recipient_email, subject, html, text):
    api_key = _conf_str("BREVO_API_KEY")
    if not api_key:
        return False, "Email verification is not configured.", 0, None

    payload = {
        "sender": _sender(),
        "to": [{"email": recipient_email}],
        "subject": subject,
        "htmlContent": html,
        "textContent": text,
    }
    headers = {
        "api-key": api_key,
        "accept": "application/json",
        "content-type": "application/json",
    }
    url = _conf_str("BREVO_API_URL", "https://api.brevo.com/v3/smtp/email") or "https://api.brevo.com/v3/smtp/email"
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
    except Exception:
        try:
            current_app.logger.exception("OTP email request failed (Brevo API)")
        except Exception:
            pass
        return False, "Could not reach the email service. Please try again.", 0, None

    if 200 <= resp.status_code < 300:
        return True, None, resp.status_code, None

    try:
        detail = resp.json()
    except Exception:
        detail = (resp.text or "")[:240]
    try:
        current_app.logger.warning("OTP email send failed via Brevo API (%s): %s", resp.status_code, detail)
    except Exception:
        pass
    return False, None, resp.status_code, detail


def _send_via_brevo_smtp(recipient_email, subject, html, text):
    api_key = _conf_str("BREVO_API_KEY")
    login = _conf_str("BREVO_SMTP_LOGIN")
    if not api_key or not login:
        return False, "SMTP email settings are incomplete.", 0, None

    host = _conf_str("BREVO_SMTP_SERVER", "smtp-relay.brevo.com") or "smtp-relay.brevo.com"
    port = _conf_int("BREVO_SMTP_PORT", 587)
    sender = _sender()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{sender['name']} <{sender['email']}>"
    msg["To"] = recipient_email
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(login, api_key)
            server.send_message(msg)
    except Exception:
        try:
            current_app.logger.exception("OTP email request failed (Brevo SMTP)")
        except Exception:
            pass
        return False, "Could not send the verification code via SMTP. Please try again.", 0, None
    return True, None, 200, None


def _failure_message(status, detail):
    msg = _brevo_detail(detail)
    lower = msg.lower()
    api_key = _conf_str("BREVO_API_KEY")
    smtp_login = _conf_str("BREVO_SMTP_LOGIN")

    if status in (401, 403) or "unauthor" in lower or "key not found" in lower or "api key" in lower:
        if (
            "unrecognised ip" in lower
            or "unrecognized ip" in lower
            or "authorised_ip" in lower
            or "authorized_ip" in lower
            or "authorised ip" in lower
            or "authorized ip" in lower
        ):
            detail_msg = msg or "Brevo blocked the request from an unrecognised IP address."
            return f"Could not send the verification code: {detail_msg}"
        if api_key.startswith("xsmtpsib") and not smtp_login:
            return (
                "Could not send the verification code: BREVO_API_KEY is an SMTP key, but Brevo Transactional Email API requires an API key (xkeysib-). "
                "Set BREVO_API_KEY to a Brevo API key, or set BREVO_SMTP_LOGIN to send via SMTP with this key."
            )
        if "sender" in lower and ("not valid" in lower or "not found" in lower or "activ" in lower):
            return "Could not send the verification code: sender email is not valid/verified in Brevo. Verify BREVO_SENDER_EMAIL in Brevo."
        if msg and status in (401, 403):
            return f"Could not send the verification code: {msg}"
        return "Could not send the verification code: email service authentication failed. Check BREVO_API_KEY and Brevo sender configuration."
    if status == 400:
        if "sender" in lower:
            return "Could not send the verification code: sender email is not accepted. Verify BREVO_SENDER_EMAIL in Brevo."
        return "Could not send the verification code: email request was rejected. Check Brevo sender/API configuration."
    if status == 402:
        return "Could not send the verification code: the email account cannot send messages right now."
    if status == 429:
        return "Could not send the verification code: too many requests. Please try again shortly."
    if status and status >= 500:
        return "Could not send the verification code: the email service is temporarily unavailable. Please try again."
    return "Could not send the verification code. Please try again."


def send_otp_email(recipient_email, code, purpose):
    """Send a 6-digit OTP using Brevo. Returns (ok, error_message)."""
    api_key = _conf_str("BREVO_API_KEY")
    if not api_key:
        return False, "Email verification is not configured."

    expiry_minutes, _max_attempts, _cooldown = _settings()
    action = "account registration" if purpose == EmailOtp.PURPOSE_REGISTER else "sign-in"
    subject = "Your OneGov PH verification code"
    html = (
        f"<div style='font-family:Arial,sans-serif;line-height:1.5'>"
        f"<p>Your OneGov PH verification code for {action} is:</p>"
        f"<p style='font-size:28px;font-weight:700;letter-spacing:6px;margin:12px 0'>{code}</p>"
        f"<p>This code expires in {expiry_minutes} minutes.</p>"
        f"<p>If you did not request this, you can ignore this message.</p>"
        f"</div>"
    )
    text = (
        f"Your OneGov PH verification code for {action} is: {code}\n"
        f"This code expires in {expiry_minutes} minutes.\n"
        f"If you did not request this, you can ignore this message."
    )

    # Primary: Brevo Transactional Email API.
    ok, err, status, detail = _send_via_brevo_api(recipient_email, subject, html, text)
    if ok:
        return True, None
    if err:
        # network/config error already logged
        return False, err

    # Fallback for SMTP-key setups only when explicitly configured.
    smtp_login = _conf_str("BREVO_SMTP_LOGIN")
    if api_key.startswith("xsmtpsib") and smtp_login and status in (401, 403):
        ok_smtp, err_smtp, _s, _d = _send_via_brevo_smtp(recipient_email, subject, html, text)
        if ok_smtp:
            return True, None
        if err_smtp:
            return False, err_smtp

    return False, _failure_message(status, detail)


def invalidate_active_otps(purpose, email, now=None):
    now = now or _now()
    (
        db.session.query(EmailOtp)
        .filter(
            EmailOtp.purpose == purpose,
            EmailOtp.email == email,
            EmailOtp.consumed_at.is_(None),
            EmailOtp.invalidated_at.is_(None),
        )
        .update({EmailOtp.invalidated_at: now}, synchronize_session=False)
    )


def _create_otp_record(purpose, email, *, user_id=None, payload=None):
    now = _now()
    expiry_minutes, max_attempts, cooldown = _settings()
    invalidate_active_otps(purpose, email, now=now)
    code = generate_code()
    record = EmailOtp(
        purpose=purpose,
        user_id=user_id,
        email=email,
        code_hash=hash_code(code),
        payload=payload,
        attempts=0,
        max_attempts=max_attempts,
        expires_at=now + timedelta(minutes=expiry_minutes),
        last_sent_at=now,
        resend_available_at=now + timedelta(seconds=cooldown),
    )
    db.session.add(record)
    db.session.flush()
    return record, code


def issue_otp(purpose, email, *, user_id=None, payload=None, commit=True):
    """Create and send a new OTP, invalidating previous active ones for the same purpose/email."""
    _ensure_otp_table()
    try:
        record, code = _create_otp_record(purpose, email, user_id=user_id, payload=payload)
    except ProgrammingError:
        db.session.rollback()
        _ensure_otp_table()
        try:
            record, code = _create_otp_record(purpose, email, user_id=user_id, payload=payload)
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Could not create OTP record")
            return None, "Email verification storage is not ready. Please try again."
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Could not create OTP record")
        return None, "Could not start verification. Please try again."

    ok, send_error = send_otp_email(email, code, purpose)
    if not ok:
        db.session.rollback()
        return None, send_error

    if commit:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return None, "Could not start verification. Please try again."
    return record, None


def get_active_otp(otp_id, purpose, email):
    if not otp_id:
        return None
    try:
        return db.session.scalar(
            db.select(EmailOtp).where(
                EmailOtp.otp_id == otp_id,
                EmailOtp.purpose == purpose,
                EmailOtp.email == email,
            )
        )
    except ProgrammingError:
        db.session.rollback()
        _ensure_otp_table()
        return None
    except Exception:
        db.session.rollback()
        return None


def resend_otp(otp_id, purpose, email):
    """Resend by invalidating current active OTP and issuing a fresh one."""
    record = get_active_otp(otp_id, purpose, email)
    now = _now()
    if record is None:
        return None, "Your verification session expired. Please start again.", 0

    # Only allow resend based on the latest active/known challenge state.
    if record.consumed_at is not None or record.invalidated_at is not None:
        try:
            latest = db.session.scalar(
                db.select(EmailOtp)
                .where(
                    EmailOtp.purpose == purpose,
                    EmailOtp.email == email,
                    EmailOtp.consumed_at.is_(None),
                    EmailOtp.invalidated_at.is_(None),
                )
                .order_by(EmailOtp.created_at.desc(), EmailOtp.otp_id.desc())
            )
        except ProgrammingError:
            db.session.rollback()
            return None, "Your verification session expired. Please start again.", 0
        except Exception:
            db.session.rollback()
            return None, "Your verification session expired. Please start again.", 0
        if latest is None:
            return None, "Your verification session expired. Please start again.", 0
        record = latest

    wait = record.resend_wait_seconds(now)
    if wait > 0:
        return None, f"Please wait {wait} seconds before requesting a new code.", wait

    user_id = record.user_id
    payload = record.payload
    new_record, error = issue_otp(purpose, email, user_id=user_id, payload=payload, commit=True)
    if error:
        return None, error, 0
    return new_record, None, 0


def verify_otp(otp_id, purpose, email, submitted_code):
    """Verify submitted code. Returns (record_or_none, error_message, status)."""
    record = get_active_otp(otp_id, purpose, email)
    now = _now()
    if record is None:
        return None, "Your verification session expired. Please start again.", "missing"

    try:
        if record.consumed_at is not None or record.invalidated_at is not None:
            return None, "This verification code is no longer valid. Please request a new code.", "invalid"

        if record.is_expired(now):
            record.invalidated_at = now
            db.session.commit()
            return None, "This verification code has expired. Please request a new code.", "expired"

        if record.attempts_exhausted():
            record.invalidated_at = now
            db.session.commit()
            return None, "Too many incorrect attempts. Please request a new code.", "locked"

        if not verify_code_hash(record.code_hash, submitted_code):
            record.attempts = (record.attempts or 0) + 1
            if record.attempts >= (record.max_attempts or 5):
                record.invalidated_at = now
                db.session.commit()
                return None, "Too many incorrect attempts. Please request a new code.", "locked"
            remaining = (record.max_attempts or 5) - record.attempts
            db.session.commit()
            suffix = "attempt" if remaining == 1 else "attempts"
            return None, f"Incorrect verification code. {remaining} {suffix} remaining.", "invalid_code"

        record.consumed_at = now
        # Invalidate any other active OTPs for same purpose/email as a safety measure.
        (
            db.session.query(EmailOtp)
            .filter(
                EmailOtp.purpose == purpose,
                EmailOtp.email == email,
                EmailOtp.otp_id != record.otp_id,
                EmailOtp.consumed_at.is_(None),
                EmailOtp.invalidated_at.is_(None),
            )
            .update({EmailOtp.invalidated_at: now}, synchronize_session=False)
        )
        db.session.commit()
        return record, None, "ok"
    except ProgrammingError:
        db.session.rollback()
        _ensure_otp_table()
        return None, "Your verification session expired. Please start again.", "missing"
    except Exception:
        db.session.rollback()
        return None, "Could not verify the code. Please try again.", "error"


def otp_status(otp_id, purpose, email):
    record = get_active_otp(otp_id, purpose, email)
    now = _now()
    if record is None or record.consumed_at is not None or record.invalidated_at is not None:
        return {"active": False, "expires_in": 0, "resend_in": 0}
    if record.is_expired(now):
        return {"active": False, "expires_in": 0, "resend_in": 0}
    return {
        "active": True,
        "expires_in": record.expires_in_seconds(now),
        "resend_in": record.resend_wait_seconds(now),
    }
