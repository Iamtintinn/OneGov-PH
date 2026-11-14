"""Certificate of Residency application types and required document uploads by type."""

RESIDENCY_TYPE_REGULAR = "Regular Application"
RESIDENCY_TYPE_EMPLOYMENT = "Employment Purpose"
RESIDENCY_TYPE_SCHOLARSHIP = "Scholarship / Educational Purpose"
RESIDENCY_TYPE_GOVERNMENT = "Government Transaction"
RESIDENCY_TYPE_REPRESENTATIVE = "Application Through an Authorized Representative"

RESIDENCY_APPLICATION_TYPES = (
    RESIDENCY_TYPE_REGULAR,
    RESIDENCY_TYPE_EMPLOYMENT,
    RESIDENCY_TYPE_SCHOLARSHIP,
    RESIDENCY_TYPE_GOVERNMENT,
    RESIDENCY_TYPE_REPRESENTATIVE,
)

RESIDENCY_TYPE_OPTIONS = (
    {
        "key": RESIDENCY_TYPE_REGULAR,
        "title": RESIDENCY_TYPE_REGULAR,
        "help": "For residents requesting proof of residency for personal, employment, or government transactions.",
    },
    {
        "key": RESIDENCY_TYPE_EMPLOYMENT,
        "title": RESIDENCY_TYPE_EMPLOYMENT,
        "help": "For residents requesting a Certificate of Residency for employment requirements.",
    },
    {
        "key": RESIDENCY_TYPE_SCHOLARSHIP,
        "title": RESIDENCY_TYPE_SCHOLARSHIP,
        "help": "For residents requesting proof of residency for school enrollment, scholarship applications, or educational assistance.",
    },
    {
        "key": RESIDENCY_TYPE_GOVERNMENT,
        "title": RESIDENCY_TYPE_GOVERNMENT,
        "help": "For residents requesting proof of residency for government applications, benefits, or other official transactions.",
    },
    {
        "key": RESIDENCY_TYPE_REPRESENTATIVE,
        "title": RESIDENCY_TYPE_REPRESENTATIVE,
        "help": "For applicants who cannot personally submit or collect their certificate, if representative processing is permitted.",
    },
)

