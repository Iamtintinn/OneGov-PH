"""Senior Citizen ID application types and physical documents to bring to OSCA."""

SENIOR_TYPE_REGULAR = "Regular Application"
SENIOR_TYPE_NO_PSA = "Without PSA Birth Certificate"
SENIOR_TYPE_DUAL_CITIZEN = "Dual Citizenship"

SENIOR_APPLICATION_TYPES = (
    SENIOR_TYPE_REGULAR,
    SENIOR_TYPE_NO_PSA,
    SENIOR_TYPE_DUAL_CITIZEN,
)

SENIOR_TYPE_OPTIONS = (
    {
        "key": SENIOR_TYPE_REGULAR,
        "title": SENIOR_TYPE_REGULAR,
        "help": "For Filipino citizens aged 60 and above with a PSA Birth Certificate and standard OSCA requirements.",
    },
    {
        "key": SENIOR_TYPE_NO_PSA,
        "title": SENIOR_TYPE_NO_PSA,
        "help": "For applicants who cannot present a PSA Birth Certificate and need alternate proof of age and citizenship.",
    },
    {
        "key": SENIOR_TYPE_DUAL_CITIZEN,
        "title": SENIOR_TYPE_DUAL_CITIZEN,
        "help": "For dual citizens who must show Filipino citizenship and Philippine residency documents.",
    },
)

_BASE_ITEMS = (
    "Original PSA Birth Certificate or acceptable supporting document",
    "Original valid government-issued ID",
    "Original Barangay Certificate of Residency, if required",
    "Printed ID photographs in the required size (1x1 or 2x2)",
    "Accomplished OSCA application form",
)

_BRING_REQUIREMENTS = {
    SENIOR_TYPE_REGULAR: {
        "note": (
            "You may also be required to personally appear for identity verification, photograph capture, or an interview. "
            "Original documents should be returned after verification unless the issuing office requires otherwise."
        ),
        "items": _BASE_ITEMS,
    },
    SENIOR_TYPE_NO_PSA: {
        "note": (
            "Bring alternate age and citizenship proof accepted by OSCA when a PSA Birth Certificate is unavailable. "
            "You may also be required to personally appear for verification."
        ),
        "items": (
            "Baptismal Certificate – If used in place of a PSA Birth Certificate",
            "Other acceptable supporting documents establishing date of birth and Filipino citizenship",
            "Additional identity verification documents requested by OSCA",
        )
        + _BASE_ITEMS[1:],
    },
    SENIOR_TYPE_DUAL_CITIZEN: {
        "note": (
            "Bring proof of Filipino citizenship and Philippine residency as required by OSCA. "
            "You may also be required to personally appear for verification."
        ),
        "items": (
            "Proof of Filipino Citizenship",
            "Supporting Documents Establishing Philippine Residency",
            "Additional Documents Required by OSCA",
        )
        + _BASE_ITEMS,
    },
}


def normalize_senior_type(application_type):
    selected = " ".join(str(application_type or "").split())
    if selected in SENIOR_APPLICATION_TYPES:
        return selected
    return selected


def bring_requirements_for(application_type):
    """Return the physical documents checklist for the selected Senior Citizen ID path."""
    normalized = normalize_senior_type(application_type)
    payload = _BRING_REQUIREMENTS.get(normalized)
    if payload is None:
        return {
            "application_type": normalized or "",
            "note": (
                "Requirements may vary by local OSCA office. "
                "Confirm the current documentary requirements before your visit."
            ),
            "items": _BASE_ITEMS,
        }
    return {
        "application_type": normalized,
        "note": payload["note"],
        "items": payload["items"],
    }
