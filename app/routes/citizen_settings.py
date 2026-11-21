"""Citizen Settings module - full functional implementation."""

from datetime import datetime
import json

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, logout_user
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models.account_request import AccountRequest
from app.models.user import AccountActivityLog, User
from app.models.user_session import UserSession
from app.services.citizen_settings_service import (
    CIVIL_STATUS_OPTIONS, DEFAULT_NOTIFICATION_PREFS, LANGUAGE_OPTIONS, NOTIF_METHOD_OPTIONS, SEX_OPTIONS,
    get_addresses, get_app_prefs, get_last_login, get_login_activity, get_notification_prefs, get_privacy,
    get_profile_extra, profile_picture_url, record_login_activity, save_profile_picture, set_addresses,
    set_app_prefs, set_extended, set_notification_prefs, set_privacy, set_profile_extra, validate_address,
    validate_profile,
)
from app.utils.decorators import citizen_portal_required
from app.utils.helpers import generate_csrf_token
from app.utils.validators import clean_text, normalize_contact_number, normalize_email, validate_new_password

settings_bp = Blueprint("citizen_settings", __name__, url_prefix="/citizen/settings")


def _ctx(section="personal"):
    extra = get_profile_extra(current_user)
    addrs = get_addresses(current_user)
    default_addr = next((a for a in addrs if a.get("is_default")), addrs[0] if addrs else None)
    return {
        "page": "citizen.settings",
        "section": section,
        "profile_extra": extra,
        "profile_picture_url": profile_picture_url(current_user),
        "addresses": addrs,
        "default_address": default_addr,
        "notif_prefs": get_notification_prefs(current_user),
        "privacy": get_privacy(current_user),
        "app_prefs": get_app_prefs(current_user),
        "last_login": get_last_login(current_user),
        "login_activity": get_login_activity(current_user),
        "active_sessions": _active_sessions(),
        "account_requests": _account_requests(),
        "sex_options": SEX_OPTIONS,
        "civil_status_options": CIVIL_STATUS_OPTIONS,
        "language_options": LANGUAGE_OPTIONS,
        "notif_method_options": NOTIF_METHOD_OPTIONS,
        "notif_categories": [
            ("application_updates", "Application Updates"),
            ("payment_notifications", "Payment Notifications"),
            ("document_processing_updates", "Document Processing Updates"),
            ("delivery_updates", "Delivery Updates"),
            ("government_announcements", "Government Announcements"),
        ],
    }


def _active_sessions():
    try:
        rows = db.session.scalars(
            db.select(UserSession)
            .where(UserSession.user_id == current_user.user_id, UserSession.revoked_at.is_(None))
            .order_by(UserSession.last_seen_at.desc())
        ).all()
        return rows
    except Exception:
        db.session.rollback()
        return []


def _account_requests():
    try:
        return db.session.scalars(
            db.select(AccountRequest)
            .where(AccountRequest.user_id == current_user.user_id)
            .order_by(AccountRequest.created_at.desc())
        ).all()
    except Exception:
        db.session.rollback()
        return []


def _log(action, description):
    try:
        db.session.add(AccountActivityLog(
            target_user_id=current_user.user_id,
            actor_user_id=current_user.user_id,
            action=action[:80],
            description=description[:500],
        ))
    except Exception:
        pass


def _settings_redirect(section):
    if request.form.get("admin_mode") == "1" or request.args.get("admin_mode") == "1":
        try:
            from app.utils.portal import in_admin_portal
            # admin portal settings page uses admin_portal.settings
            return redirect(url_for("admin_portal.settings", section=section))
        except Exception:
            pass
    ref = request.referrer or ""
    if "/admin/portal/settings" in ref:
        return redirect(url_for("admin_portal.settings", section=section))
    return redirect(url_for("citizen_settings.index", section=section))


def _json_or_redirect(ok, message, section, category="success"):
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        status = 200 if ok else 400
        return jsonify({"ok": ok, "message": message, "category": category}), status
    flash(message, category)
    return _settings_redirect(section)