_DOCUMENTS_BY_TYPE = {
    RESIDENCY_TYPE_REGULAR: (
        {
            "key": "valid_id",
            "label": "Valid Government-issued ID",
            "help": "Upload a clear PDF or photo of one government ID. The name should match this application.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "valid_id_photocopy",
            "label": "Photocopy of Valid ID",
            "help": "Upload a photocopy or secondary scan of your valid ID if required.",
            "required": True,
        },
        {
            "key": "proof_of_address",
            "label": "Proof of Residency",
            "help": "Upload a bill, lease, barangay certification, or other document that shows your current residential address.",
            "required": True,
        },
        {
            "key": "cedula",
            "label": "Community Tax Certificate (Cedula)",
            "help": "Upload your Community Tax Certificate (Cedula) if your barangay requires it.",
            "required": True,
        },
    ),
    RESIDENCY_TYPE_EMPLOYMENT: (
        {
            "key": "valid_id",
            "label": "Valid Government-issued ID",
            "help": "Upload a clear PDF or photo of one government ID. The name should match this application.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "valid_id_photocopy",
            "label": "Photocopy of Valid ID",
            "help": "Upload a photocopy or secondary scan of your valid ID if required.",
            "required": True,
        },
        {
            "key": "proof_of_address",
            "label": "Proof of Residency",
            "help": "Upload a document that shows your current residential address.",
            "required": True,
        },
        {
            "key": "employer_request",
            "label": "Employer’s Request Letter",
            "help": "Upload the employer’s request letter when required for employment purposes.",
            "required": True,
        },
        {
            "key": "cedula",
            "label": "Community Tax Certificate (Cedula)",
            "help": "Upload your Community Tax Certificate (Cedula) if required.",
            "required": True,
        },
    ),
    RESIDENCY_TYPE_SCHOLARSHIP: (
        {
            "key": "valid_id",
            "label": "Valid Government-issued ID",
            "help": "Upload a clear PDF or photo of one government ID. The name should match this application.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "proof_of_address",
            "label": "Proof of Residency",
            "help": "Upload a document that shows your current residential address.",
            "required": True,
        },
        {
            "key": "school_id",
            "label": "School ID",
            "help": "Upload your school ID when you have one for scholarship or educational purposes.",
            "required": True,
        },
        {
            "key": "scholarship_request",
            "label": "Scholarship or School Request Letter",
            "help": "Upload the scholarship or school request letter when required.",
            "required": True,
        },
        {
            "key": "cedula",
            "label": "Community Tax Certificate (Cedula)",
            "help": "Upload your Community Tax Certificate (Cedula) if required.",
            "required": True,
        },
    ),
    RESIDENCY_TYPE_GOVERNMENT: (
        {
            "key": "valid_id",
            "label": "Valid Government-issued ID",
            "help": "Upload a clear PDF or photo of one government ID. The name should match this application.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "valid_id_photocopy",
            "label": "Photocopy of Valid ID",
            "help": "Upload a photocopy or secondary scan of your valid ID if required.",
            "required": True,
        },
        {
            "key": "proof_of_address",
            "label": "Proof of Residency",
            "help": "Upload a document that shows your current residential address.",
            "required": True,
        },
        {
            "key": "government_request",
            "label": "Request Letter or Government Reference",
            "help": "Upload the government request letter or reference document when required.",
            "required": True,
        },
        {
            "key": "cedula",
            "label": "Community Tax Certificate (Cedula)",
            "help": "Upload your Community Tax Certificate (Cedula) if required.",
            "required": True,
        },
    ),
    RESIDENCY_TYPE_REPRESENTATIVE: (
        {
            "key": "applicant_valid_id",
            "label": "Applicant’s Valid Government-issued ID",
            "help": "Upload a clear photocopy of the applicant’s government-issued ID.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "representative_valid_id",
            "label": "Representative’s Valid Government-issued ID",
            "help": "Upload a clear PDF or photo of the representative’s government-issued ID.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "authorization_letter",
            "label": "Authorization Letter",
            "help": "Upload the authorization letter signed by the applicant.",
            "required": True,
        },
        {
            "key": "supporting_documents",
            "label": "Other Supporting Documents",
            "help": "Upload any other supporting documents the barangay asks for with a representative filing.",
            "required": True,
        },
    ),
}

_DEFAULT_DOCUMENTS = (
    {
        "key": "valid_id",
        "label": "Valid Government-issued ID",
        "help": "Upload a clear PDF or photo of one government ID. The name should match this application.",
        "required": True,
        "id_choices": "barangay",
    },
    {
        "key": "proof_of_address",
        "label": "Proof of Residency",
        "help": "Upload a document that shows your current residential address.",
        "required": True,
    },
    {
        "key": "cedula",
        "label": "Community Tax Certificate (Cedula)",
        "help": "Upload your Community Tax Certificate (Cedula) if required.",
        "required": True,
    },
)


def normalize_residency_type(application_type):
    selected = " ".join(str(application_type or "").split())
    if selected in RESIDENCY_APPLICATION_TYPES:
        return selected
    return selected


def document_requirements_for(application_type):
    """Return required upload rules for the selected residency certificate type."""
    normalized = normalize_residency_type(application_type)
    docs = _DOCUMENTS_BY_TYPE.get(normalized) or _DEFAULT_DOCUMENTS
    return {
        "application_type": normalized or "",
        "note": (
            "The barangay may still conduct an actual residency verification when necessary. "
            "Upload clear copies for each required document below."
        ),
        "documents": docs,
    }


def bring_requirements_for(application_type):
    """Deprecated helper kept for imports; physical bring lists are no longer shown on confirmation."""
    payload = document_requirements_for(application_type)
    return {
        "application_type": payload["application_type"],
        "note": payload["note"],
        "items": tuple(item["label"] for item in payload["documents"]),
    }
