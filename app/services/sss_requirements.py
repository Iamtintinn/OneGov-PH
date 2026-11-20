"""Requirement helpers for SSS MySSS Card assistance flows."""

from app.services.application_forms import SSS_MYSSS_TYPE_NEW, normalize_sss_mysss_type

SSS_NEW_MYSSS_REQUIREMENTS = (
    "Permanent SSS Number.",
    "Active My.SSS online account.",
    "Philippine National ID (PhilSys) registration.",
    "Updated email address.",
    "Updated mobile number.",
    "Updated residential/mailing address.",
    "National ID for identity verification and facial scan.",
    "Partner bank account opening and identity verification (additional requirement).",
)

SSS_NEW_MYSSS_NOTE = (
    "Physical appearance: Not required at an SSS branch. "
    "Bank verification may require an online process or branch visit, depending on the bank."
)


def bring_requirements_for(application_type):
    """Return preparation/verification requirements for MySSS Card confirmation/receipt."""
    selected = normalize_sss_mysss_type(application_type)
    if selected == SSS_MYSSS_TYPE_NEW:
        return {
            "application_type": selected,
            "items": SSS_NEW_MYSSS_REQUIREMENTS,
            "note": SSS_NEW_MYSSS_NOTE,
        }
    return {"application_type": selected, "items": (), "note": None}
