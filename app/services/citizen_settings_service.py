"""Citizen settings helpers: validation, storage, and preference defaults."""

from datetime import datetime
import json
import re

from flask import current_app
from werkzeug.utils import secure_filename

from app.utils.validators import clean_text, normalize_contact_number, normalize_email, validate_name

PROFILE_PIC_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
PROFILE_PIC_MAX = 2 * 1024 * 1024

DEFAULT_NOTIFICATION_PREFS = {
    "application_updates": {"in_app": True, "email": True, "sms": False},
    "payment_notifications": {"in_app": True, "email": True, "sms": False},
    "document_processing_updates": {"in_app": True, "email": True, "sms": False},
    "delivery_updates": {"in_app": True, "email": True, "sms": False},
    "government_announcements": {"in_app": True, "email": False, "sms": False},
}

DEFAULT_PRIVACY = {
    "privacy_policy_accepted": False,
    "terms_accepted": False,
    "data_collection_consent": False,
    "personal_info_usage_consent": False,
}

DEFAULT_APP_PREFS = {
    "preferred_notification_method": "in_app",
    "preferred_language": "en",
    "default_application_contact_number": "",
    "default_delivery_address_id": None,
}

SEX_OPTIONS = ["Male", "Female", "Prefer not to say"]
CIVIL_STATUS_OPTIONS = ["Single", "Married", "Widowed", "Separated", "Divorced"]
LANGUAGE_OPTIONS = [("en", "English"), ("fil", "Filipino")]
NOTIF_METHOD_OPTIONS = [("in_app", "In-App"), ("email", "Email"), ("sms", "SMS")]


def _perm_dict(user):
    p = user.admin_permissions
    return dict(p) if isinstance(p, dict) else {}


def _mark_perm_dirty(user):
    try:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(user, "admin_permissions")
    except Exception:
        pass


def _save_perm(user, key, value):
    p = _perm_dict(user)
    p[key] = value
    user.admin_permissions = p
    _mark_perm_dirty(user)


def get_extended(user):
    p = _perm_dict(user)
    ext = p.get("citizen_settings") if isinstance(p.get("citizen_settings"), dict) else {}
    return ext


def set_extended(user, ext):
    p = _perm_dict(user)
    p["citizen_settings"] = ext
    user.admin_permissions = p
    _mark_perm_dirty(user)


def get_notification_prefs(user):
    ext = get_extended(user)
    prefs = ext.get("notification_preferences")
    if not isinstance(prefs, dict):
        prefs = {}
    merged = {}
    for cat, defaults in DEFAULT_NOTIFICATION_PREFS.items():
        current = prefs.get(cat) if isinstance(prefs.get(cat), dict) else {}
        merged[cat] = {ch: bool(current.get(ch, dv)) for ch, dv in defaults.items()}
    return merged


def set_notification_prefs(user, prefs):
    ext = get_extended(user)
    ext["notification_preferences"] = prefs
    set_extended(user, ext)


def get_privacy(user):
    ext = get_extended(user)
    priv = ext.get("privacy")
    if not isinstance(priv, dict):
        priv = {}
    merged = dict(DEFAULT_PRIVACY)
    for k in DEFAULT_PRIVACY:
        if k in priv:
            merged[k] = bool(priv[k])
    return merged


def set_privacy(user, privacy):
    ext = get_extended(user)
    ext["privacy"] = privacy
    set_extended(user, ext)


def get_app_prefs(user):
    ext = get_extended(user)
    prefs = ext.get("app_preferences")
    if not isinstance(prefs, dict):
        prefs = {}
    merged = dict(DEFAULT_APP_PREFS)
    merged.update({k: prefs.get(k, v) for k, v in DEFAULT_APP_PREFS.items() if k in prefs or k not in merged})
    for k, v in DEFAULT_APP_PREFS.items():
        if k not in prefs:
            merged[k] = v
        else:
            merged[k] = prefs[k]
    method = clean_text(str(merged.get("preferred_notification_method") or "in_app")).lower()
    merged["preferred_notification_method"] = method if method in {"in_app", "email", "sms"} else "in_app"
    lang = clean_text(str(merged.get("preferred_language") or "en")).lower()
    merged["preferred_language"] = lang if lang in {"en", "fil"} else "en"
    merged["default_application_contact_number"] = clean_text(str(merged.get("default_application_contact_number") or ""))[:20]
    return merged


