"""Birth Certificate request types and required document uploads by type."""

BIRTH_TYPE_PERSONAL = "Personal Request (Own Birth Certificate)"
BIRTH_TYPE_MINOR = "Request for Minor Child"
BIRTH_TYPE_REPRESENTATIVE = "Authorized Representative"
BIRTH_TYPE_DECEASED = "Request for Deceased Person"

BIRTH_APPLICATION_TYPES = (
    BIRTH_TYPE_PERSONAL,
    BIRTH_TYPE_MINOR,
    BIRTH_TYPE_REPRESENTATIVE,
    BIRTH_TYPE_DECEASED,
)

BIRTH_TYPE_OPTIONS = (
    {
        "key": BIRTH_TYPE_PERSONAL,
        "title": BIRTH_TYPE_PERSONAL,
        "help": "For applicants requesting their own PSA Birth Certificate.",
    },
    {
        "key": BIRTH_TYPE_MINOR,
        "title": BIRTH_TYPE_MINOR,
        "help": "For a parent or guardian requesting a birth certificate for a minor child.",
    },
    {
        "key": BIRTH_TYPE_REPRESENTATIVE,
        "title": BIRTH_TYPE_REPRESENTATIVE,
        "help": "For an authorized representative requesting a birth certificate on behalf of the document owner.",
    },
    {
        "key": BIRTH_TYPE_DECEASED,
        "title": BIRTH_TYPE_DECEASED,
        "help": "For a requester asking for the birth certificate of a deceased person.",
    },
)

_DOCUMENTS_BY_TYPE = {
    BIRTH_TYPE_PERSONAL: (
        {
            "key": "valid_id",
            "label": "Valid Government-issued ID",
            "help": "Choose one valid government ID from the searchable list, then upload a clear PDF or photo of that same ID for identity verification.",
            "required": True,
            "id_choices": "barangay",
        },
    ),
    BIRTH_TYPE_MINOR: (
        {
            "key": "parent_valid_id",
            "label": "Parent’s Valid Government-issued ID",
            "help": "Choose one valid government ID belonging to the parent, then upload a clear PDF or photo of that same ID.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "child_birth_details",
            "label": "Child’s Birth Details",
            "help": "Upload a document or clear record that shows the child’s birth details needed for this request.",
            "required": True,
        },
        {
            "key": "proof_of_parental_relationship",
            "label": "Proof of Parental Relationship",
            "help": "Upload proof of parental relationship when requested for this birth certificate request.",
            "required": True,
        },
    ),
    BIRTH_TYPE_REPRESENTATIVE: (
        {
            "key": "authorization",
            "label": "Authorization Letter",
            "help": "Upload the authorization letter signed by the document owner.",
            "required": True,
        },
        {
            "key": "owner_valid_id_photocopy",
            "label": "Photocopy of the Document Owner’s Valid ID",
            "help": "Upload a clear photocopy of the document owner’s valid government-issued ID.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "representative_valid_id",
            "label": "Representative’s Valid Government-issued ID",
            "help": "Choose one valid government ID belonging to the representative, then upload a clear PDF or photo of that same ID.",
            "required": True,
            "id_choices": "barangay",
        },
    ),
    BIRTH_TYPE_DECEASED: (
        {
            "key": "requester_valid_id",
            "label": "Requester’s Valid Government-issued ID",
            "help": "Choose one valid government ID belonging to the requester, then upload a clear PDF or photo of that same ID.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "proof_of_relationship",
            "label": "Proof of Relationship to the Deceased",
            "help": "Upload a birth certificate or other supporting document that shows your relationship to the deceased, when required.",
            "required": True,
        },
        {
            "key": "proof_of_legal_authority",
            "label": "Proof of Legal Authority",
            "help": "Upload proof of legal authority when it applies to this request.",
            "required": True,
        },
    ),
}


def normalize_birth_type(application_type):
    selected = " ".join(str(application_type or "").split())
    if selected in BIRTH_APPLICATION_TYPES:
        return selected
    return selected


def document_requirements_for(application_type):
    """Return required upload rules for the selected birth certificate request type."""
    normalized = normalize_birth_type(application_type)
    docs = _DOCUMENTS_BY_TYPE.get(normalized) or _DOCUMENTS_BY_TYPE[BIRTH_TYPE_PERSONAL]
    return {
        "application_type": normalized or "",
        "note": (
            f"Upload every required document for {normalized or 'your selected request type'}. "
            "Proof of payment is collected on the payment step, not as a document upload."
        ),
        "documents": docs,
    }
