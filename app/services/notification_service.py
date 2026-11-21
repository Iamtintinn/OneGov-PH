"""Create notifications while respecting citizen notification preferences."""

from datetime import datetime

from app import db
from app.models.notification import Notification
from app.services.citizen_settings_service import get_notification_prefs

TYPE_TO_CATEGORY = {
    "application": "application_updates",
    "payment": "payment_notifications",
    "appointment": "application_updates",
    "account": "application_updates",
    "system": "government_announcements",
    "document": "document_processing_updates",
    "delivery": "delivery_updates",
}

# Some services pass category directly
CATEGORY_ALIASES = {
    "application_updates": "application_updates",
    "payment_notifications": "payment_notifications",
    "document_processing_updates": "document_processing_updates",
    "delivery_updates": "delivery_updates",
    "government_announcements": "government_announcements",
}


def _category_for(notification_type, category=None):
    if category and category in CATEGORY_ALIASES:
        return category
    return TYPE_TO_CATEGORY.get((notification_type or "").lower(), "application_updates")


def should_notify(user, notification_type, channel="in_app", category=None):
    """Return True if user allows this channel for the notification category."""
    try:
        prefs = get_notification_prefs(user)
    except Exception:
        return True
    cat = _category_for(notification_type, category)
    cat_prefs = prefs.get(cat) or {}
    return bool(cat_prefs.get(channel, True))


def create_notification(user, *, title, message, notification_type="system", category=None):
    """Create in-app notification if user preference allows it. Returns Notification or None."""
    if user is None:
        return None
    if not should_notify(user, notification_type, "in_app", category=category):
        return None
    notice = Notification(
        user_id=user.user_id,
        notification_title=str(title)[:200],
        notification_message=str(message),
        notification_type=notification_type if notification_type in {"application","payment","appointment","account","system"} else "system",
        read_status="unread",
        created_date=datetime.now().replace(microsecond=0),
    )
    db.session.add(notice)
    return notice


def create_notification_for_user_id(user_id, *, title, message, notification_type="system", category=None):
    from app.models.user import User
    user = db.session.get(User, user_id)
    return create_notification(user, title=title, message=message, notification_type=notification_type, category=category)