def set_app_prefs(user, prefs):
    ext = get_extended(user)
    ext["app_preferences"] = prefs
    set_extended(user, ext)


def get_addresses(user):
    ext = get_extended(user)
    addrs = ext.get("addresses")
    if not isinstance(addrs, list):
        addrs = []
    cleaned = []
    for i, a in enumerate(addrs):
        if not isinstance(a, dict):
            continue
        cleaned.append({
            "id": str(a.get("id") or i + 1),
            "house_unit": clean_text(str(a.get("house_unit") or ""))[:120],
            "street": clean_text(str(a.get("street") or ""))[:120],
            "barangay": clean_text(str(a.get("barangay") or ""))[:120],
            "city": clean_text(str(a.get("city") or ""))[:120],
            "province": clean_text(str(a.get("province") or ""))[:120],
            "region": clean_text(str(a.get("region") or ""))[:120],
            "zip_code": clean_text(str(a.get("zip_code") or ""))[:10],
            "is_default": bool(a.get("is_default")),
        })
    if cleaned and not any(a["is_default"] for a in cleaned):
        cleaned[0]["is_default"] = True
    return cleaned


def set_addresses(user, addresses):
    ext = get_extended(user)
    ext["addresses"] = addresses
    set_extended(user, ext)


def get_profile_extra(user):
    ext = get_extended(user)
    extra = ext.get("profile") if isinstance(ext.get("profile"), dict) else {}
    return {
        "suffix": clean_text(str(extra.get("suffix") or ""))[:20],
        "date_of_birth": clean_text(str(extra.get("date_of_birth") or ""))[:10],
        "sex": clean_text(str(extra.get("sex") or ""))[:30],
        "civil_status": clean_text(str(extra.get("civil_status") or ""))[:30],
        "nationality": clean_text(str(extra.get("nationality") or "Filipino"))[:60],
        "profile_picture": clean_text(str(extra.get("profile_picture") or ""))[:255],
        "contact_verification_status": clean_text(str(extra.get("contact_verification_status") or "unverified"))[:20] or "unverified",
    }


def set_profile_extra(user, extra):
    ext = get_extended(user)
    ext["profile"] = extra
    set_extended(user, ext)


def get_login_activity(user):
    ext = get_extended(user)
    logs = ext.get("login_activity")
    if not isinstance(logs, list):
        logs = []
    return logs[:20]


def record_login_activity(user, ip_address=None, user_agent=None):
    ext = get_extended(user)
    logs = ext.get("login_activity")
    if not isinstance(logs, list):
        logs = []
    logs.insert(0, {
        "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": (ip_address or "")[:64],
        "user_agent": (user_agent or "")[:255],
    })
    ext["login_activity"] = logs[:20]
    ext["last_login_at"] = logs[0]["at"]
    set_extended(user, ext)


def get_last_login(user):
    ext = get_extended(user)
    return ext.get("last_login_at") or ""


def profile_picture_url(user):
    extra = get_profile_extra(user)
    pic = extra.get("profile_picture")
    if not pic:
        return None
    import os
    from flask import url_for
    static_root = current_app.static_folder or os.path.join(current_app.root_path, "static")
    candidates = [
        os.path.join(static_root, "uploads", "profile_pictures", pic),
        os.path.join(current_app.root_path, "..", "static", "uploads", "profile_pictures", pic),
    ]
    file_path = next((p for p in candidates if os.path.exists(p)), candidates[0])
    ver = int(os.path.getmtime(file_path)) if os.path.exists(file_path) else 0
    try:
        return url_for("static", filename=f"uploads/profile_pictures/{pic}", v=ver)
    except Exception:
        return f"/static/uploads/profile_pictures/{pic}?v={ver}"


