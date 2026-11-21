"""Demonstration home-delivery details for birth certificate requests."""

from datetime import datetime
from decimal import Decimal

from app import db
from app.models.notification import Notification
from app.services.notification_service import should_notify
from app.services.application_service import read_details, write_details
from app.utils.validators import clean_text, normalize_contact_number

REGION = "National Capital Region"
PROVINCE = "Metro Manila"
CITY = "Quezon City"

DELIVERY_FEE = Decimal("0.00")

LAT_MIN, LAT_MAX = 4.5, 21.5
LNG_MIN, LNG_MAX = 116.0, 127.0

DEFAULT_LAT = 14.5995
DEFAULT_LNG = 120.9842

ORIGIN_NAME = "PSA Central Office / CRS"
ORIGIN_ADDRESS = "PSA Complex, East Avenue, Diliman, Quezon City, Metro Manila."
ORIGIN_LAT = 14.6392
ORIGIN_LNG = 121.0437

DEMO_BARANGAYS = (
    {"name": "Commonwealth", "latitude": 14.6986, "longitude": 121.0850},
    {"name": "Batasan Hills", "latitude": 14.6786, "longitude": 121.0965},
    {"name": "Holy Spirit", "latitude": 14.6850, "longitude": 121.0770},
    {"name": "Fairview", "latitude": 14.7100, "longitude": 121.0600},
    {"name": "Payatas", "latitude": 14.7110, "longitude": 121.1050},
)


def _now():
    return datetime.now().replace(microsecond=0)


def birth_by_name(name):
    key = clean_text(name).lower()
    return next((item for item in DEMO_BARANGAYS if item["name"].lower() == key), None)


def birth_center(name):
    item = birth_by_name(name)
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
        "origin_barangay": ORIGIN_NAME,
        "origin_address": ORIGIN_ADDRESS,
        "origin_latitude": f"{ORIGIN_LAT:.7f}",
        "origin_longitude": f"{ORIGIN_LNG:.7f}",
        "origin_location_confirmed": True,
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

    latitude = _as_float(form.get("latitude"))
    longitude = _as_float(form.get("longitude"))
    if latitude is None or longitude is None:
        errors["latitude"] = "Pin the delivery location on the map."
    elif not LAT_MIN <= latitude <= LAT_MAX:
        errors["latitude"] = "The pinned latitude is outside the supported area."
    elif not LNG_MIN <= longitude <= LNG_MAX:
        errors["longitude"] = "The pinned longitude is outside the supported area."

    confirmed = str(form.get("delivery_location_confirmed") or "").strip() == "yes"
    if not confirmed:
        errors["location_confirmed"] = "Confirm the pinned delivery location before continuing."

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
        "origin_barangay": ORIGIN_NAME,
        "origin_address": ORIGIN_ADDRESS,
        "origin_latitude": f"{ORIGIN_LAT:.7f}",
        "origin_longitude": f"{ORIGIN_LNG:.7f}",
        "origin_location_confirmed": True,
    }
    return values, errors


def save_delivery(application, user, values):
    if not values.get("latitude") or not values.get("longitude"):
        return "Pin the delivery location on the map."

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
        "origin_barangay": ORIGIN_NAME,
        "origin_address": ORIGIN_ADDRESS,
        "origin_latitude": f"{ORIGIN_LAT:.7f}",
        "origin_longitude": f"{ORIGIN_LNG:.7f}",
        "saved_at": _now().isoformat(),
    }
    payload["address"] = delivery_address(payload)

    details = read_details(application)
    details["delivery"] = payload
    write_details(application, details, commit=False)

    now = _now()
    _n_user = db.session.get(__import__('app.models.user',fromlist=['User']).User, user.user_id) if not isinstance(user.user_id, __import__('app.models.user',fromlist=['User']).User) else user.user_id
    if should_notify(_n_user, "application", 'in_app'):
        db.session.add(Notification(
        user_id=user.user_id,
        notification_title="Delivery details saved",
        notification_message=(
        "Your Birth Certificate home-delivery location and recipient details "
        f"were saved for {payload['address'] or 'the pinned location'}."
        ),
        notification_type="application",
        read_status="unread",
        created_date=now,
        ))
    db.session.commit()
    return None
