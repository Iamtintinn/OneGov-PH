"""CENOMAR request types and required document uploads."""

CENOMAR_TYPE_PERSONAL = "Personal Use"
CENOMAR_TYPE_MARRIAGE = "Marriage Requirement"
CENOMAR_TYPE_PASSPORT = "Passport / Travel"
CENOMAR_TYPE_LOCAL_EMPLOYMENT = "Local Employment"
CENOMAR_TYPE_OVERSEAS_EMPLOYMENT = "Overseas Employment"
CENOMAR_TYPE_SCHOOL = "School Requirements"
CENOMAR_TYPE_LEGAL = "Legal / Government Transactions"
CENOMAR_TYPE_OTHER = "Other Purposes"

CENOMAR_APPLICATION_TYPES = (
    CENOMAR_TYPE_PERSONAL,
    CENOMAR_TYPE_MARRIAGE,
    CENOMAR_TYPE_PASSPORT,
    CENOMAR_TYPE_LOCAL_EMPLOYMENT,
    CENOMAR_TYPE_OVERSEAS_EMPLOYMENT,
    CENOMAR_TYPE_SCHOOL,
    CENOMAR_TYPE_LEGAL,
    CENOMAR_TYPE_OTHER,
)

CENOMAR_TYPE_OPTIONS = tuple(
    {
        "key": application_type,
        "title": application_type,
        "help": "A valid government-issued ID is required for this request.",
    }
    for application_type in CENOMAR_APPLICATION_TYPES
)


def normalize_cenomar_type(application_type):
    selected = " ".join(str(application_type or "").split())
    return selected if selected in CENOMAR_APPLICATION_TYPES else selected


def document_requirements_for(application_type):
    """Return the required ID upload for the selected CENOMAR request type."""
    normalized = normalize_cenomar_type(application_type)
    return {
        "application_type": normalized or "",
        "note": (
            f"Upload a valid government-issued ID for {normalized or 'your selected request type'}. "
            "Choose the ID type from the searchable list, then upload a clear copy of that ID."
        ),
        "documents": (
            {
                "key": "valid_id",
                "label": "Valid Government-issued ID",
                "help": "Choose one valid government-issued ID, then upload a clear PDF or photo of that same ID.",
                "required": True,
                "id_choices": "barangay",
            },
        ),
    }
