"""Demonstration home-delivery details for CENOMAR requests."""

from datetime import datetime

from app import db
from app.models.notification import Notification
from app.services.application_service import read_details, write_details
from app.services.birth_delivery import (
    CITY,
    DEFAULT_LAT,
    DEFAULT_LNG,
    DELIVERY_FEE,
    DEMO_BARANGAYS,
    PROVINCE,
    REGION,
    birth_center as cenomar_center,
    delivery_address,
    delivery_for,
    delivery_ready,
    delivery_values,
    validate_delivery_form,
)


def _now():
    return datetime.now().replace(microsecond=0)


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
                "Your CENOMAR home-delivery location and recipient details "
                f"were saved for {payload['address'] or 'the pinned location'}."
            ),
            notification_type="application",
            read_status="unread",
            created_date=now,
        )
    )
    db.session.commit()
    return None
