"""Administrator confirmation of NBI documents and physical requirements."""

from datetime import datetime, timedelta
from secrets import token_hex

from app.services.application_forms import specification_for
from app.services.application_service import field_map, read_details, write_details
from app.services.nbi_delivery import DELIVERY, PICKUP, fulfillment_method
from app.services.nbi_scheduling import appointment_for

PHYSICAL_KEY = "nbi_physical_requirements"
STATUS_KEY = "nbi_status_key"


def _specification(application):
    return specification_for(application.service, field_map(application)) or {}


def is_nbi_application(application):
    return _specification(application).get("kind") == "nbi"


def _config(application):
    return _specification(application).get("physical_requirements_confirmation") or {}


def physical_requirements(application):
    details = read_details(application)
    value = details.get(PHYSICAL_KEY)
    return value if isinstance(value, dict) else {}


def is_confirmed(application):
    return bool(physical_requirements(application).get("confirmed"))


def schedule_recorded(application):
    return appointment_for(application) is not None


def gate_message(application):
    if not is_nbi_application(application) or is_confirmed(application):
        return ""
    if not schedule_recorded(application):
        return ""
    return _config(application).get("gate_message") or (
        "Confirm the applicant's documents and physical requirements before updating the application status or dispatch status."
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
        return None, "The applicant must choose pickup or home delivery before confirmation."
    if not schedule_recorded(application):
        return None, "The applicant must have a recorded appointment schedule before confirmation."

    existing = physical_requirements(application)
    if existing.get("confirmed"):
        return existing, None

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
        payload["pickup_id"] = _pickup_id(application, config.get("pickup_id_prefix") or "NBI-PU")
        payload["pickup_date"] = pickup_date.isoformat()
        payload["pickup_date_label"] = pickup_date.strftime("%d %b %Y")

    details = read_details(application)
    details[PHYSICAL_KEY] = payload
    write_details(application, details, commit=False)
    return payload, None


def summary(application):
    if not is_nbi_application(application):
        return None

    config = _config(application)
    record = physical_requirements(application)
    method = fulfillment_method(application)
    delivery = read_details(application).get("delivery") or {}
    if method == PICKUP:
        method_label = "Show up at NBI Clearance Center to submit documents"
    elif method == DELIVERY:
        method_label = "Home delivery"
    else:
        method_label = "Not selected"

    return {
        "label": config.get("label") or "Confirm physical requirements",
        "help": config.get("help") or "",
        "gate_message": gate_message(application),
        "requirements": list(config.get("requirements") or ()),
        "requires_confirmation": bool(_config(application)),
        "schedule_recorded": schedule_recorded(application),
        "confirmed": bool(record.get("confirmed")),
        "fulfillment_method": method,
        "fulfillment_label": method_label,
        "pickup_location": delivery.get("pickup_location") or "",
        "pickup_address": delivery.get("pickup_address") or "",
        "confirmed_by_name": record.get("confirmed_by_name") or "",
        "confirmed_at_label": record.get("confirmed_at_label") or "",
        "pickup_id": record.get("pickup_id") or "",
        "pickup_date": record.get("pickup_date") or "",
        "pickup_date_label": record.get("pickup_date_label") or "",
        "lead_business_days": record.get("lead_business_days") or config.get("pickup_lead_business_days") or 7,
        "source_date": record.get("source_date") or "",
    }
