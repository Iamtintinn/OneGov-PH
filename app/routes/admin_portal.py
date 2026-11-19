"""Administrator-facing copies of the citizen portal features.

The views and templates are the same ones used by the citizen portal, but the
URLs live under /admin/portal. This keeps administrators inside the unified
Admin Console while avoiding duplicated application logic.
"""

import copy
import json
from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app import db
from app.models.application import Application, ApplicationEvent
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.user import User
from app.routes import citizen
from app.routes.applications import register as register_application_routes
from app.routes.routing import fetch_route
from app.services.application_forms import specification_for
from app.services.application_service import field_map, read_details
from app.utils.access import (
    application_or_404,
    visible_application_query,
    visible_payment_query,
)
from app.utils.decorators import admin_console_required
from app.utils.validators import clean_text, normalize_contact_number

admin_portal_bp = Blueprint("admin_portal", __name__)


def _confirmation_gate(application):
    from app.services.passport_admin import gate_message
    from app.services.senior_admin import gate_message as senior_gate_message

    return gate_message(application) or senior_gate_message(application)


LEGACY_STATUS_LABELS = {
    "draft": "Draft",
    "submitted": "Submitted",
    "under_review": "Under review",
    "pending_documents": "Corrections requested",
    "for_payment": "For payment",
    "paid": "Paid",
    "scheduled": "Scheduled",
    "processing": "Processing",
    "ready_for_release": "Ready for release",
    "completed": "Completed",
    "rejected": "Rejected",
    "cancelled": "Cancelled",
    "approved": "Approved",
    "for_biometrics": "For biometrics",
    "with_hit": "With hit",
}

ADMIN_PROCESSING_STATUSES = (
    ("application_submitted", "Application Submitted", "submitted"),
    ("payment_confirmed", "Payment Confirmed", "paid"),
    ("requirements_under_review", "Requirements Under Review", "under_review"),
    ("rejected", "Rejected", "rejected"),
    ("requirements_verified", "Requirements Verified", "approved"),
    ("processing_document", "Processing Document", "processing"),
    ("document_approved", "Document Approved", "approved"),
    ("ready_for_dispatch", "Ready for Dispatch", "ready_for_release"),
    ("completed", "Completed", "completed"),
)
PASSPORT_PROCESSING_STATUSES = (
    ("cancelled", "Cancelled", "cancelled"),
    ("rejected", "Rejected", "rejected"),
    ("released_claimed", "Released / Claimed", "completed"),
)
ADMIN_PROCESSING_BY_KEY = {
    key: {"key": key, "label": label, "legacy_status": legacy}
    for key, label, legacy in ADMIN_PROCESSING_STATUSES + PASSPORT_PROCESSING_STATUSES
}
ADMIN_PROCESSING_KEY_BY_LEGACY = {}
for _key, _label, _legacy in ADMIN_PROCESSING_STATUSES:
    ADMIN_PROCESSING_KEY_BY_LEGACY.setdefault(_legacy, _key)

DELIVERY_STATUSES = (
    ("courier_assigned", "Courier Assigned", 0.08),
    ("picked_up", "Picked Up", 0.25),
    ("out_for_delivery", "Out for Delivery", 0.65),
    ("delivered", "Delivered", 1.0),
)
DELIVERY_BY_KEY = {
    key: {"key": key, "label": label, "progress": progress}
    for key, label, progress in DELIVERY_STATUSES
}
MAP_DELIVERY_STATUSES = frozenset({"picked_up", "out_for_delivery", "delivered"})
DEFAULT_BARANGAY_OFFICE = (14.6760, 121.0437)


