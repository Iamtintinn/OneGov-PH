"""Administrator confirmation of Senior Citizen ID documents and physical appearance."""

from datetime import datetime, timedelta
from secrets import token_hex

from app.services.application_forms import specification_for
from app.services.application_service import document_rules, field_map, read_details, write_details
from app.services.senior_delivery import DELIVERY, PICKUP, fulfillment_method

CONFIRMATION_KEY = "senior_confirmation"
STATUS_KEY = "senior_status_key"


def _specification(application):
    return specification_for(application.service, field_map(application)) or {}


def is_senior_application(application):
    return _specification(application).get("kind") == "senior"


def _config(application):
    return _specification(application).get("senior_confirmation") or {}


def confirmation(application):
    details = read_details(application)
    value = details.get(CONFIRMATION_KEY)
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
    return bool(confirmation(application).get("confirmed"))


def required_documents(application):
    spec = _specification(application)
    if not spec or spec.get("checklist"):
        return []
    values = field_map(application)
    return [rule for rule in document_rules(spec, values) if rule.get("required")]


def documents_ready(application):
    rules = required_documents(application)
    if not rules:
        return False
    uploaded = {
        item.requirement_name
        for item in application.requirements
        if item.uploaded_file
    }
    return all(rule.get("key") in uploaded for rule in rules)


def gate_message(application):
    if not is_senior_application(application):
        return ""
    config = _config(application)
    if not config or is_confirmed(application):
        return ""
    return config.get("gate_message") or (
        "Confirm the applicant's submitted documents or physical appearance before updating the application status or dispatch status."
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


def confirm(application, user, physical_appearance=False, remarks=""):
    if not is_senior_application(application):
        return None, "Confirmation is only available for Senior Citizen ID applications."
    if is_confirmed(application):
        return confirmation(application), None

    method = fulfillment_method(application)
    if method not in {PICKUP, DELIVERY}:
        return None, "The applicant must choose pickup or home delivery before confirmation."

    has_documents = documents_ready(application)
    if not has_documents and not physical_appearance:
        return None, "Confirm that all required documents were submitted or mark physical appearance as complete."

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
        "documents_submitted": bool(has_documents),
        "physical_appearance": bool(physical_appearance),
        "remarks": remarks or "",
        "lead_business_days": lead_days,
        "source_date": application.submission_date.date().isoformat()
        if isinstance(application.submission_date, datetime)
        else str(application.submission_date),
    }

    delivery = read_details(application).get("delivery") or {}
    if method == PICKUP:
        pickup_date = add_business_days(application.submission_date, lead_days)
        payload["pickup_id"] = _pickup_id(application, config.get("pickup_id_prefix") or "OSCA-PU")
        payload["pickup_date"] = pickup_date.isoformat()
        payload["pickup_date_label"] = pickup_date.strftime("%d %b %Y")
        payload["pickup_location"] = delivery.get("pickup_location") or ""

    details = read_details(application)
    details[CONFIRMATION_KEY] = payload
    write_details(application, details, commit=False)
    return payload, None


def summary(application):
    if not is_senior_application(application):
        return None

    config = _config(application)
    record = confirmation(application)
    method = fulfillment_method(application)
    if method == PICKUP:
        method_label = "Show up at OSCA office to submit documents"
    elif method == DELIVERY:
        method_label = "Home delivery"
    else:
        method_label = "Not selected"

    return {
        "label": config.get("label") or "Confirm documents and physical appearance",
        "help": config.get("help") or "",
        "gate_message": gate_message(application),
        "requirements": list(config.get("requirements") or ()),
        "confirmed": bool(record.get("confirmed")),
        "fulfillment_method": method,
        "fulfillment_label": method_label,
        "documents_ready": documents_ready(application),
        "documents_label": "Submitted" if documents_ready(application) else "Pending",
        "physical_appearance": bool(record.get("physical_appearance")),
        "pickup_location": record.get("pickup_location") or "",
        "confirmed_by_name": record.get("confirmed_by_name") or "",
        "confirmed_at_label": record.get("confirmed_at_label") or "",
        "pickup_id": record.get("pickup_id") or "",
        "pickup_date": record.get("pickup_date") or "",
        "pickup_date_label": record.get("pickup_date_label") or "",
        "lead_business_days": record.get("lead_business_days") or config.get("pickup_lead_business_days") or 7,
        "source_date": record.get("source_date") or "",
    }