@settings_bp.route("/", methods=["GET"])
@citizen_portal_required
def index():
    section = clean_text(request.args.get("section")) or "personal"
    allowed = {"personal", "address", "security", "notifications", "privacy", "preferences", "help"}
    if section not in allowed:
        section = "personal"
    return render_template("citizen/settings/index.html", **_ctx(section))


@settings_bp.route("/personal", methods=["POST"])
@citizen_portal_required
def save_personal():
    cleaned, errors = validate_profile(request.form, current_user)
    pic_file = request.files.get("profile_picture")
    pic_name = None
    if pic_file and pic_file.filename:
        pic_name, pic_err = save_profile_picture(current_user, pic_file)
        if pic_err:
            errors["profile_picture"] = pic_err

    email_changed = cleaned.get("email") and cleaned["email"] != (current_user.email or "").lower()
    if email_changed:
        existing = db.session.scalar(db.select(User).where(User.email == cleaned["email"], User.user_id != current_user.user_id))
        if existing:
            errors["email"] = "This email address is already in use."

    if errors:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False, "message": "Please correct the highlighted fields.", "errors": errors}), 400
        for msg in errors.values():
            flash(msg, "warning")
        return redirect(url_for("citizen_settings.index", section="personal"))

    old_email = current_user.email
    current_user.first_name = cleaned["first_name"]
    current_user.middle_name = cleaned["middle_name"] or None
    current_user.last_name = cleaned["last_name"]
    # preserve existing full_name behavior
    parts = [cleaned["first_name"], cleaned.get("middle_name") or "", cleaned["last_name"]]
    if cleaned.get("suffix"):
        parts.append(cleaned["suffix"])
    current_user.full_name = " ".join([p for p in parts if p]).strip()
    current_user.contact_number = cleaned["contact_number"]
    if email_changed:
        current_user.email = cleaned["email"]
        try:
            current_user.email_verification_status = "unverified"
        except Exception:
            pass

    extra = get_profile_extra(current_user)
    extra.update({
        "suffix": cleaned["suffix"], "date_of_birth": cleaned["date_of_birth"], "sex": cleaned["sex"],
        "civil_status": cleaned["civil_status"], "nationality": cleaned["nationality"] or "Filipino",
    })
    if pic_name:
        extra["profile_picture"] = pic_name
    set_profile_extra(current_user, extra)
    _log("profile_updated", "Updated personal information.")
    db.session.commit()

    msg = "Personal information saved."
    if email_changed:
        msg += " Email changed; please verify your new email address."
    return _json_or_redirect(True, msg, "personal")


@settings_bp.route("/address", methods=["POST"])
@citizen_portal_required
def save_address():
    action = clean_text(request.form.get("action")) or "save"
    addrs = get_addresses(current_user)

    if action == "delete":
        addr_id = clean_text(request.form.get("address_id"))
        addrs = [a for a in addrs if str(a.get("id")) != addr_id]
        if addrs and not any(a.get("is_default") for a in addrs):
            addrs[0]["is_default"] = True
        set_addresses(current_user, addrs)
        _log("address_deleted", "Deleted an address.")
        db.session.commit()
        return _json_or_redirect(True, "Address removed.", "address")

    cleaned, errors = validate_address(request.form)
    if errors:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False, "message": "Please correct the highlighted fields.", "errors": errors}), 400
        for msg in errors.values():
            flash(msg, "warning")
        return redirect(url_for("citizen_settings.index", section="address"))

    addr_id = clean_text(request.form.get("address_id"))
    make_default = request.form.get("is_default") == "1" or not addrs
    entry = {"id": addr_id or str(int(datetime.now().timestamp() * 1000)), **cleaned, "is_default": make_default}
    found = False
    for i, a in enumerate(addrs):
        if str(a.get("id")) == str(entry["id"]):
            addrs[i] = entry; found = True; break
    if not found:
        addrs.append(entry)
    if make_default:
        for a in addrs:
            a["is_default"] = str(a.get("id")) == str(entry["id"])
    set_addresses(current_user, addrs)

    # keep legacy address string in sync with default
    default_addr = next((a for a in addrs if a.get("is_default")), None)
    if default_addr:
        parts = [default_addr.get("house_unit"), default_addr.get("street"), default_addr.get("barangay"),
                 default_addr.get("city"), default_addr.get("province"), default_addr.get("region"), default_addr.get("zip_code")]
        current_user.address = ", ".join([p for p in parts if p])[:500]

    _log("address_saved", "Saved address information.")
    db.session.commit()
    return _json_or_redirect(True, "Address saved.", "address")


