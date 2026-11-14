"""Barangay Clearance application types and required document uploads by type."""

BARANGAY_TYPE_REGULAR = "Regular Application"
BARANGAY_TYPE_EMPLOYMENT = "Employment Purpose"
BARANGAY_TYPE_FIRST_TIME_JOBSEEKER = "First-Time Jobseeker"
BARANGAY_TYPE_BANKING = "Banking / Financial Transactions"
BARANGAY_TYPE_SCHOLARSHIP = "Scholarship / Educational Purpose"
BARANGAY_TYPE_REPRESENTATIVE = "Application Through an Authorized Representative"

BARANGAY_APPLICATION_TYPES = (
    BARANGAY_TYPE_REGULAR,
    BARANGAY_TYPE_EMPLOYMENT,
    BARANGAY_TYPE_FIRST_TIME_JOBSEEKER,
    BARANGAY_TYPE_BANKING,
    BARANGAY_TYPE_SCHOLARSHIP,
    BARANGAY_TYPE_REPRESENTATIVE,
)

BARANGAY_TYPE_OPTIONS = (
    {
        "key": BARANGAY_TYPE_REGULAR,
        "title": BARANGAY_TYPE_REGULAR,
        "help": "For residents requesting a Barangay Clearance for employment, personal transactions, or other legal purposes.",
    },
    {
        "key": BARANGAY_TYPE_EMPLOYMENT,
        "title": BARANGAY_TYPE_EMPLOYMENT,
        "help": "For residents requesting Barangay Clearance as part of their employment requirements.",
    },
    {
        "key": BARANGAY_TYPE_FIRST_TIME_JOBSEEKER,
        "title": BARANGAY_TYPE_FIRST_TIME_JOBSEEKER,
        "help": "For qualified residents applying for employment for the first time under Republic Act No. 11261.",
    },
    {
        "key": BARANGAY_TYPE_BANKING,
        "title": BARANGAY_TYPE_BANKING,
        "help": "For residents requesting Barangay Clearance for bank account opening, loans, or other financial transactions.",
    },
    {
        "key": BARANGAY_TYPE_SCHOLARSHIP,
        "title": BARANGAY_TYPE_SCHOLARSHIP,
        "help": "For residents requesting Barangay Clearance for scholarship applications or educational requirements.",
    },
    {
        "key": BARANGAY_TYPE_REPRESENTATIVE,
        "title": BARANGAY_TYPE_REPRESENTATIVE,
        "help": "For applicants who cannot personally submit or collect their Barangay Clearance, if representative processing is permitted.",
    },
)

