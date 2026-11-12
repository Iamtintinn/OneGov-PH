"""Public webhook endpoints (no login, CSRF-exempt)."""

from flask import Blueprint, current_app, jsonify, request

from app.services.passport_payment import process_maya_webhook

webhooks_bp = Blueprint("webhooks", __name__)


@webhooks_bp.post("/webhooks/maya")
def maya_webhook():
    """
    Maya Checkout sandbox webhook receiver.
    Always acknowledge quickly with 200 when payload is readable; verification is server-side.
    """
    payload = request.get_json(silent=True)
    if payload is None:
        current_app.logger.warning("Maya webhook received non-JSON body")
        return jsonify({"ok": False, "error": "expected JSON"}), 400

    ok, detail = process_maya_webhook(payload)
    if not ok:
        current_app.logger.warning("Maya webhook processing issue: %s", detail)
        # Still 200 for unknown refs so Maya does not endlessly retry bad sandboxes on shared keys.
        return jsonify({"ok": False, "detail": detail}), 200

    return jsonify({"ok": True, "status": detail}), 200
