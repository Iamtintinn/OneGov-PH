"""Administrator confirmation of passport documents and physical requirements."""

from datetime import date, datetime, timedelta
from secrets import token_hex

from app.services.application_forms import specification_for
from app.services.application_service import field_map, read_details, write_details
from app.services.passport_delivery import DELIVERY, PICKUP, fulfillment_method

PHYSICAL_KEY = "physical_requirements"
STATUS_KEY = "passport_status_key"


def _specification(application):
    return specification_for(application.service, field_map(application)) or {}


def is_passport_application(application):
    return _specification(application).get("kind") == "passport"


def _config(application):
    return _specification(application).get("physical_requirements_confirmation") or {}


def physical_requirements(application):
    details = read_details(application)
    value = details.get(PHYSICAL_KEY)
    return value if isinstance(value, dict) else {}


def admin_status_options(application):
    return list(_specification(application).get("admin_status_options") or ())


def _status_option(application, key):
    return next(
        (item for item in admin_status_options(application) if item.get("key") == key),
        None,
    )


def current_status_key(application):
    options = admin_status_options(application)
    keys = {item.get("key") for item in options}
    stored = read_details(application).get(STATUS_KEY)
    if stored in keys:
        return stored
    legacy = application.application_status
    if legacy == "completed":
        return "completed"
    return next(
        (item.get("key") for item in options if item.get("legacy_status") == legacy),
        "",
    )


def resolve_status_update(application, key):
    option = _status_option(application, key)
    if option is None:
        return None, None
    return option.get("legacy_status"), option.get("label")


def status_key_for_legacy(application, legacy):
    if legacy == "completed":
        return "completed"
    return next(
        (
            item.get("key")
            for item in admin_status_options(application)
            if item.get("legacy_status") == legacy
        ),
        "",
    )


def status_label(application):
    option = _status_option(application, current_status_key(application))
    return (option or {}).get("label") or ""


def is_confirmed(application):
    return bool(physical_requirements(application).get("confirmed"))


def gate_message(application):
    if not is_passport_application(application):
        return ""
    config = _config(application)
    if not config or is_confirmed(application):
        return ""
    return config.get("gate_message") or (
        "Confirm the applicant's documents and physical requirements before updating the application status."
    )


def add_business_days(start, days):
    current = start.date() if isinstance(start, datetime) else start
    remaining = max(0, int(days or 0))
    while remaining:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def _pickup_id(application, prefix):
    return f"{prefix}-{application.application_id:05d}-{token_hex(3).upper()}"


def confirm(application, user):
    method = fulfillment_method(application)
    if method not in {PICKUP, DELIVERY}:
        return None

    existing = physical_requirements(application)
    if existing.get("confirmed"):
        return existing

    config = _config(application)
    lead_days = int(config.get("pickup_lead_business_days") or 7)
    now = datetime.now().replace(microsecond=0)
    payload = {
        "confirmed": True,
        "confirmed_by": user.user_id,
        "confirmed_by_name": user.full_name,
        "confirmed_at": now.isoformat(),
        "confirmed_at_label": now.strftime("%d %b %Y, %I:%M %p"),
        "fulfillment_method": method,
        "lead_business_days": lead_days,
        "source_date": application.submission_date.date().isoformat()
        if isinstance(application.submission_date, datetime)
        else str(application.submission_date),
    }

    if method == PICKUP:
        pickup_date = add_business_days(application.submission_date, lead_days)
        payload["pickup_id"] = _pickup_id(application, config.get("pickup_id_prefix") or "PU")
        payload["pickup_date"] = pickup_date.isoformat()
        payload["pickup_date_label"] = pickup_date.strftime("%d %b %Y")

    details = read_details(application)
    details[PHYSICAL_KEY] = payload
    write_details(application, details, commit=False)
    return payload


def summary(application):
    if not is_passport_application(application):
        return None

    config = _config(application)
    record = physical_requirements(application)
    method = fulfillment_method(application)
    delivery = read_details(application).get("delivery") or {}
    if method == PICKUP:
        method_label = "Show up at DFA office to submit documents"
    elif method == DELIVERY:
        method_label = "Home delivery"
    else:
        method_label = "Not selected"

    return {
        "label": config.get("label") or "Confirm physical requirements",
        "help": config.get("help") or "",
        "gate_message": gate_message(application),
        "requirements": list(config.get("requirements") or ()),
        "requires_confirmation": True,
        "confirmed": bool(record.get("confirmed")),
        "fulfillment_method": method,
        "fulfillment_label": method_label,
        "pickup_location": delivery.get("pickup_location") or "",
        "confirmed_by_name": record.get("confirmed_by_name") or "",
        "confirmed_at_label": record.get("confirmed_at_label") or "",
        "pickup_id": record.get("pickup_id") or "",
        "pickup_date": record.get("pickup_date") or "",
        "pickup_date_label": record.get("pickup_date_label") or "",
        "lead_business_days": record.get("lead_business_days") or config.get("pickup_lead_business_days") or 7,
        "source_date": record.get("source_date") or "",
    }
