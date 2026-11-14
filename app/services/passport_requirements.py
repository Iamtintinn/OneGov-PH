"""Passport application types and physical documents to bring on appointment day."""

PASSPORT_TYPE_NEW = "New Application (First-time)"
PASSPORT_TYPE_RENEWAL_EXPIRED = "Renewal – Expired Passport"
PASSPORT_TYPE_RENEWAL_EXPIRING = "Renewal – Expiring Passport"
PASSPORT_TYPE_LOST_VALID = "Lost Passport – Valid"
PASSPORT_TYPE_LOST_EXPIRED = "Lost Passport – Expired"
PASSPORT_TYPE_DAMAGED = "Damaged / Mutilated Passport"
PASSPORT_TYPE_CHANGE_NAME = "Change of Name"
PASSPORT_TYPE_CORRECTION = "Correction of Personal Information"

PASSPORT_APPLICATION_TYPES = (
    PASSPORT_TYPE_NEW,
    PASSPORT_TYPE_RENEWAL_EXPIRED,
    PASSPORT_TYPE_RENEWAL_EXPIRING,
    PASSPORT_TYPE_LOST_VALID,
    PASSPORT_TYPE_LOST_EXPIRED,
    PASSPORT_TYPE_DAMAGED,
    PASSPORT_TYPE_CHANGE_NAME,
    PASSPORT_TYPE_CORRECTION,
)

_LEGACY_TYPES = {
    "New": PASSPORT_TYPE_NEW,
    "Renewal": PASSPORT_TYPE_RENEWAL_EXPIRED,
}

PASSPORT_TYPE_OPTIONS = (
    {
        "key": PASSPORT_TYPE_NEW,
        "title": PASSPORT_TYPE_NEW,
        "help": "For applicants who have never been issued a Philippine passport.",
    },
    {
        "key": PASSPORT_TYPE_RENEWAL_EXPIRED,
        "title": PASSPORT_TYPE_RENEWAL_EXPIRED,
        "help": "For applicants whose previous Philippine passport has expired.",
    },
    {
        "key": PASSPORT_TYPE_RENEWAL_EXPIRING,
        "title": PASSPORT_TYPE_RENEWAL_EXPIRING,
        "help": "For applicants whose passport is still valid but approaching expiration.",
    },
    {
        "key": PASSPORT_TYPE_LOST_VALID,
        "title": PASSPORT_TYPE_LOST_VALID,
        "help": "For applicants who lost their passport while it was still valid. Subject to a 15-day clearing period.",
    },
    {
        "key": PASSPORT_TYPE_LOST_EXPIRED,
        "title": PASSPORT_TYPE_LOST_EXPIRED,
        "help": "For applicants who lost their passport after it had expired.",
    },
    {
        "key": PASSPORT_TYPE_DAMAGED,
        "title": PASSPORT_TYPE_DAMAGED,
        "help": "For applicants whose previous passport is physically damaged.",
    },
    {
        "key": PASSPORT_TYPE_CHANGE_NAME,
        "title": PASSPORT_TYPE_CHANGE_NAME,
        "help": "For applicants requesting a passport name change due to marriage or another legally recognized reason.",
    },
    {
        "key": PASSPORT_TYPE_CORRECTION,
        "title": PASSPORT_TYPE_CORRECTION,
        "help": "For applicants requesting corrections to their passport information.",
    },
)