_DOCUMENTS_BY_TYPE = {
    BARANGAY_TYPE_REGULAR: (
        {
            "key": "valid_id",
            "label": "Valid Government-issued ID",
            "help": "Select one accepted government ID, then upload a clear PDF or photo of that same ID. The name should match this application.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "valid_id_photocopy",
            "label": "Photocopy of Valid ID",
            "help": "Upload a photocopy or secondary scan of your valid ID if your barangay requires one.",
            "required": True,
        },
        {
            "key": "residency_proof",
            "label": "Proof of Residency",
            "help": "Upload a barangay certification, utility bill, lease, or other document that shows you live in this barangay.",
            "required": True,
        },
        {
            "key": "cedula",
            "label": "Community Tax Certificate (Cedula)",
            "help": "Upload your Community Tax Certificate (Cedula) if your barangay requires it for clearance.",
            "required": True,
        },
    ),
    BARANGAY_TYPE_EMPLOYMENT: (
        {
            "key": "valid_id",
            "label": "Valid Government-issued ID",
            "help": "Select one accepted government ID, then upload a clear PDF or photo of that same ID.",
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
            "key": "residency_proof",
            "label": "Proof of Residency",
            "help": "Upload a document that shows you live in this barangay.",
            "required": True,
        },
        {
            "key": "cedula",
            "label": "Community Tax Certificate (Cedula)",
            "help": "Upload your Community Tax Certificate (Cedula) if required.",
            "required": True,
        },
        {
            "key": "employer_request",
            "label": "Employer’s Request Letter",
            "help": "Upload the employer’s request letter when your barangay or employer requires one.",
            "required": True,
        },
    ),
    BARANGAY_TYPE_FIRST_TIME_JOBSEEKER: (
        {
            "key": "valid_id",
            "label": "Valid Government-issued ID",
            "help": "Select one accepted government ID, then upload a clear PDF or photo of that same ID.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "residency_proof",
            "label": "Proof of Residency",
            "help": "Upload a document that shows you live in this barangay.",
            "required": True,
        },
        {
            "key": "first_time_jobseeker_cert",
            "label": "First-Time Jobseeker Certification",
            "help": "Upload your First-Time Jobseeker Certification under RA 11261.",
            "required": True,
        },
        {
            "key": "oath_of_undertaking",
            "label": "Oath of Undertaking",
            "help": "Upload the signed Oath of Undertaking required for first-time jobseeker clearance.",
            "required": True,
        },
    ),
    BARANGAY_TYPE_BANKING: (
        {
            "key": "valid_id",
            "label": "Valid Government-issued ID",
            "help": "Select one accepted government ID, then upload a clear PDF or photo of that same ID.",
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
            "key": "residency_proof",
            "label": "Proof of Residency",
            "help": "Upload a document that shows you live in this barangay.",
            "required": True,
        },
        {
            "key": "cedula",
            "label": "Community Tax Certificate (Cedula)",
            "help": "Upload your Community Tax Certificate (Cedula) if required.",
            "required": True,
        },
        {
            "key": "bank_request",
            "label": "Bank or Financial Institution Request",
            "help": "Upload the bank or financial institution request when required for this clearance.",
            "required": True,
        },
    ),
    BARANGAY_TYPE_SCHOLARSHIP: (
        {
            "key": "valid_id",
            "label": "Valid Government-issued ID",
            "help": "Select one accepted government ID, then upload a clear PDF or photo of that same ID.",
            "required": True,
            "id_choices": "barangay",
        },
        {
            "key": "residency_proof",
            "label": "Proof of Residency",
            "help": "Upload a document that shows you live in this barangay.",
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
            "label": "Scholarship Request Letter",
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
    BARANGAY_TYPE_REPRESENTATIVE: (
        {
            "key": "applicant_valid_id",
            "label": "Applicant’s Valid Government-issued ID",
            "help": "Upload a clear copy of the applicant’s government-issued ID.",
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
            "help": "Upload any other supporting documents your barangay asks for with a representative filing.",
            "required": True,
        },
    ),
}

_DEFAULT_DOCUMENTS = (
    {
        "key": "valid_id",
        "label": "Valid Government-issued ID",
        "help": "Select one accepted government ID, then upload a clear PDF or photo of that same ID.",
        "required": True,
        "id_choices": "barangay",
    },
    {
        "key": "residency_proof",
        "label": "Proof of Residency",
        "help": "Upload a document that shows you live in this barangay.",
        "required": True,
    },
    {
        "key": "cedula",
        "label": "Community Tax Certificate (Cedula)",
        "help": "Upload your Community Tax Certificate (Cedula) if your barangay requires it.",
        "required": True,
    },
)


def normalize_barangay_type(application_type):
    selected = " ".join(str(application_type or "").split())
    if selected in BARANGAY_APPLICATION_TYPES:
        return selected
    return selected


def document_requirements_for(application_type):
    """Return required upload rules for the selected barangay clearance type."""
    normalized = normalize_barangay_type(application_type)
    docs = _DOCUMENTS_BY_TYPE.get(normalized) or _DEFAULT_DOCUMENTS
    note = None
    if normalized == BARANGAY_TYPE_FIRST_TIME_JOBSEEKER:
        note = (
            "Eligible first-time jobseekers may qualify for free issuance of covered pre-employment "
            "documents under RA 11261, subject to its requirements."
        )
    return {
        "application_type": normalized or "",
        "note": note,
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
