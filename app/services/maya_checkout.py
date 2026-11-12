"""Maya Checkout Sandbox client. Sandbox API only — never call production."""

from __future__ import annotations

import logging
from typing import Any

import requests
from flask import current_app

logger = logging.getLogger(__name__)

SANDBOX_HOST = "https://pg-sandbox.paymaya.com"
PRODUCTION_HOST = "https://pg.paymaya.com"

# Official webhook event names for Maya Checkout (supersede CHECKOUT_*).
WEBHOOK_EVENTS = (
    "PAYMENT_SUCCESS",
    "PAYMENT_FAILED",
    "PAYMENT_EXPIRED",
    "PAYMENT_CANCELLED",
)

SUCCESS_STATUSES = frozenset({"PAYMENT_SUCCESS"})
FAILED_STATUSES = frozenset({"PAYMENT_FAILED", "AUTH_FAILED"})
CANCELLED_STATUSES = frozenset({"PAYMENT_CANCELLED"})
EXPIRED_STATUSES = frozenset({"PAYMENT_EXPIRED"})
PENDING_STATUSES = frozenset(
    {
        "PENDING_TOKEN",
        "PENDING_PAYMENT",
        "FOR_AUTHENTICATION",
        "AUTHENTICATING",
        "AUTH_SUCCESS",
        "PAYMENT_PROCESSING",
    }
)


class MayaCheckoutError(RuntimeError):
    """Raised when Maya Checkout sandbox rejects or cannot complete a call."""


def _require_sandbox_config() -> tuple[str, str, str]:
    environment = (current_app.config.get("MAYA_ENVIRONMENT") or "").strip().lower()
    api_url = (current_app.config.get("MAYA_API_URL") or "").strip().rstrip("/")
    public_key = (current_app.config.get("MAYA_PUBLIC_KEY") or "").strip()
    secret_key = (current_app.config.get("MAYA_SECRET_KEY") or "").strip()

    if environment != "sandbox":
        raise MayaCheckoutError(
            "Maya Checkout is locked to sandbox mode for this project. "
            "Set MAYA_ENVIRONMENT=sandbox."
        )
    if not api_url or api_url == PRODUCTION_HOST or "pg-sandbox.paymaya.com" not in api_url:
        raise MayaCheckoutError(
            "Maya Checkout must use the sandbox host https://pg-sandbox.paymaya.com."
        )
    if not public_key.startswith("pk-") or not secret_key.startswith("sk-"):
        raise MayaCheckoutError(
            "Maya sandbox public (pk-...) and secret (sk-...) keys are required in .env."
        )
    return api_url, public_key, secret_key


def _auth(key: str) -> tuple[str, str]:
    # Maya Basic Auth: API key as username, blank password.
    return key, ""


