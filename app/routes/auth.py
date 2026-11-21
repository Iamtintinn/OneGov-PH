from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, logout_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.email_otp import EmailOtp
from app.models.user import AccountActivityLog, User
from app.services import otp_service
from app.utils.helpers import establish_session, home_endpoint_for_role
from app.utils.validators import (
    clean_text,
    normalize_email,
    validate_new_password,
    validate_registration,
)

auth_bp = Blueprint("auth", __name__)

OTP_SESSION_KEYS = ("otp_id", "otp_purpose", "otp_email", "otp_next")


def _safe_next_url(raw):
    """Allow only same-site relative paths (used after Maya QRPh return)."""
    candidate = (raw or "").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return None
    if "\\" in candidate or "://" in candidate:
        return None
    return candidate


def _clear_otp_session():
    for key in OTP_SESSION_KEYS:
        session.pop(key, None)


def _render_verify_otp(error=None, notice=None):
    otp_id = session.get("otp_id")
    purpose = session.get("otp_purpose")
    email = session.get("otp_email") or ""
    status = otp_service.otp_status(otp_id, purpose, email)
    if not status.get("active"):
        _clear_otp_session()
        flash("Your verification session expired. Please start again.", "warning")
        if purpose == EmailOtp.PURPOSE_REGISTER:
            return redirect(url_for("auth.register"))
        return redirect(url_for("auth.login"))
    return render_template(
        "auth/verify_otp.html",
        purpose=purpose,
        email=email,
        error=error,
        notice=notice,
        expires_in=status.get("expires_in", 0),
        resend_in=status.get("resend_in", 0),
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = _safe_next_url(request.values.get("next"))
    if current_user.is_authenticated:
        return redirect(next_url or url_for(home_endpoint_for_role(current_user.role)))

    email = ""
    error = None
    if request.method == "POST":
        email = normalize_email(request.form.get("email"))
        password = request.form.get("password") or ""
        if not email or not password:
            error = "Enter your email and password."
        else:
            user = db.session.scalar(db.select(User).where(User.email == email))
            if user is None or not user.check_password(password):
                error = "Invalid email or password."
                try:
                    log_activity(activity_type="Failed Login", module="Authentication", description=f"Failed login attempt for {email}", record_id=getattr(user,'user_id',None), status="Failed", user=user)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
            elif not user.is_active:
                error = "This account is disabled. Contact OneGov PH support."
                try:
                    log_activity(activity_type="Login Denied", module="Authentication", description=f"Login denied for disabled account {email}", record_id=user.user_id, status="Denied", user=user)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
            elif email in {"admin@0negov.ph", "admin@onegov.ph"} or not getattr(user, "login_otp_enabled", True):
                establish_session(user)
                try:
                    log_activity(activity_type="Login", module="Authentication", description=f"User signed in: {user.email}", record_id=user.user_id, status="Success", user=user)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                return redirect(next_url or url_for(home_endpoint_for_role(user.role)))
            else:
                _clear_otp_session()
                record, send_error = otp_service.issue_otp(
                    EmailOtp.PURPOSE_LOGIN,
                    user.email,
                    user_id=user.user_id,
                )
                if send_error or record is None:
                    error = send_error or "Could not send the verification code. Please try again."
                else:
                    session["otp_id"] = record.otp_id
                    session["otp_purpose"] = EmailOtp.PURPOSE_LOGIN
                    session["otp_email"] = user.email
                    if next_url:
                        session["otp_next"] = next_url
                    flash("A verification code was sent to your email.", "success")
                    return redirect(url_for("auth.verify_otp"))

    return render_template("auth/login.html", email=email, error=error, next_url=next_url)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(home_endpoint_for_role(current_user.role)))

    form = {
        "first_name": "",
        "middle_name": "",
        "last_name": "",
        "email": "",
        "contact_number": "",
    }
    errors = {}
    if request.method == "POST":
        submitted = {
            "first_name": request.form.get("first_name", ""),
            "middle_name": request.form.get("middle_name", ""),
            "last_name": request.form.get("last_name", ""),
            "email": request.form.get("email", ""),
            "contact_number": request.form.get("contact_number", ""),
        }
        cleaned, errors = validate_registration(
            submitted,
            request.form.get("password") or "",
            request.form.get("confirm_password") or "",
        )
        form = {
            "first_name": clean_text(submitted["first_name"]),
            "middle_name": clean_text(submitted["middle_name"]),
            "last_name": clean_text(submitted["last_name"]),
            "email": cleaned.get("email") or normalize_email(submitted["email"]),
            "contact_number": clean_text(submitted["contact_number"]),
        }
        if not errors:
            duplicate = db.session.scalar(
                db.select(User.user_id).where(User.email == cleaned["email"])
            )
            if duplicate is not None:
                errors["email"] = "An account with this email already exists."
            else:
                payload = {
                    "first_name": cleaned["first_name"],
                    "middle_name": cleaned.get("middle_name") or "",
                    "last_name": cleaned["last_name"],
                    "email": cleaned["email"],
                    "contact_number": cleaned["contact_number"],
                    "password": request.form.get("password") or "",
                }
                _clear_otp_session()
                record, send_error = otp_service.issue_otp(
                    EmailOtp.PURPOSE_REGISTER,
                    cleaned["email"],
                    payload=payload,
                )
                if send_error or record is None:
                    errors["email"] = send_error or "Could not send the verification code. Please try again."
                else:
                    session["otp_id"] = record.otp_id
                    session["otp_purpose"] = EmailOtp.PURPOSE_REGISTER
                    session["otp_email"] = cleaned["email"]
                    flash("A verification code was sent to your email.", "success")
                    return redirect(url_for("auth.verify_otp"))

    return render_template("auth/register.html", form=form, errors=errors)


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    purpose = session.get("otp_purpose")
    otp_id = session.get("otp_id")
    email = session.get("otp_email") or ""
    if purpose not in EmailOtp.PURPOSES or not otp_id or not email:
        _clear_otp_session()
        flash("Start again to continue.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        action = clean_text(request.form.get("action")) or "verify"
        if action == "resend":
            record, send_error, _wait = otp_service.resend_otp(otp_id, purpose, email)
            if send_error or record is None:
                # If session expired/missing, send user back appropriately
                if "session expired" in (send_error or "").lower() or "start again" in (send_error or "").lower():
                    _clear_otp_session()
                    flash(send_error or "Your verification session expired. Please start again.", "warning")
                    return redirect(url_for("auth.register" if purpose == EmailOtp.PURPOSE_REGISTER else "auth.login"))
                return _render_verify_otp(error=send_error)
            session["otp_id"] = record.otp_id
            flash("A new verification code was sent to your email.", "success")
            return redirect(url_for("auth.verify_otp"))

        code = (request.form.get("code") or "").strip()
        if not code:
            return _render_verify_otp(error="Enter the 6-digit verification code.")
        if not code.isdigit() or len(code) != 6:
            return _render_verify_otp(error="Enter the 6-digit verification code.")

        record, verify_error, status = otp_service.verify_otp(otp_id, purpose, email, code)
        if verify_error or record is None:
            if status in {"expired", "locked", "invalid", "missing"}:
                _clear_otp_session()
                flash(verify_error or "Please start again.", "warning")
                return redirect(url_for("auth.register" if purpose == EmailOtp.PURPOSE_REGISTER else "auth.login"))
            return _render_verify_otp(error=verify_error)

        if purpose == EmailOtp.PURPOSE_LOGIN:
            user = db.session.get(User, record.user_id) if record.user_id else None
            if user is None or not user.is_active:
                _clear_otp_session()
                flash("This account is unavailable. Sign in again.", "warning")
                return redirect(url_for("auth.login"))
            next_url = _safe_next_url(session.get("otp_next"))
            _clear_otp_session()
            establish_session(user)
            try:
                log_activity(activity_type="Login", module="Authentication", description=f"User signed in via OTP: {user.email}", record_id=user.user_id, status="Success", user=user)
                db.session.commit()
            except Exception:
                db.session.rollback()
            return redirect(next_url or url_for(home_endpoint_for_role(user.role)))

        # Registration: create account only after successful verification.
        data = record.payload or {}
        reg_email = normalize_email(data.get("email") or email)
        if not reg_email or not data.get("password"):
            _clear_otp_session()
            flash("Registration session expired. Please register again.", "warning")
            return redirect(url_for("auth.register"))
        if db.session.scalar(db.select(User.user_id).where(User.email == reg_email)) is not None:
            _clear_otp_session()
            flash("An account with this email already exists.", "warning")
            return redirect(url_for("auth.register"))

        user = User.register_citizen(
            first_name=data.get("first_name") or "",
            middle_name=(data.get("middle_name") or None),
            last_name=data.get("last_name") or "",
            email=reg_email,
            contact_number=data.get("contact_number") or "",
            password=data.get("password") or "",
        )
        user.email_verification_status = "verified"
        user.login_otp_enabled = True
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            _clear_otp_session()
            flash("An account with this email already exists.", "warning")
            return redirect(url_for("auth.register"))

        _clear_otp_session()
        establish_session(user)
        flash("Your citizen account has been created.", "success")
        return redirect(url_for("citizen.dashboard"))

    return _render_verify_otp()


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    errors = {}
    if request.method == "POST":
        current_password = request.form.get("current_password") or ""
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""
        if not current_user.check_password(current_password):
            errors["current_password"] = "Current password is incorrect."
        errors.update(validate_new_password(password, confirm_password))
        if not errors:
            current_user.set_password(password)
            current_user.clear_password_change_requirement()
            db.session.add(
                AccountActivityLog(
                    target_user_id=current_user.user_id,
                    actor_user_id=current_user.user_id,
                    action="password_changed",
                    description=f"Password changed by {current_user.full_name}.",
                )
            )
            db.session.commit()
            flash("Your password has been updated.", "success")
            return redirect(url_for(home_endpoint_for_role(current_user.role)))
    return render_template("auth/change_password.html", errors=errors)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    try:
        if current_user.is_authenticated:
            log_activity(activity_type="Logout", module="Authentication", description=f"User signed out: {current_user.email}", record_id=current_user.user_id, status="Success", user=current_user)
            db.session.commit()
    except Exception:
        db.session.rollback()
    _clear_otp_session()
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