_BRING_REQUIREMENTS = {
    PASSPORT_TYPE_NEW: {
        "note": None,
        "items": (
            "PSA Birth Certificate – Original and one photocopy",
            "Valid Government-issued ID – Original and one photocopy",
            "Passport Application Form",
            "Proof of Payment / E-Receipt",
            "Additional Supporting Documents (if applicable)",
        ),
    },
    PASSPORT_TYPE_RENEWAL_EXPIRED: {
        "note": None,
        "items": (
            "Latest Philippine Passport – Original",
            "Photocopy of Passport Data Page",
            "Passport Application Form",
            "Proof of Payment / E-Receipt",
            "Supporting Documents for Name Changes (if applicable)",
        ),
    },
    PASSPORT_TYPE_RENEWAL_EXPIRING: {
        "note": None,
        "items": (
            "Latest Philippine Passport – Original",
            "Photocopy of Passport Data Page",
            "Passport Application Form",
            "Proof of Payment / E-Receipt",
            "Supporting Documents for Name Changes (if applicable)",
        ),
    },
    PASSPORT_TYPE_LOST_VALID: {
        "note": "Subject to a 15-day clearing period.",
        "items": (
            "Notarized Affidavit of Loss – Original",
            "Police Report – Original",
            "Copy of Lost Passport (if available)",
            "PSA Birth Certificate (if required)",
            "Valid Government-issued ID (if required)",
            "Passport Application Form",
            "Proof of Payment / E-Receipt",
        ),
    },
    PASSPORT_TYPE_LOST_EXPIRED: {
        "note": None,
        "items": (
            "Notarized Affidavit of Loss – Original",
            "Police Report – Original",
            "Copy of Lost Passport (if available)",
            "PSA Birth Certificate (if required)",
            "Valid Government-issued ID (if required)",
            "Passport Application Form",
            "Proof of Payment / E-Receipt",
        ),
    },
    PASSPORT_TYPE_DAMAGED: {
        "note": None,
        "items": (
            "Damaged / Mutilated Passport – Original",
            "Notarized Affidavit of Explanation – Original",
            "PSA Birth Certificate – Original",
            "Valid Government-issued ID – Original",
            "Passport Application Form",
            "Proof of Payment / E-Receipt",
        ),
    },
    PASSPORT_TYPE_CHANGE_NAME: {
        "note": None,
        "items": (
            "Latest Philippine Passport – Original",
            "Photocopy of Passport Data Page",
            "PSA Marriage Certificate (for applicable marriage-related changes)",
            "Other Applicable PSA or Legal Documents",
            "Passport Application Form",
            "Proof of Payment / E-Receipt",
        ),
    },
    PASSPORT_TYPE_CORRECTION: {
        "note": None,
        "items": (
            "Latest Philippine Passport – Original (if available)",
            "PSA Birth Certificate – Original",
            "Valid Government-issued ID – Original",
            "Supporting PSA Documents (depending on the correction)",
            "Notarized Affidavit of Explanation (if required)",
            "Passport Application Form",
            "Proof of Payment / E-Receipt",
        ),
    },
}


def normalize_passport_type(value):
    cleaned = str(value or "").strip()
    if cleaned in _BRING_REQUIREMENTS:
        return cleaned
    return _LEGACY_TYPES.get(cleaned, cleaned)


def is_passport_renewal_type(application_type):
    normalized = normalize_passport_type(application_type)
    return normalized in {
        PASSPORT_TYPE_RENEWAL_EXPIRED,
        PASSPORT_TYPE_RENEWAL_EXPIRING,
        PASSPORT_TYPE_CHANGE_NAME,
        PASSPORT_TYPE_CORRECTION,
        PASSPORT_TYPE_DAMAGED,
        PASSPORT_TYPE_LOST_VALID,
        PASSPORT_TYPE_LOST_EXPIRED,
    }


def bring_requirements_for(application_type):
    """Return the physical documents checklist for the selected passport application type."""
    normalized = normalize_passport_type(application_type)
    payload = _BRING_REQUIREMENTS.get(normalized)
    if payload is None:
        return {
            "application_type": normalized or "",
            "note": "Confirm the current documentary requirements with DFA before your appointment.",
            "items": (
                "Passport Application Form",
                "Proof of Payment / E-Receipt",
                "Valid Government-issued ID – Original",
            ),
        }
    return {
        "application_type": normalized,
        "note": payload["note"],
        "items": payload["items"],
    }
