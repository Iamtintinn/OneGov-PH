"""Demonstration home-delivery details for barangay clearance requests.

Delivery information is stored on the existing application details JSON blob so
the current database structure stays unchanged. No courier is dispatched.
"""

from datetime import datetime
from decimal import Decimal

from app import db
from app.models.notification import Notification
from app.services.application_service import read_details, write_details
from app.utils.validators import clean_text, normalize_contact_number

REGION = "National Capital Region"
PROVINCE = "Metro Manila"
CITY = "Quezon City"

# Home delivery costs ₱50.00; the clearance fee stays at ₱50.00.
DELIVERY_FEE = Decimal("50.00")

DEMO_BARANGAYS = (
    {"name": "Commonwealth", "latitude": 14.6986, "longitude": 121.0850},
    {"name": "Batasan Hills", "latitude": 14.6786, "longitude": 121.0965},
    {"name": "Holy Spirit", "latitude": 14.6850, "longitude": 121.0770},
    {"name": "Fairview", "latitude": 14.7100, "longitude": 121.0600},
    {"name": "Payatas", "latitude": 14.7110, "longitude": 121.1050},
)

DEFAULT_LAT = 14.5995
DEFAULT_LNG = 120.9842

LAT_MIN, LAT_MAX = 4.5, 21.5
LNG_MIN, LNG_MAX = 116.0, 127.0


def _now():
    return datetime.now().replace(microsecond=0)


def barangay_by_name(name):
    key = clean_text(name).lower()
    return next((item for item in DEMO_BARANGAYS if item["name"].lower() == key), None)


def barangay_center(name):
    item = barangay_by_name(name)
    if item is None:
        return None
    return item["latitude"], item["longitude"]


def delivery_for(application):
    details = read_details(application)
    delivery = details.get("delivery")
    if not isinstance(delivery, dict):
        return None
    return delivery


def delivery_ready(application):
    return delivery_for(application) is not None


def delivery_address(delivery):
    if not delivery:
        return ""
    parts = [
        delivery.get("house_number"),
        delivery.get("street"),
        delivery.get("subdivision"),
        delivery.get("barangay"),
        delivery.get("city"),
        delivery.get("province"),
        delivery.get("region"),
    ]
    return ", ".join(part for part in (clean_text(item) for item in parts) if part)


def delivery_values(application):
    delivery = delivery_for(application) or {}
    latitude = delivery.get("latitude") or ""
    longitude = delivery.get("longitude") or ""
    return {
        "recipient_name": delivery.get("recipient_name") or "",
        "contact_number": delivery.get("contact_number") or "",
        "region": delivery.get("region") or REGION,
        "province": delivery.get("province") or PROVINCE,
        "city": delivery.get("city") or CITY,
        "barangay": delivery.get("barangay") or "",
        "house_number": delivery.get("house_number") or "",
        "street": delivery.get("street") or "",
        "subdivision": delivery.get("subdivision") or "",
        "landmark": delivery.get("landmark") or "",
        "latitude": latitude,
        "longitude": longitude,
        "location_confirmed": bool(latitude and longitude),
        "origin_barangay": delivery.get("origin_barangay") or "",
        "origin_address": delivery.get("origin_address") or "",
        "origin_latitude": delivery.get("origin_latitude") or "",
        "origin_longitude": delivery.get("origin_longitude") or "",
        "origin_location_confirmed": bool(
            delivery.get("origin_latitude") and delivery.get("origin_longitude")
        ),
    }