@settings_bp.route("/security/password", methods=["POST"])
@citizen_portal_required
def change_password():
    current_password = request.form.get("current_password") or ""
    password = request.form.get("password") or ""
    confirm = request.form.get("confirm_password") or ""
    errors = {}
    if not current_user.check_password(current_password):
        errors["current_password"] = "Current password is incorrect."
    errors.update(validate_new_password(password, confirm))
    if errors:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False, "message": "Please correct the highlighted fields.", "errors": errors}), 400
        for msg in errors.values():
            flash(msg, "warning")
        return redirect(url_for("citizen_settings.index", section="security"))
    current_user.set_password(password)
    _log("password_changed", "Changed account password from settings.")
    db.session.commit()
    return _json_or_redirect(True, "Password updated successfully.", "security")


@settings_bp.route("/security/2fa", methods=["POST"])
@citizen_portal_required
def toggle_2fa():
    enabled = request.form.get("enabled") == "1"
    extra = get_profile_extra(current_user)
    ext = current_user.admin_permissions if isinstance(current_user.admin_permissions, dict) else {}
    # store 2FA flag in citizen_settings
    settings_ext = ext.get("citizen_settings") if isinstance(ext.get("citizen_settings"), dict) else {}
    settings_ext["two_factor_enabled"] = bool(enabled)
    ext["citizen_settings"] = settings_ext
    current_user.admin_permissions = ext
    _log("2fa_toggled", f"{'Enabled' if enabled else 'Disabled'} two-factor authentication preference.")
    db.session.commit()
    return _json_or_redirect(True, f"Two-factor authentication {'enabled' if enabled else 'disabled'}.", "security")


@settings_bp.route("/security/sessions/logout-all", methods=["POST"])
@citizen_portal_required
def logout_all_devices():
    try:
        sessions = db.session.scalars(
            db.select(UserSession).where(UserSession.user_id == current_user.user_id, UserSession.revoked_at.is_(None))
        ).all()
        now = datetime.now()
        for s in sessions:
            s.revoked_at = now
        _log("logout_all_devices", "Logged out from all devices.")
        db.session.commit()
    except Exception:
        db.session.rollback()
    logout_user()
    flash("You have been logged out from all devices.", "success")
    return redirect(url_for("auth.login"))


@settings_bp.route("/notifications", methods=["POST"])
@citizen_portal_required
def save_notifications():
    prefs = get_notification_prefs(current_user)
    for cat in prefs.keys():
        for ch in ["in_app", "email", "sms"]:
            prefs[cat][ch] = request.form.get(f"{cat}__{ch}") == "1"
    set_notification_prefs(current_user, prefs)
    _log("notification_preferences_updated", "Updated notification preferences.")
    db.session.commit()
    return _json_or_redirect(True, "Notification preferences saved.", "notifications")


@settings_bp.route("/privacy/consent", methods=["POST"])
@citizen_portal_required
def save_privacy():
    privacy = get_privacy(current_user)
    for k in privacy.keys():
        privacy[k] = request.form.get(k) == "1"
    set_privacy(current_user, privacy)
    _log("privacy_updated", "Updated privacy and consent settings.")
    db.session.commit()
    return _json_or_redirect(True, "Privacy settings saved.", "privacy")