def _json_dict(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return {}
    return value if isinstance(value, dict) else {}


def _raw_application_details(application):
    return copy.deepcopy(_json_dict(application.application_details))


def _admin_tracking_state(application):
    raw = _raw_application_details(application)
    tracking = _json_dict(raw.get("admin_tracking"))
    processing = _json_dict(tracking.get("processing"))
    delivery = _json_dict(tracking.get("delivery"))
    history = processing.get("history")
    processing["history"] = history if isinstance(history, list) else []
    delivery_history = delivery.get("history")
    delivery["history"] = delivery_history if isinstance(delivery_history, list) else []
    return {"raw": raw, "tracking": tracking, "processing": processing, "delivery": delivery}


def _save_admin_tracking(application, state):
    raw = dict(state["raw"])
    tracking = dict(state["tracking"])
    tracking["processing"] = state["processing"]
    tracking["delivery"] = state["delivery"]
    raw["admin_tracking"] = tracking
    application.application_details = raw


def _service_status_labels(application):
    labels = dict(LEGACY_STATUS_LABELS)
    spec = specification_for(application.service, field_map(application))
    if spec and spec.get("status_labels"):
        labels.update(spec["status_labels"])
    return labels


def _current_processing(application, state, service_labels):
    processing = state["processing"]
    key = processing.get("key")
    stored_legacy = processing.get("legacy_status")
    if key in ADMIN_PROCESSING_BY_KEY and (
        not stored_legacy or stored_legacy == application.application_status
    ):
        return key, ADMIN_PROCESSING_BY_KEY[key]["label"]
    fallback_key = ADMIN_PROCESSING_KEY_BY_LEGACY.get(application.application_status)
    if fallback_key:
        return fallback_key, ADMIN_PROCESSING_BY_KEY[fallback_key]["label"]
    return None, service_labels.get(
        application.application_status, application.application_status
    )


def _delivery_state(state):
    delivery = state["delivery"]
    key = delivery.get("status")
    if key not in DELIVERY_BY_KEY:
        key = None
    history = delivery.get("history") if isinstance(delivery.get("history"), list) else []
    return {
        "status": key,
        "label": DELIVERY_BY_KEY[key]["label"] if key else "Not dispatched",
        "progress": float(delivery.get("progress") or (DELIVERY_BY_KEY[key]["progress"] if key else 0)),
        "courier_name": delivery.get("courier_name") or "",
        "courier_contact": delivery.get("courier_contact") or "",
        "note": delivery.get("note") or "",
        "history": history,
        "dispatched_at": delivery.get("dispatched_at"),
        "dispatched_at_label": delivery.get("dispatched_at_label") or "",
        "delivered_at": delivery.get("delivered_at"),
        "delivered_at_label": delivery.get("delivered_at_label") or "",
        "updated_at": delivery.get("updated_at"),
        "updated_at_label": delivery.get("updated_at_label") or "",
        "map": _json_dict(delivery.get("map")),
    }


def _delivery_info(application):
    delivery = read_details(application).get("delivery")
    return delivery if isinstance(delivery, dict) else {}


def _coordinate(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _delivery_map_data(application, delivery, applicant):
    saved = _json_dict(delivery.get("map"))
    citizen_delivery = _delivery_info(application)
    origin_lat = _coordinate(citizen_delivery.get("origin_latitude"))
    origin_lng = _coordinate(citizen_delivery.get("origin_longitude"))
    destination_lat = _coordinate(citizen_delivery.get("latitude"))
    destination_lng = _coordinate(citizen_delivery.get("longitude"))
    destination_label = (
        clean_text(citizen_delivery.get("address"))
        or (applicant.address if applicant and applicant.address else "")
        or "Citizen delivery destination"
    )
    should_fetch_route = delivery.get("status") in MAP_DELIVERY_STATUSES

    def route_for(start_lat, start_lng, end_lat, end_lng, fallback):
        if should_fetch_route:
            routed = fetch_route(start_lat, start_lng, end_lat, end_lng)
            if routed and len(routed.get("coordinates") or []) > 1:
                return routed["coordinates"], routed.get("distance"), routed.get("duration")
        return fallback, None, None

    if origin_lat is not None and origin_lng is not None:
        origin_address = clean_text(citizen_delivery.get("origin_address"))
        origin_barangay = clean_text(citizen_delivery.get("origin_barangay"))
        start_label = origin_address or "Starting location"
        if origin_barangay and origin_barangay.lower() not in start_label.lower():
            start_label = f"{origin_barangay} · {start_label}"

        if destination_lat is None or destination_lng is None:
            destination_lat = origin_lat + 0.012
            destination_lng = origin_lng + 0.009
        if abs(destination_lat - origin_lat) < 0.0015 and abs(destination_lng - origin_lng) < 0.0015:
            destination_lat += 0.012
            destination_lng += 0.009
        fallback_route = [
            [origin_lat, origin_lng],
            [destination_lat, destination_lng],
        ]
        route, distance, duration = route_for(
            origin_lat, origin_lng, destination_lat, destination_lng, fallback_route
        )
        payload = {
            "start": {"lat": origin_lat, "lng": origin_lng, "label": start_label},
            "destination": {
                "lat": destination_lat,
                "lng": destination_lng,
                "label": destination_label,
            },
            "route": route,
        }
    elif saved.get("start") and saved.get("destination") and saved.get("route"):
        payload = dict(saved)
        saved_start = _json_dict(saved.get("start"))
        saved_destination = _json_dict(saved.get("destination"))
        route, distance, duration = route_for(
            _coordinate(saved_start.get("lat")) or 0,
            _coordinate(saved_start.get("lng")) or 0,
            _coordinate(saved_destination.get("lat")) or 0,
            _coordinate(saved_destination.get("lng")) or 0,
            saved["route"],
        )
        payload["route"] = route
    else:
        from app.services.barangay_delivery import barangay_center

        barangay = clean_text(citizen_delivery.get("barangay"))
        office = barangay_center(barangay) or DEFAULT_BARANGAY_OFFICE
        office_lat, office_lng = office
        if destination_lat is None or destination_lng is None:
            destination_lat = office_lat + 0.012
            destination_lng = office_lng + 0.009
        if abs(destination_lat - office_lat) < 0.0015 and abs(destination_lng - office_lng) < 0.0015:
            destination_lat += 0.012
            destination_lng += 0.009
        fallback_route = [
            [office_lat, office_lng],
            [
                (office_lat + destination_lat) / 2 + 0.0025,
                (office_lng + destination_lng) / 2 - 0.0025,
            ],
            [destination_lat, destination_lng],
        ]
        route, distance, duration = route_for(
            office_lat, office_lng, destination_lat, destination_lng, fallback_route
        )
        payload = {
            "start": {
                "lat": office_lat,
                "lng": office_lng,
                "label": f"Barangay Office · {barangay}" if barangay else "Barangay Office (simulated)",
            },
            "destination": {
                "lat": destination_lat,
                "lng": destination_lng,
                "label": destination_label,
            },
            "route": route,
        }

    payload["map_id"] = f"admin-delivery-map-{application.application_id}"
    payload["progress"] = delivery.get("progress") or 0
    payload["from_progress"] = delivery.get(
        "from_progress", saved.get("from_progress", 0)
    ) or 0
    payload["started_at"] = delivery.get("dispatched_at") or delivery.get("updated_at")
    payload["started_at_label"] = (
        delivery.get("dispatched_at_label")
        or delivery.get("updated_at_label")
        or "Not dispatched yet"
    )
    payload["ends_at"] = delivery.get("delivered_at")
    payload["ends_at_label"] = delivery.get("delivered_at_label") or "Pending"
    payload["route_distance"] = distance
    payload["route_duration"] = duration
    payload["status"] = delivery.get("status")
    payload["status_label"] = delivery.get("label") or delivery.get("status_label")
    return payload


def tracking_detail_data(application, applicant=None, include_map=True):
    """Build the tracking controls shared by the list and full review page."""
    from app.services.passport_admin import (
        current_status_key,
        status_label,
        summary as passport_summary,
    )
    from app.services.application_forms import specification_for
    from app.services.application_service import field_map
    from app.services.passport_delivery import PICKUP
    from app.services.senior_admin import summary as senior_confirmation_summary
    from app.services.senior_delivery import PICKUP as SENIOR_PICKUP
    from app.services.senior_delivery import fulfillment_method as senior_fulfillment_method

    passport = passport_summary(application)
    spec = specification_for(application.service, field_map(application))
    is_senior = bool(spec and spec.get("kind") == "senior")
    senior_method = senior_fulfillment_method(application) if is_senior else ""
    senior_fulfillment = {"method": senior_method} if is_senior else None
    senior_confirmation = senior_confirmation_summary(application)
    state = _admin_tracking_state(application)
    service_labels = _service_status_labels(application)
    processing_key, processing_label = _current_processing(
        application, state, service_labels
    )
    if passport and current_status_key(application):
        processing_label = status_label(application) or processing_label
    elif passport and passport["fulfillment_method"] == PICKUP and processing_key == "ready_for_dispatch":
        processing_label = "Ready for Pickup"
    elif is_senior and senior_method == SENIOR_PICKUP and processing_key == "ready_for_dispatch":
        processing_label = "Ready for Pickup"
    delivery = _delivery_state(state)
    is_pickup = bool(
        (passport and passport["fulfillment_method"] == PICKUP)
        or (is_senior and senior_method == SENIOR_PICKUP)
    )
    if is_pickup and application.application_status == "completed":
        delivery["label"] = "Received"
    map_payload = None
    if include_map and not (passport and passport["fulfillment_method"] == PICKUP) and not (
        is_senior and senior_method == SENIOR_PICKUP
    ):
        map_payload = _delivery_map_data(application, delivery, applicant)
    gated = bool(passport and passport["gate_message"]) or bool(
        senior_confirmation and senior_confirmation["gate_message"]
    )
    can_manage_delivery = application.application_status == "ready_for_release" or bool(
        delivery["status"]
    )
    if gated or (passport and passport["fulfillment_method"] == PICKUP) or (
        is_senior and senior_method == SENIOR_PICKUP
    ):
        can_manage_delivery = False
    return {
        "processing_key": processing_key,
        "processing_label": processing_label,
        "processing_selected": processing_key
        if processing_key in ADMIN_PROCESSING_BY_KEY
        else "",
        "delivery": delivery,
        "delivery_progress_percent": int(round(delivery["progress"] * 100)),
        "citizen_delivery": _delivery_info(application),
        "passport_fulfillment": passport,
        "senior_fulfillment": senior_fulfillment,
        "senior_confirmation": senior_confirmation,
        "can_update_status": application.application_status not in {"draft", "cancelled"}
        and not gated,
        "can_manage_delivery": can_manage_delivery,
        "show_map": map_payload is not None,
        "map": map_payload,
    }


def _log_admin_status_event(application, previous_status, description):
    now = datetime.now().replace(microsecond=0)
    db.session.add(
        ApplicationEvent(
            application_id=application.application_id,
            previous_status=previous_status,
            new_status=application.application_status,
            update_description=description[:500],
            updated_by=current_user.user_id,
            recorded_at=now,
        )
    )
    db.session.add(
        Notification(
            user_id=application.applicant_id,
            notification_title="Application status updated",
            notification_message=f"{application.tracking_number}: {description[:500]}",
            notification_type="application",
            read_status="unread",
            created_date=now,
        )
    )
    application.last_updated = now
    return now


def _admin_application_or_404(application_id):
    return application_or_404(application_id, include_documents=True, include_payments=True)


def _tracking_redirect(application_id):
    if clean_text(request.form.get("return_to")) == "detail":
        action = clean_text(request.form.get("action"))
        anchor = {
            "update_status": "processing-status",
            "assign_courier": "delivery-management",
        }.get(action, "delivery-management")
        if (
            action == "update_delivery"
            and clean_text(request.form.get("delivery_status")) in MAP_DELIVERY_STATUSES
        ):
            anchor = "dispatch-monitor"
        return redirect(
            f"{url_for('admin.application_detail', application_id=application_id)}#{anchor}"
        )
    return redirect(f"{url_for('admin_portal.tracking')}#application-{application_id}")


def _update_processing_status(application):
    target_key = clean_text(request.form.get("processing_status"))
    remarks = clean_text(request.form.get("remarks"))
    target = ADMIN_PROCESSING_BY_KEY.get(target_key)
    if target is None:
        abort(400, description="Choose a valid processing status.")
    if application.application_status in {"draft", "cancelled"}:
        flash("Only applications at the Confirmation stage or later can be updated.", "warning")
        return _tracking_redirect(application.application_id)
    confirmation_gate = _confirmation_gate(application)
    if confirmation_gate:
        flash(confirmation_gate, "warning")
        return _tracking_redirect(application.application_id)
    if len(remarks) > 500:
        flash("Remarks must be 500 characters or fewer.", "warning")
        return _tracking_redirect(application.application_id)

    target_label = target["label"]
    state = _admin_tracking_state(application)
    processing = state["processing"]
    now = datetime.now().replace(microsecond=0)
    processing.update(
        {
            "key": target["key"],
            "label": target_label,
            "legacy_status": target["legacy_status"],
            "note": remarks,
            "updated_by": current_user.user_id,
            "updated_by_name": current_user.full_name,
            "recorded_at": now.isoformat(),
            "recorded_at_label": now.strftime("%d %b %Y, %I:%M %p"),
        }
    )
    processing["history"].append(
        {
            "key": target["key"],
            "label": target_label,
            "legacy_status": target["legacy_status"],
            "note": remarks,
            "updated_by": current_user.user_id,
            "updated_by_name": current_user.full_name,
            "recorded_at": now.isoformat(),
            "recorded_at_label": now.strftime("%d %b %Y, %I:%M %p"),
        }
    )
    _save_admin_tracking(application, state)

    previous_status = application.application_status
    application.application_status = target["legacy_status"]
    description = f"Administrator set processing status to {target_label}."
    if remarks:
        description += f" Remarks: {remarks}"
    _log_admin_status_event(application, previous_status, description)
    db.session.commit()
    flash(f"{application.tracking_number} is now marked {target_label}.", "success")
    return _tracking_redirect(application.application_id)


def _assign_courier(application):
    confirmation_gate = _confirmation_gate(application)
    if confirmation_gate:
        flash(confirmation_gate, "warning")
        return _tracking_redirect(application.application_id)
    state = _admin_tracking_state(application)
    delivery = _delivery_state(state)
    if application.application_status != "ready_for_release" and not delivery["status"]:
        flash("Set the application to Ready for Dispatch before assigning a courier.", "warning")
        return _tracking_redirect(application.application_id)

    courier_name = clean_text(request.form.get("courier_name"))
    courier_contact = clean_text(request.form.get("courier_contact"))
    if not courier_name:
        flash("Enter the courier name.", "warning")
        return _tracking_redirect(application.application_id)
    if len(courier_name) > 120:
        flash("Courier name must be 120 characters or fewer.", "warning")
        return _tracking_redirect(application.application_id)
    if courier_contact:
        courier_contact = normalize_contact_number(courier_contact)
        digits = courier_contact[1:] if courier_contact.startswith("+") else courier_contact
        if not digits.isdigit() or not 10 <= len(digits) <= 15:
            flash("Enter a valid courier contact number.", "warning")
            return _tracking_redirect(application.application_id)

    now = datetime.now().replace(microsecond=0)
    stored_delivery = state["delivery"]
    previous_status = delivery["status"]
    recreate_status = not previous_status or previous_status == "courier_assigned"
    new_status = "courier_assigned" if recreate_status else previous_status
    note = f"Courier {'assigned' if recreate_status else 'reassigned'}: {courier_name}."
    stored_delivery.update(
        {
            "courier_name": courier_name,
            "courier_contact": courier_contact,
            "courier_assigned_at": now.isoformat(),
            "courier_assigned_at_label": now.strftime("%d %b %Y, %I:%M %p"),
            "status": new_status,
            "progress": DELIVERY_BY_KEY[new_status]["progress"],
        }
    )
    stored_delivery["history"].append(
        {
            "status": new_status,
            "status_label": DELIVERY_BY_KEY[new_status]["label"],
            "description": note,
            "progress": DELIVERY_BY_KEY[new_status]["progress"],
            "updated_by": current_user.user_id,
            "updated_by_name": current_user.full_name,
            "recorded_at": now.isoformat(),
            "recorded_at_label": now.strftime("%d %b %Y, %I:%M %p"),
        }
    )
    _save_admin_tracking(application, state)
    db.session.commit()
    flash(f"Courier {courier_name} was saved for {application.tracking_number}.", "success")
    return _tracking_redirect(application.application_id)


def _update_delivery_status(application):
    confirmation_gate = _confirmation_gate(application)
    if confirmation_gate:
        flash(confirmation_gate, "warning")
        return _tracking_redirect(application.application_id)
    target_key = clean_text(request.form.get("delivery_status"))
    note = clean_text(request.form.get("delivery_note"))
    target = DELIVERY_BY_KEY.get(target_key)
    if target is None:
        abort(400, description="Choose a valid delivery status.")
    if len(note) > 500:
        flash("Delivery notes must be 500 characters or fewer.", "warning")
        return _tracking_redirect(application.application_id)

    state = _admin_tracking_state(application)
    delivery = _delivery_state(state)
    if application.application_status != "ready_for_release" and not delivery["status"]:
        flash("Set the application to Ready for Dispatch before updating delivery.", "warning")
        return _tracking_redirect(application.application_id)
    if not delivery["courier_name"]:
        flash("Assign a courier before updating the delivery status.", "warning")
        return _tracking_redirect(application.application_id)

    now = datetime.now().replace(microsecond=0)
    stored_delivery = state["delivery"]
    previous_label = delivery["label"]
    previous_progress = float(delivery["progress"] or 0)
    stored_delivery.update(
        {
            "status": target["key"],
            "progress": target["progress"],
            "note": note,
            "updated_by": current_user.user_id,
            "updated_by_name": current_user.full_name,
            "updated_at": now.isoformat(),
            "updated_at_label": now.strftime("%d %b %Y, %I:%M %p"),
        }
    )
    if target["key"] in MAP_DELIVERY_STATUSES and not stored_delivery.get("dispatched_at"):
        stored_delivery["dispatched_at"] = now.isoformat()
        stored_delivery["dispatched_at_label"] = now.strftime("%d %b %Y, %I:%M %p")
    if target["key"] == "delivered":
        stored_delivery["delivered_at"] = now.isoformat()
        stored_delivery["delivered_at_label"] = now.strftime("%d %b %Y, %I:%M %p")

    description = f"Delivery status changed from {previous_label} to {target['label']}."
    if note:
        description += f" Notes: {note}"
    stored_delivery["history"].append(
        {
            "status": target["key"],
            "status_label": target["label"],
            "description": description,
            "progress": target["progress"],
            "updated_by": current_user.user_id,
            "updated_by_name": current_user.full_name,
            "recorded_at": now.isoformat(),
            "recorded_at_label": now.strftime("%d %b %Y, %I:%M %p"),
        }
    )
    if target["key"] in MAP_DELIVERY_STATUSES:
        map_context = dict(stored_delivery)
        map_context.update(
            {
                "status": target["key"],
                "label": target["label"],
                "progress": target["progress"],
                "from_progress": previous_progress,
                "map": stored_delivery.get("map"),
            }
        )
        stored_delivery["map"] = _delivery_map_data(
            application,
            map_context,
            db.session.get(User, application.applicant_id),
        )
    _save_admin_tracking(application, state)
    db.session.commit()
    flash(f"Delivery status for {application.tracking_number} is now {target['label']}.", "success")
    return _tracking_redirect(application.application_id)


def _admin_only(view):
    return admin_console_required(view)


def _add_rule(path, view, endpoint, methods=("GET",)):
    admin_portal_bp.add_url_rule(
        path,
        endpoint=endpoint,
        view_func=_admin_only(view),
        methods=list(methods),
    )


@admin_portal_bp.context_processor
def admin_portal_navigation():
    return citizen.portal_navigation_context()


@admin_portal_bp.route("/admin/portal/dashboard")
@admin_console_required
def dashboard():
    return redirect(url_for("admin.dashboard"))


@admin_portal_bp.route("/admin/portal/tracking", methods=["GET", "POST"])
@admin_console_required
def tracking():
    if request.method == "POST":
        application_id = clean_text(request.form.get("application_id"))
        if not application_id.isdigit():
            abort(400, description="Choose a valid application.")
        application = _admin_application_or_404(int(application_id))
        action = clean_text(request.form.get("action"))
        if action == "update_status":
            return _update_processing_status(application)
        if action == "assign_courier":
            return _assign_courier(application)
        if action == "update_delivery":
            return _update_delivery_status(application)
        abort(400, description="Choose a valid tracking action.")

    search = clean_text(request.args.get("q"))
    query = visible_application_query(
        db.select(Application)
        .options(joinedload(Application.service))
        .where(Application.application_status != "draft")
    )
    if search:
        pattern = f"%{search}%"
        query = query.join(User, User.user_id == Application.applicant_id).where(
            or_(
                Application.tracking_number.ilike(pattern),
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
            )
        )
    applications = db.session.scalars(
        query.order_by(Application.last_updated.desc(), Application.application_id.desc()).limit(200)
    ).unique().all()
    applicant_ids = {application.applicant_id for application in applications}
    applicants = (
        {
            user.user_id: user
            for user in db.session.scalars(
                db.select(User).where(User.user_id.in_(applicant_ids))
            ).all()
        }
        if applicant_ids
        else {}
    )
    tracking_rows = []
    for application in applications:
        applicant = applicants.get(application.applicant_id)
        fields = field_map(application)
        tracking_rows.append(
            {
                "application": application,
                "applicant": applicant,
                "application_type": fields.get("application_type") or "—",
                **tracking_detail_data(application, applicant, include_map=False),
            }
        )

    return render_template(
        "admin/application_tracking.html",
        tracking_rows=tracking_rows,
        search=search,
    )


_add_rule("/admin/portal/services", citizen.services, "services")
_add_rule("/admin/portal/applications", citizen.applications, "applications")
_add_rule(
    "/admin/portal/applications/<int:application_id>",
    citizen.application_detail,
    "application_detail",
)
_add_rule("/admin/portal/notifications", citizen.notifications, "notifications")
_add_rule(
    "/admin/portal/profile",
    citizen.profile,
    "profile",
    ("GET", "POST"),
)
_add_rule(
    "/admin/portal/settings",
    citizen.settings,
    "settings",
    ("GET", "POST"),
)


@admin_portal_bp.route("/admin/portal/payments")
@admin_console_required
def payments():
    records = db.session.scalars(
        visible_payment_query(
            db.select(Payment)
            .options(joinedload(Payment.application).joinedload(Application.service))
            .order_by(Payment.payment_id.desc())
        )
    ).unique().all()
    applicant_ids = {
        record.application.applicant_id for record in records if record.application is not None
    }
    applicants = (
        {
            user.user_id: user
            for user in db.session.scalars(
                db.select(User).where(User.user_id.in_(applicant_ids))
            ).all()
        }
        if applicant_ids
        else {}
    )
    return render_template(
        "payments/payment_history.html",
        payments=records,
        applicants=applicants,
        admin_payments=True,
        payment_method_labels=citizen.PAYMENT_METHOD_LABELS,
        payment_status_labels=citizen.PAYMENT_STATUS_LABELS,
    )


register_application_routes(
    admin_portal_bp,
    base="/admin/portal",
    wrap=_admin_only,
)