def _as_float(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def validate_delivery_form(form):
    errors = {}

    recipient = clean_text(form.get("recipient_name"))
    if not recipient:
        errors["recipient_name"] = "Enter the recipient's full name."
    elif len(recipient) > 200:
        errors["recipient_name"] = "Use 200 characters or fewer for the recipient name."

    contact = normalize_contact_number(form.get("contact_number"))
    contact_digits = contact[1:] if contact.startswith("+") else contact
    if not contact:
        errors["contact_number"] = "Enter a contact number."
    elif not contact_digits.isdigit() or not 10 <= len(contact_digits) <= 15:
        errors["contact_number"] = "Enter a valid contact number."

    barangay = clean_text(form.get("barangay"))
    if not barangay:
        errors["barangay"] = "Enter the barangay."
    elif len(barangay) > 200:
        errors["barangay"] = "Use 200 characters or fewer for the barangay."

    house_number = clean_text(form.get("house_number"))
    if not house_number:
        errors["house_number"] = "Enter the house or building number."
    elif len(house_number) > 120:
        errors["house_number"] = "Use 120 characters or fewer."

    street = clean_text(form.get("street"))
    if not street:
        errors["street"] = "Enter the street."
    elif len(street) > 200:
        errors["street"] = "Use 200 characters or fewer."

    subdivision = clean_text(form.get("subdivision"))[:200]
    landmark = clean_text(form.get("landmark"))[:200]

    origin_barangay = clean_text(form.get("origin_barangay"))[:200]
    if not origin_barangay:
        errors["origin_barangay"] = "Enter the barangay where the clearance is being requested."

    origin_address = clean_text(form.get("origin_address"))[:300]
    if not origin_address:
        errors["origin_address"] = "Enter the starting address."

    origin_latitude = _as_float(form.get("origin_latitude"))
    origin_longitude = _as_float(form.get("origin_longitude"))
    if origin_latitude is None or origin_longitude is None:
        errors["origin_latitude"] = "Pin the starting location on the map."
    elif not LAT_MIN <= origin_latitude <= LAT_MAX:
        errors["origin_latitude"] = "The pinned latitude is outside the supported area."
    elif not LNG_MIN <= origin_longitude <= LNG_MAX:
        errors["origin_longitude"] = "The pinned longitude is outside the supported area."

    origin_confirmed = origin_latitude is not None and origin_longitude is not None

    latitude = _as_float(form.get("latitude"))
    longitude = _as_float(form.get("longitude"))
    if latitude is None or longitude is None:
        errors["latitude"] = "Pin the delivery location on the map."
    elif not LAT_MIN <= latitude <= LAT_MAX:
        errors["latitude"] = "The pinned latitude is outside the supported area."
    elif not LNG_MIN <= longitude <= LNG_MAX:
        errors["longitude"] = "The pinned longitude is outside the supported area."

    confirmed = latitude is not None and longitude is not None

    values = {
        "recipient_name": recipient,
        "contact_number": contact,
        "region": REGION,
        "province": PROVINCE,
        "city": CITY,
        "barangay": barangay,
        "house_number": house_number,
        "street": street,
        "subdivision": subdivision,
        "landmark": landmark,
        "latitude": f"{latitude:.7f}" if latitude is not None else "",
        "longitude": f"{longitude:.7f}" if longitude is not None else "",
        "location_confirmed": confirmed,
        "origin_barangay": origin_barangay,
        "origin_address": origin_address,
        "origin_latitude": f"{origin_latitude:.7f}" if origin_latitude is not None else "",
        "origin_longitude": f"{origin_longitude:.7f}" if origin_longitude is not None else "",
        "origin_location_confirmed": origin_confirmed,
    }
    return values, errors


def save_delivery(application, user, values):
    if not values.get("latitude") or not values.get("longitude"):
        return "Pin the delivery location on the map."
    if not values.get("origin_latitude") or not values.get("origin_longitude"):
        return "Pin the starting location on the map."

    payload = {
        "recipient_name": values.get("recipient_name") or "",
        "contact_number": values.get("contact_number") or "",
        "region": values.get("region") or REGION,
        "province": values.get("province") or PROVINCE,
        "city": values.get("city") or CITY,
        "barangay": values.get("barangay") or "",
        "house_number": values.get("house_number") or "",
        "street": values.get("street") or "",
        "subdivision": values.get("subdivision") or "",
        "landmark": values.get("landmark") or "",
        "latitude": str(values.get("latitude") or ""),
        "longitude": str(values.get("longitude") or ""),
        "origin_barangay": values.get("origin_barangay") or "",
        "origin_address": values.get("origin_address") or "",
        "origin_latitude": str(values.get("origin_latitude") or ""),
        "origin_longitude": str(values.get("origin_longitude") or ""),
        "saved_at": _now().isoformat(),
    }
    payload["address"] = delivery_address(payload)

    details = read_details(application)
    details["delivery"] = payload
    write_details(application, details, commit=False)

    now = _now()
    db.session.add(
        Notification(
            user_id=user.user_id,
            notification_title="Delivery details saved",
            notification_message=(
                "Your Barangay Clearance home-delivery route, starting location, "
                f"and recipient details were saved for {payload['address'] or 'the pinned location'}."
            ),
            notification_type="application",
            read_status="unread",
            created_date=now,
        )
    )
    db.session.commit()
    return None