@settings_bp.route("/privacy/download", methods=["GET"])
@citizen_portal_required
def download_my_data():
    from flask import Response
    payload = {
        "exported_at": datetime.now().isoformat(),
        "user": {
            "user_id": current_user.user_id,
            "first_name": current_user.first_name, "middle_name": current_user.middle_name,
            "last_name": current_user.last_name, "full_name": current_user.full_name,
            "email": current_user.email, "contact_number": current_user.contact_number,
            "address": current_user.address, "account_status": current_user.account_status,
            "email_verification_status": current_user.email_verification_status,
            "date_registered": str(current_user.date_registered),
        },
        "profile_extra": get_profile_extra(current_user),
        "addresses": get_addresses(current_user),
        "notification_preferences": get_notification_prefs(current_user),
        "privacy": get_privacy(current_user),
        "application_preferences": get_app_prefs(current_user),
    }
    _log("data_downloaded", "Downloaded personal data export.")
    db.session.commit()
    body = json.dumps(payload, indent=2, default=str)
    return Response(body, mimetype="application/json", headers={"Content-Disposition": "attachment; filename=onegov-my-data.json"})


@settings_bp.route("/privacy/account-request", methods=["POST"])
@citizen_portal_required
def account_request():
    req_type = clean_text(request.form.get("request_type"))
    reason = clean_text(request.form.get("reason"))[:500]
    if req_type not in {"deactivation", "deletion"}:
        return _json_or_redirect(False, "Invalid request type.", "privacy", "warning")
    # prevent duplicate pending
    try:
        existing = db.session.scalar(
            db.select(AccountRequest).where(
                AccountRequest.user_id == current_user.user_id,
                AccountRequest.request_type == req_type,
                AccountRequest.status == "pending",
            )
        )
    except Exception:
        db.session.rollback()
        existing = None
    if existing:
        return _json_or_redirect(False, f"You already have a pending {req_type} request.", "privacy", "warning")
    try:
        req = AccountRequest(user_id=current_user.user_id, request_type=req_type, reason=reason or None, status="pending")
        db.session.add(req)
        _log(f"account_{req_type}_requested", f"Requested account {req_type}.")
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("account request failed")
        return _json_or_redirect(False, "Could not submit request. The database migration may be required.", "privacy", "danger")
    return _json_or_redirect(True, f"Account {req_type} request submitted for review.", "privacy")


@settings_bp.route("/preferences", methods=["POST"])
@citizen_portal_required
def save_preferences():
    prefs = get_app_prefs(current_user)
    prefs["preferred_notification_method"] = clean_text(request.form.get("preferred_notification_method")) or "in_app"
    prefs["preferred_language"] = clean_text(request.form.get("preferred_language")) or "en"
    contact = normalize_contact_number(request.form.get("default_application_contact_number"))
    prefs["default_application_contact_number"] = contact
    addr_id = clean_text(request.form.get("default_delivery_address_id"))
    if addr_id:
        prefs["default_delivery_address_id"] = addr_id
        addrs = get_addresses(current_user)
        for a in addrs:
            a["is_default"] = str(a.get("id")) == addr_id
        set_addresses(current_user, addrs)
        default_addr = next((a for a in addrs if a.get("is_default")), None)
        if default_addr:
            parts = [default_addr.get("house_unit"), default_addr.get("street"), default_addr.get("barangay"),
                     default_addr.get("city"), default_addr.get("province"), default_addr.get("region"), default_addr.get("zip_code")]
            current_user.address = ", ".join([p for p in parts if p])[:500]
    if prefs["preferred_notification_method"] not in {"in_app", "email", "sms"}:
        prefs["preferred_notification_method"] = "in_app"
    if prefs["preferred_language"] not in {"en", "fil"}:
        prefs["preferred_language"] = "en"
    set_app_prefs(current_user, prefs)
    _log("app_preferences_updated", "Updated application preferences.")
    db.session.commit()
    return _json_or_redirect(True, "Application preferences saved.", "preferences")


@settings_bp.route("/help/report", methods=["POST"])
@citizen_portal_required
def report_problem():
    subject = clean_text(request.form.get("subject"))[:120]
    message = clean_text(request.form.get("message"))[:1000]
    if not subject or not message:
        return _json_or_redirect(False, "Subject and message are required.", "help", "warning")
    _log("support_request", f"Help/Support: {subject} - {message[:200]}")
    db.session.commit()
    return _json_or_redirect(True, "Your message has been submitted. Our support team will review it.", "help")
