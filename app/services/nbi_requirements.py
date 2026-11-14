"""NBI Clearance application types, New bring-list, and non-New upload requirements."""

NBI_TYPE_NEW = "New Application"
NBI_TYPE_RENEWAL = "Renewal Application"
NBI_TYPE_LOST = "Lost NBI Clearance"
NBI_TYPE_DAMAGED = "Damaged NBI Clearance"

NBI_APPLICATION_TYPES = (
    NBI_TYPE_NEW,
    NBI_TYPE_RENEWAL,
    NBI_TYPE_LOST,
    NBI_TYPE_DAMAGED,
)

NBI_TYPE_OPTIONS = (
    {
        "key": NBI_TYPE_NEW,
        "title": NBI_TYPE_NEW,
        "help": "For first-time applicants who must personally appear at an NBI Clearance Center for biometric registration.",
    },
    {
        "key": NBI_TYPE_RENEWAL,
        "title": NBI_TYPE_RENEWAL,
        "help": "For eligible applicants renewing an existing NBI Clearance. Physical appearance is not always required.",
    },
    {
        "key": NBI_TYPE_LOST,
        "title": NBI_TYPE_LOST,
        "help": "For applicants replacing a lost NBI Clearance. Additional verification may be required.",
    },
    {
        "key": NBI_TYPE_DAMAGED,
        "title": NBI_TYPE_DAMAGED,
        "help": "For applicants replacing a damaged NBI Clearance. Additional verification may be required.",
    },
)

_NEW_BRING_ITEMS = (
    "Two (2) valid government-issued identification documents – Original copies",
    "NBI Online Application Reference Number – Printed or digital copy",
    "Proof of Payment – Printed or digital copy",
)

_DOCUMENTS_BY_TYPE = {
    NBI_TYPE_NEW: (
        {
            "key": "valid_id",
            "label": "Valid Government-Issued ID",
            "help": "Choose one valid government ID from the searchable list, then upload a clear PDF or photo of that same ID.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "valid_id_secondary",
            "label": "Second valid government-issued ID",
            "help": "Choose a second valid government ID from the searchable list, then upload a clear PDF or photo of that same ID. Use a different ID from the first upload.",
            "required": True,
            "id_choices": "barangay",
        },
    ),
    NBI_TYPE_RENEWAL: (
        {
            "key": "previous_nbi_clearance",
            "label": "Previous NBI Clearance",
            "help": "Upload a digital or scanned copy of your previous NBI Clearance.",
            "required": True,
        },
        {
            "key": "valid_id",
            "label": "Valid Government-issued ID",
            "help": "Choose one valid government ID from the searchable list, then upload a clear PDF or photo of that same ID.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "renewal_reference",
            "label": "NBI Online Renewal Reference Number",
            "help": "Upload a printed or digital copy that shows your NBI online renewal reference number.",
            "required": True,
        },
    ),
    NBI_TYPE_LOST: (
        {
            "key": "valid_id",
            "label": "Valid Government-issued ID",
            "help": "Choose one valid government ID from the searchable list, then upload a clear PDF or photo of that same ID.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "previous_nbi_details",
            "label": "Previous NBI Clearance details",
            "help": "Upload any available copy or record of your previous NBI Clearance details.",
            "required": True,
        },
        {
            "key": "application_reference",
            "label": "NBI Application Reference Number",
            "help": "Upload a printed or digital copy that shows your NBI application reference number.",
            "required": True,
        },
        {
            "key": "affidavit_of_loss",
            "label": "Affidavit of Loss",
            "help": "Upload an Affidavit of Loss when NBI requires one for a lost clearance.",
            "required": True,
        },
    ),
    NBI_TYPE_DAMAGED: (
        {
            "key": "damaged_nbi_clearance",
            "label": "Damaged NBI Clearance",
            "help": "Upload a clear photo or scan of the damaged NBI Clearance, if available.",
            "required": True,
        },
        {
            "key": "valid_id",
            "label": "Valid Government-issued ID",
            "help": "Choose one valid government ID from the searchable list, then upload a clear PDF or photo of that same ID.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "application_reference",
            "label": "NBI Application Reference Number",
            "help": "Upload a printed or digital copy that shows your NBI application reference number.",
            "required": True,
        },
        {
            "key": "supporting_documents",
            "label": "Additional supporting documents",
            "help": "Upload any additional supporting documents requested for a damaged clearance replacement.",
            "required": True,
        },
    ),
}


def normalize_nbi_type(application_type):
    selected = " ".join(str(application_type or "").split())
    if selected in NBI_APPLICATION_TYPES:
        return selected
    return selected


def is_nbi_new_application(application_type):
    return normalize_nbi_type(application_type) == NBI_TYPE_NEW


def requires_nbi_schedule(application_type):
    return is_nbi_new_application(application_type)


def document_requirements_for(application_type):
    """Return required upload rules for the selected NBI application type."""
    normalized = normalize_nbi_type(application_type)
    docs = _DOCUMENTS_BY_TYPE.get(normalized) or _DOCUMENTS_BY_TYPE[NBI_TYPE_NEW]
    if normalized == NBI_TYPE_NEW:
        note = (
            "Upload two valid government-issued IDs for this monitoring request. "
            "Physical appearance is required for New Application. "
            "NBI captures the photograph and biometrics at the Clearance Center."
        )
    elif normalized == NBI_TYPE_RENEWAL:
        note = (
            "Upload the renewal documents below so this request can continue online. "
            "Physical appearance is not always required for renewal."
        )
    elif normalized == NBI_TYPE_LOST:
        note = (
            "Upload the documents below for a lost clearance request. "
            "Physical appearance is conditional and may be instructed by NBI."
        )
    else:
        note = (
            "Upload the documents below for a damaged clearance request. "
            "Physical appearance is conditional and may be instructed by NBI."
        )
    return {
        "application_type": normalized or "",
        "note": note,
        "documents": docs,
    }


def bring_requirements_for(application_type):
    """Physical documents checklist for New Application confirmation and receipt only."""
    normalized = normalize_nbi_type(application_type)
    if not is_nbi_new_application(normalized):
        return {
            "application_type": normalized or "",
            "note": None,
            "items": (),
            "appearance": None,
        }
    return {
        "application_type": normalized,
        "appearance": "REQUIRED",
        "note": (
            "Physical appearance is required. NBI personnel will capture your digital photograph, "
            "fingerprints, and electronic signature. Printed 2x2 ID photographs are not normally required "
            "because the official photograph is captured at the NBI office."
        ),
        "items": _NEW_BRING_ITEMS,
    }