def save_profile_picture(user, file_storage):
    if not file_storage or not file_storage.filename:
        return None, "No file selected."
    filename = secure_filename(file_storage.filename)
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in PROFILE_PIC_EXTS:
        return None, "Profile picture must be JPG, PNG, or WEBP."
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > PROFILE_PIC_MAX:
        return None, "Profile picture must be 2MB or smaller."
    import os, secrets
    static_root = current_app.static_folder or os.path.join(current_app.root_path, "static")
    upload_dir = os.path.join(static_root, "uploads", "profile_pictures")
    os.makedirs(upload_dir, exist_ok=True)
    stored = f"user_{user.user_id}_{secrets.token_hex(8)}{ext}"
    dest = os.path.join(upload_dir, stored)
    file_storage.save(dest)
    # also place in BASE_DIR/static for safety if app serves from different root
    alt_static = os.path.join(os.path.dirname(current_app.root_path), "static", "uploads", "profile_pictures")
    if os.path.abspath(alt_static) != os.path.abspath(upload_dir):
        try:
            os.makedirs(alt_static, exist_ok=True)
            import shutil
            shutil.copy2(dest, os.path.join(alt_static, stored))
        except Exception:
            pass
    # remove old
    old = get_profile_extra(user).get("profile_picture")
    if old and old != stored:
        for d in [upload_dir, alt_static]:
            try:
                os.remove(os.path.join(d, old))
            except OSError:
                pass
    return stored, None


def validate_profile(form, user):
    errors = {}
    first_name, e = validate_name(form.get("first_name"), "First name"); errors.update({"first_name": e} if e else {})
    middle_name, e = validate_name(form.get("middle_name"), "Middle name", required=False); errors.update({"middle_name": e} if e else {})
    last_name, e = validate_name(form.get("last_name"), "Last name"); errors.update({"last_name": e} if e else {})
    suffix = clean_text(form.get("suffix"))[:20]
    dob = clean_text(form.get("date_of_birth"))
    sex = clean_text(form.get("sex"))
    civil = clean_text(form.get("civil_status"))
    nationality = clean_text(form.get("nationality")) or "Filipino"
    email = normalize_email(form.get("email"))
    contact = normalize_contact_number(form.get("contact_number"))
    contact_digits = contact[1:] if contact.startswith("+") else contact

    if not email:
        errors["email"] = "Email address is required."
    elif len(email) > 255 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        errors["email"] = "Enter a valid email address."
    if not contact:
        errors["contact_number"] = "Contact number is required."
    elif not contact_digits.isdigit() or not 10 <= len(contact_digits) <= 15:
        errors["contact_number"] = "Enter a valid contact number."
    if dob:
        try:
            d = datetime.strptime(dob, "%Y-%m-%d").date()
            if d.year < 1900 or d > datetime.now().date():
                errors["date_of_birth"] = "Enter a valid date of birth."
        except ValueError:
            errors["date_of_birth"] = "Enter a valid date of birth."
    if sex and sex not in SEX_OPTIONS:
        errors["sex"] = "Select a valid sex option."
    if civil and civil not in CIVIL_STATUS_OPTIONS:
        errors["civil_status"] = "Select a valid civil status."
    if len(nationality) > 60:
        errors["nationality"] = "Nationality must be 60 characters or fewer."

    cleaned = {
        "first_name": first_name or "", "middle_name": middle_name or "", "last_name": last_name or "",
        "suffix": suffix, "date_of_birth": dob, "sex": sex, "civil_status": civil, "nationality": nationality,
        "email": email, "contact_number": contact,
    }
    return cleaned, errors


def validate_address(form):
    errors = {}
    fields = ["house_unit", "street", "barangay", "city", "province", "region", "zip_code"]
    cleaned = {k: clean_text(form.get(k))[:120] for k in fields}
    cleaned["zip_code"] = clean_text(form.get("zip_code"))[:10]
    for req in ["barangay", "city", "province", "region"]:
        if not cleaned[req]:
            errors[req] = f"{req.replace('_',' ').title()} is required."
    if cleaned["zip_code"] and not re.fullmatch(r"\d{4,10}", cleaned["zip_code"]):
        errors["zip_code"] = "Enter a valid ZIP code."
    return cleaned, errors
