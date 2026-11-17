"""Helpers that keep administrators inside the unified admin interface."""

from flask import current_app, has_request_context, request
from flask import url_for as flask_url_for

ADMIN_PATH_PREFIX = "/admin"
ADMIN_PORTAL_BLUEPRINT = "admin_portal"


def in_admin_portal():
    return has_request_context() and request.path.startswith(ADMIN_PATH_PREFIX)


def portal_endpoint(endpoint):
    """Return the admin-portal equivalent of a citizen endpoint when available."""
    if not endpoint or not endpoint.startswith("citizen."):
        return endpoint
    candidate = f"{ADMIN_PORTAL_BLUEPRINT}.{endpoint.split('.', 1)[1]}"
    if candidate in current_app.view_functions:
        return candidate
    return endpoint


def portal_url_for(endpoint, **values):
    """Use the admin portal equivalent of citizen links while inside /admin."""
    if in_admin_portal():
        endpoint = portal_endpoint(endpoint)
    return flask_url_for(endpoint, **values)
