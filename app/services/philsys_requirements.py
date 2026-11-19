"""PhilSys National ID application types and type-specific document requirements."""

PHILSYS_TYPE_LOST = "Lost National ID"
PHILSYS_TYPE_DAMAGED = "Damaged National ID"
PHILSYS_TYPE_DEFECTIVE = "Defective National ID"
PHILSYS_TYPE_PEELED = "Peeled-off Photograph"
PHILSYS_TYPE_DISASTER = "Replacement Due to Natural Disaster"

PHILSYS_APPLICATION_TYPES = (
    PHILSYS_TYPE_LOST,
    PHILSYS_TYPE_DAMAGED,
    PHILSYS_TYPE_DEFECTIVE,
    PHILSYS_TYPE_PEELED,
    PHILSYS_TYPE_DISASTER,
)

PHILSYS_TYPE_OPTIONS = (
    {
        "key": PHILSYS_TYPE_LOST,
        "title": PHILSYS_TYPE_LOST,
        "help": "For replacing a lost National ID. Upload a notarized affidavit of loss and a valid ID if available.",
    },
    {
        "key": PHILSYS_TYPE_DAMAGED,
        "title": PHILSYS_TYPE_DAMAGED,
        "help": "For replacing a damaged National ID. Upload a photo of the damaged card and the original card if required by PSA.",
    },
    {
        "key": PHILSYS_TYPE_DEFECTIVE,
        "title": PHILSYS_TYPE_DEFECTIVE,
        "help": "For replacing a National ID with a printing or identification defect. Upload a photo showing the defect.",
    },
    {
        "key": PHILSYS_TYPE_PEELED,
        "title": PHILSYS_TYPE_PEELED,
        "help": "For replacing a National ID with a peeled or detached photograph. Upload a photo of the issue and the original card.",
    },
    {
        "key": PHILSYS_TYPE_DISASTER,
        "title": PHILSYS_TYPE_DISASTER,
        "help": "For replacement due to natural disaster. Upload proof of disaster-related loss or damage and supporting identification if available.",
    },
)

_DOCUMENTS_BY_TYPE = {
    PHILSYS_TYPE_LOST: (
        {
            "key": "affidavit_of_loss",
            "label": "Notarized Affidavit of Loss",
            "help": "Upload a clear scan or photo of the notarized Affidavit of Loss.",
            "required": True,
        },
        {
            "key": "valid_id",
            "label": "Valid government-issued ID, if available",
            "help": "If available, choose one valid government ID from the list and upload a clear copy of that same ID.",
            "required": False,
            "id_choices": "barangay",
        },
    ),
    PHILSYS_TYPE_DAMAGED: (
        {
            "key": "damaged_id_photo",
            "label": "Photo of damaged National ID",
            "help": "Upload a clear photo showing the damaged National ID.",
            "required": True,
        },
        {
            "key": "original_damaged_id",
            "label": "Original damaged National ID, if required by PSA",
            "help": "If required by PSA, upload a clear scan or photo of the original damaged National ID. Bring the original to the authorized PSA center when requested.",
            "required": False,
        },
    ),
    PHILSYS_TYPE_DEFECTIVE: (
        {
            "key": "defect_photo",
            "label": "Photo showing printing or identification defect",
            "help": "Upload a clear photo showing the printing or identification defect on the National ID.",
            "required": True,
        },
        {
            "key": "original_defective_id",
            "label": "Original defective National ID, if required by PSA",
            "help": "If required by PSA, upload a clear scan or photo of the original defective National ID. Bring the original to the authorized PSA center when requested.",
            "required": False,
        },
    ),
    PHILSYS_TYPE_PEELED: (
        {
            "key": "peeled_photo",
            "label": "Photo showing peeled or detached photograph",
            "help": "Upload a clear photo showing the peeled or detached photograph on the National ID.",
            "required": True,
        },
        {
            "key": "original_national_id",
            "label": "Original National ID",
            "help": "Upload a clear scan or photo of the original National ID. Bring the original to the authorized PSA center when requested.",
            "required": True,
        },
    ),
    PHILSYS_TYPE_DISASTER: (
        {
            "key": "disaster_proof",
            "label": "Barangay Certification or other proof of disaster-related loss or damage",
            "help": "Upload a Barangay Certification or other proof showing disaster-related loss or damage.",
            "required": True,
        },
        {
            "key": "supporting_identification",
            "label": "Supporting identification, if available",
            "help": "If available, choose one valid government ID from the list and upload a clear copy of that same ID.",
            "required": False,
            "id_choices": "barangay",
        },
    ),
}


def normalize_philsys_type(application_type):
    selected = " ".join(str(application_type or "").split())
    if selected in PHILSYS_APPLICATION_TYPES:
        return selected
    return selected


def document_requirements_for(application_type):
    """Return upload requirements for the selected PhilSys application type."""
    normalized = normalize_philsys_type(application_type)
    docs = _DOCUMENTS_BY_TYPE.get(normalized) or _DOCUMENTS_BY_TYPE[PHILSYS_TYPE_LOST]
    return {
        "application_type": normalized or "",
        "note": "Required documents depend on the selected PhilSys National ID application type.",
        "documents": docs,
    }
