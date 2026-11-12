"""Status history and cancellation for an application the citizen owns."""

from datetime import datetime

from sqlalchemy import update

from app import db
from app.models.application import Application, ApplicationEvent
from app.models.notification import Notification
from app.utils.validators import clean_text

CLOSED_STATUSES = frozenset({"cancelled", "completed", "rejected"})


def _now():
    return datetime.now().replace(microsecond=0)


def add_event(application, user_id, new_status, description, previous_status, recorded_at):
    db.session.add(
        ApplicationEvent(
            application_id=application.application_id,
            previous_status=previous_status,
            new_status=new_status,
            update_description=description[:500],
            updated_by=user_id,
            recorded_at=recorded_at,
        )
    )


def events_by_application(application_ids):
    grouped = {application_id: [] for application_id in application_ids}
    if not application_ids:
        return grouped
    events = db.session.scalars(
        db.select(ApplicationEvent)
        .where(ApplicationEvent.application_id.in_(application_ids))
        .order_by(ApplicationEvent.recorded_at.desc(), ApplicationEvent.tracking_id.desc())
    ).all()
    for event in events:
        grouped.setdefault(event.application_id, []).append(event)
    return grouped


def cancel_application(application, user, reason):
    """Cancel one owned application and keep the reason in its history."""
    cleaned = clean_text(reason)
    if application.application_status == "draft":
        return "draft"
    if not cleaned:
        return "Enter the reason for cancelling this application."
    if len(cleaned) > 500:
        return "Use no more than 500 characters."
    if application.application_status in CLOSED_STATUSES:
        return "This application can no longer be cancelled."
    now = _now()
    previous = application.application_status
    updated = db.session.execute(
        update(Application)
        .where(
            Application.application_id == application.application_id,
            Application.applicant_id == user.user_id,
            Application.application_status == previous,
        )
        .values(
            application_status="cancelled",
            cancellation_reason=cleaned,
            last_updated=now,
        )
    )
    if updated.rowcount != 1:
        db.session.rollback()
        return "This application could not be cancelled. Refresh the page and try again."
    add_event(
        application,
        user.user_id,
        "cancelled",
        f"Cancelled by the citizen. Reason: {cleaned}",
        previous,
        now,
    )
    db.session.add(
        Notification(
            user_id=user.user_id,
            notification_title="Application cancelled",
            notification_message=(
                f"Your {application.service.service_name} request {application.tracking_number} "
                "was cancelled in OneGov PH. This does not withdraw a filing from a government agency."
            ),
            notification_type="application",
            read_status="unread",
            created_date=now,
        )
    )
    db.session.commit()
    return None