def _request(
    method: str,
    path: str,
    *,
    key: str,
    json_body: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any] | list[Any]:
    api_url, public_key, secret_key = _require_sandbox_config()
    if key == "public":
        auth = _auth(public_key)
    elif key == "secret":
        auth = _auth(secret_key)
    else:
        raise MayaCheckoutError("Invalid Maya key type.")

    url = f"{api_url}{path}"
    try:
        response = requests.request(
            method,
            url,
            auth=auth,
            json=json_body,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        logger.exception("Maya Checkout request failed: %s %s", method, path)
        raise MayaCheckoutError("Could not reach Maya Checkout sandbox.") from exc

    if response.status_code >= 400:
        detail = response.text[:500]
        logger.error("Maya Checkout error %s %s → %s %s", method, path, response.status_code, detail)
        raise MayaCheckoutError(
            f"Maya Checkout returned HTTP {response.status_code}. Check sandbox credentials and payload."
        )

    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError as exc:
        raise MayaCheckoutError("Maya Checkout returned a non-JSON response.") from exc


def create_checkout(
    *,
    amount: float,
    request_reference_number: str,
    redirect_urls: dict[str, str],
    buyer: dict[str, Any] | None = None,
    item_name: str = "Passport application fee",
) -> dict[str, Any]:
    """
    POST /checkout/v1/checkouts (PUBLIC key).
    Returns checkoutId and redirectUrl per Maya Create Checkout docs.
    """
    value = f"{float(amount):.2f}"
    payload: dict[str, Any] = {
        "totalAmount": {"value": value, "currency": "PHP"},
        "requestReferenceNumber": request_reference_number[:36],
        "redirectUrl": {
            "success": redirect_urls["success"],
            "failure": redirect_urls["failure"],
            "cancel": redirect_urls["cancel"],
        },
        "items": [
            {
                "name": item_name[:100],
                "quantity": "1",
                "amount": {"value": value},
                "totalAmount": {"value": value},
            }
        ],
    }
    if buyer:
        payload["buyer"] = buyer
    data = _request("POST", "/checkout/v1/checkouts", key="public", json_body=payload)
    if not isinstance(data, dict) or not data.get("checkoutId") or not data.get("redirectUrl"):
        raise MayaCheckoutError("Maya Create Checkout response was missing checkoutId or redirectUrl.")
    return data


def retrieve_payment_by_id(payment_id: str) -> dict[str, Any]:
    """GET /payments/v1/payments/{paymentId} (SECRET key)."""
    data = _request("GET", f"/payments/v1/payments/{payment_id}", key="secret")
    if not isinstance(data, dict):
        raise MayaCheckoutError("Unexpected Maya payment response.")
    return data


def retrieve_payment_by_rrn(request_reference_number: str) -> dict[str, Any]:
    """GET /payments/v1/payment-rrns/{rrn} (SECRET key). May return a list."""
    data = _request(
        "GET",
        f"/payments/v1/payment-rrns/{request_reference_number}",
        key="secret",
    )
    if isinstance(data, list):
        if not data:
            raise MayaCheckoutError("No Maya payment found for that reference.")
        first = data[0]
        if not isinstance(first, dict):
            raise MayaCheckoutError("Unexpected Maya payment-rrn response.")
        return first
    if not isinstance(data, dict):
        raise MayaCheckoutError("Unexpected Maya payment-rrn response.")
    return data


def payment_status_from_payload(payload: dict[str, Any]) -> str:
    status = (
        payload.get("paymentStatus")
        or payload.get("status")
        or ""
    )
    normalized = str(status).strip().upper()
    # Some Retrieve Payment responses expose isPaid before status settles.
    if not normalized and payload.get("isPaid") is True:
        return "PAYMENT_SUCCESS"
    if normalized in {"SUCCESS", "SUCCESSFUL", "PAID"}:
        return "PAYMENT_SUCCESS"
    return normalized


def map_maya_status(maya_status: str) -> str | None:
    """Map Maya paymentStatus to local payment_status enum, or None if still in progress."""
    status = (maya_status or "").strip().upper()
    if status in SUCCESS_STATUSES:
        return "paid"
    if status in FAILED_STATUSES:
        return "failed"
    if status in CANCELLED_STATUSES:
        return "cancelled"
    if status in EXPIRED_STATUSES:
        return "cancelled"
    if status in PENDING_STATUSES or not status:
        return None
    # Unknown terminal-ish statuses: keep pending and log.
    logger.warning("Unrecognized Maya paymentStatus: %s", status)
    return None


def create_webhook(name: str, callback_url: str) -> dict[str, Any]:
    """POST /payments/v1/webhooks (SECRET key)."""
    data = _request(
        "POST",
        "/payments/v1/webhooks",
        key="secret",
        json_body={"name": name, "callbackUrl": callback_url},
    )
    if not isinstance(data, dict):
        raise MayaCheckoutError("Unexpected Maya webhook response.")
    return data


def list_webhooks() -> list[dict[str, Any]]:
    """GET /payments/v1/webhooks (SECRET key)."""
    data = _request("GET", "/payments/v1/webhooks", key="secret")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def ensure_webhooks(callback_url: str) -> list[dict[str, Any]]:
    """Register PAYMENT_* webhooks for the given HTTPS callback URL when missing."""
    existing = list_webhooks()
    by_name = {str(item.get("name")): item for item in existing}
    results = []
    for name in WEBHOOK_EVENTS:
        current = by_name.get(name)
        if current and str(current.get("callbackUrl") or "").rstrip("/") == callback_url.rstrip("/"):
            results.append(current)
            continue
        results.append(create_webhook(name, callback_url))
    return results
