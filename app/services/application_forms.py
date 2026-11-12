"""Application questions and document lists for each catalog service."""


def _field(
    key,
    label,
    help_text,
    field_type="text",
    required=True,
    options=None,
    max_length=160,
    section=None,
    source=None,
    empty=None,
    calc=None,
    min_age=None,
    allow_future=False,
    step=None,
    default=None,
    show_when=None,
    show_if_set=None,
    required_when_shown=False,
    lookup=None,
    placeholder=None,
):
    item = {
        "key": key,
        "label": label,
        "help": help_text,
        "type": field_type,
        "required": required,
        "max_length": max_length,
    }
    if options is not None:
        item["options"] = options
    if section:
        item["section"] = section
    if source:
        item["source"] = source
    if empty:
        item["empty"] = empty
    if calc:
        item["calc"] = calc
    if min_age:
        item["min_age"] = min_age
    if allow_future:
        item["allow_future"] = True
    if step:
        item["step"] = step
    if default is not None:
        item["default"] = default
    rules = []
    if show_if_set:
        for source_key in show_if_set:
            rules.append({"key": source_key, "set": True})
    if show_when is not None:
        pairs = show_when if isinstance(show_when[0], (list, tuple)) else (show_when,)
        for pair in pairs:
            rules.append({"key": pair[0], "equals": pair[1]})
        item["show_when"] = show_when
    if rules:
        item["show_rules"] = rules
    if required_when_shown:
        item["required_when_shown"] = True
    if lookup:
        item["lookup"] = lookup
    if placeholder:
        item["placeholder"] = placeholder
    return item


def field_is_visible(field, source):
    """True when every display rule matches the current answers."""
    for rule in field.get("show_rules") or []:
        current = source.get(rule["key"], "") if source is not None else ""
        current = "" if current is None else str(current).strip()
        if rule.get("set"):
            if not current:
                return False
        elif current != rule.get("equals"):
            return False
    return True


def _document(key, label, help_text, required=True, required_unless=None, required_when=None, id_choices=None):
    item = {
        "key": key,
        "label": label,
        "help": help_text,
        "required": required,
    }
    if required_unless is not None:
        item["required_unless"] = required_unless
    if required_when is not None:
        item["required_when"] = required_when
    if id_choices:
        item["id_choices"] = id_choices
    return item


_SEX = ("Female", "Male")
_CIVIL_STATUS = ("Single", "Married", "Widowed", "Separated", "Divorced")

PERSONAL_FIELDS = (
    _field("first_name", "First name", "Enter your first name as it appears on your identification."),
    _field(
        "middle_name",
        "Middle name",
        "Leave this blank if you have no middle name.",
        required=False,
    ),
    _field("last_name", "Last name", "Enter your last name as it appears on your identification."),
    _field(
        "date_of_birth",
        "Date of birth",
        "Use the date of birth on your birth record.",
        field_type="date",
    ),
    _field("sex", "Sex", "Select the sex recorded on your identification.", field_type="select", options=_SEX),
    _field(
        "civil_status",
        "Civil status",
        "Select your civil status today.",
        field_type="select",
        options=_CIVIL_STATUS,
    ),
    _field("nationality", "Nationality", "Enter your nationality. Most applicants enter Filipino."),
    _field(
        "address",
        "Complete address",
        "Include the house number, street, barangay, city or municipality, and province.",
        field_type="textarea",
        max_length=500,
    ),
    _field(
        "contact_number",
        "Contact number",
        "Enter a mobile number where the office can reach you.",
        field_type="tel",
        max_length=20,
    ),
    _field(
        "email",
        "Email address",
        "Enter an email address you can open. Status messages are also shown in OneGov PH.",
        field_type="email",
        max_length=255,
    ),
)

_VALID_ID = _document(
    "valid_id",
    "Valid government ID",
    "Upload a clear PDF or photo of one government ID. The name should match this application.",
)


def _service(
    process,
    fields,
    documents,
):
    return {
        "process": process,
        "fields": fields,
        "documents": documents,
    }


SERVICE_FORMS = {
    "Birth Certificate": _service(
        "OneGov PH records your PSA birth certificate request so you can track the details and documents you prepared. PSA still issues the certificate.",
        (
            _field(
                "certificate_for",
                "Who is named on the certificate",
                "Choose Self if the certificate is yours. Choose another option if you are requesting it for a relative.",
                field_type="select",
                options=("Self", "Child", "Parent", "Spouse", "Other relative"),
            ),
            _field("owner_first_name", "Certificate owner's first name", "Enter the first name printed on the birth record."),
            _field(
                "owner_middle_name",
                "Certificate owner's middle name",
                "Leave this blank if the birth record has no middle name.",
                required=False,
            ),
            _field("owner_last_name", "Certificate owner's last name", "Enter the last name printed on the birth record."),
            _field(
                "owner_birth_date",
                "Certificate owner's date of birth",
                "Use the date of birth on the birth record.",
                field_type="date",
            ),
            _field("place_of_birth", "Place of birth", "Enter the city or municipality and province of birth."),
            _field("father_name", "Father's complete name", "Enter the father's name as it should appear on the record."),
            _field(
                "mother_maiden_name",
                "Mother's complete maiden name",
                "Enter the mother's maiden name, not her married name.",
            ),
            _field(
                "copies",
                "Number of copies",
                "Enter how many copies you are preparing to request, from 1 to 5.",
                field_type="number",
                max_length=1,
            ),
            _field(
                "purpose",
                "Purpose of the request",
                "Example: school, passport, employment, or a personal record.",
                field_type="textarea",
                max_length=400,
            ),
        ),
        (
            _VALID_ID,
            _document(
                "authorization",
                "Authorization letter",
                "Required when the certificate is not your own. Upload a signed letter from the document owner, or your proof of relationship.",
                required=False,
                required_unless=("certificate_for", "Self"),
            ),
        ),
    ),
    "CENOMAR": {"compose": "cenomar"},
    "Passport Application Assistance and Tracking": {
        **_service(
            "OneGov PH records passport demonstration details for portfolio tracking. "
            "This is not an official DFA application.",
            (
                _field(
                    "application_type",
                    "Application type",
                    "Choose whether this is a new passport or a renewal.",
                    field_type="select",
                    options=("New", "Renewal"),
                ),
                _field("place_of_birth", "Place of birth", "Enter the place of birth shown on your birth record."),
            ),
            (
                _document(
                    "valid_id",
                    "Valid government ID",
                    "Select one ID. Upload a clear, readable, untampered PDF, JPG, JPEG, or PNG no larger than 16 MB. "
                    "Use a synthetic sample for public demonstration accounts.",
                    id_choices="dfa",
                ),
            ),
        ),
        "kind": "passport",
        "kicker": "Passport demonstration",
        "department_label": "Passport demonstration",
        "upload_intro": (
            "Select one valid government ID, then upload a clear PDF or photo of that same ID "
            "(PDF, JPG, JPEG, or PNG, up to 16 MB). Readable name, birth date, and other details "
            "from the ID will auto-fill the application form on the next step."
        ),
        "disclaimer": (
            "OneGov PH is an independent portfolio demonstration. This platform is not affiliated with or authorized by "
            "the Department of Foreign Affairs (DFA). All appointment schedules, payments, confirmations, and tracking "
            "records are simulated."
        ),
        "step_labels": (
            "1. Documents",
            "2. Application details",
            "3. Scheduling",
            "4. Payment",
            "5. Confirmation",
        ),
        "documents_first": True,
        "confirmation_step": 5,
        "status_labels": {
            "paid": "Paid",
            "scheduled": "Scheduled",
        },
        "submit_event": (
            "Passport appointment and payment were saved in OneGov PH."
        ),
        "submit_notice": (
            "Your passport request {reference} was saved in OneGov PH."
        ),
        "next_steps": (
            "Keep your confirmation ID and reference number.",
            "Open Application tracking to see status changes on your account.",
            "Download the PDF confirmation for your records.",
        ),
    },
    "NBI Clearance Application Monitoring": {"compose": "nbi"},
    "Barangay Clearance": {"compose": "barangay"},
    "Certificate of Residency": {"compose": "residency"},
    "Senior Citizen ID": {"compose": "senior"},
    "SS Number Application Assistance and Tracking": {"compose": "sss"},
    "SS Number Registration Assistance and Tracking": {"compose": "sss"},
}


BARANGAY_DISCLAIMER = (
    "OneGov PH keeps this request for assistance and tracking. "
    "It is not sent to the agency as an official filing. "
    "The barangay remains responsible for reviewing the request and issuing the official clearance."
)
BARANGAY_FEE_NOTE = (
    "Processing Fee: Depends on your local barangay. "
    "Please confirm the actual amount with your barangay before proceeding. "
    "OneGov PH does not collect this payment."
)

# Add a record here only after that barangay's fee, documents, and office details are confirmed.
# Keys are "city|barangay" in lowercase, with extra spaces removed.
VERIFIED_BARANGAYS = {}


def _place_key(city, barangay):
    def norm(value):
        return " ".join(str(value or "").casefold().split())

    city_name = norm(city)
    barangay_name = norm(barangay)
    if not city_name or not barangay_name:
        return ""
    return f"{city_name}|{barangay_name}"


def barangay_profile(values):
    """Return verified local rules, or a starting list when none are on file."""
    key = _place_key(values.get("city"), values.get("barangay"))
    verified = VERIFIED_BARANGAYS.get(key) if key else None
    if verified:
        return {"verified": True, **verified}
    return {
        "verified": False,
        "require_date_of_birth": False,
        "require_sex": False,
        "require_civil_status": False,
        "require_nationality": False,
        "documents": {
            "valid_id": True,
            "residency_proof": True,
            "cedula": False,
        },
        "fee_amount": None,
        "address": None,
        "contact_number": None,
        "office_hours": None,
        "instructions": None,
    }


def compose_barangay_clearance(values=None):
    """Barangay Clearance rules. Other services keep their own field and document lists."""
    answers = values or {}
    profile = barangay_profile(answers)
    city = " ".join(str(answers.get("city") or "").split())
    barangay = " ".join(str(answers.get("barangay") or "").split())
    applicant = "Applicant information"
    residency = "Residency information"
    purpose_section = "Purpose of clearance"
    fields = [
        _field(
            "first_name",
            "First name",
            "Enter your first name as it appears on your identification.",
            section=applicant,
        ),
        _field(
            "middle_name",
            "Middle name",
            "Leave this blank if you have no middle name.",
            required=False,
            section=applicant,
        ),
        _field(
            "last_name",
            "Last name",
            "Enter your last name as it appears on your identification.",
            section=applicant,
        ),
        _field(
            "date_of_birth",
            "Date of birth",
            "This barangay asks for your date of birth."
            if profile["require_date_of_birth"]
            else "Enter your date of birth if the issuing barangay asks for it. Leave this blank when it does not.",
            field_type="date",
            required=profile["require_date_of_birth"],
            section=applicant,
        ),
        _field(
            "sex",
            "Sex",
            "This barangay asks for the sex recorded on your identification."
            if profile["require_sex"]
            else "Select this only if the issuing barangay asks for it.",
            field_type="select",
            required=profile["require_sex"],
            options=_SEX,
            section=applicant,
        ),
        _field(
            "civil_status",
            "Civil status",
            "This barangay asks for your civil status."
            if profile["require_civil_status"]
            else "Select this only if the issuing barangay asks for it.",
            field_type="select",
            required=profile["require_civil_status"],
            options=_CIVIL_STATUS,
            section=applicant,
        ),
        _field(
            "address",
            "Complete address",
            "Include the house or building, street, and province. Enter the city and barangay in the residency section.",
            field_type="textarea",
            max_length=500,
            section=applicant,
        ),
        _field(
            "contact_number",
            "Contact number",
            "Enter a mobile or telephone number the barangay can use. Include the area code for a landline.",
            field_type="tel",
            max_length=20,
            section=applicant,
        ),
        _field(
            "email",
            "Email address",
            "Enter an email address you can open. Status messages are also shown in OneGov PH.",
            field_type="email",
            max_length=255,
            section=applicant,
        ),
        _field(
            "city",
            "City or municipality",
            "Enter the city or municipality of the barangay that will issue the clearance.",
            section=residency,
        ),
        _field(
            "barangay",
            "Barangay",
            "Enter the barangay that should issue the clearance. Requirements and fees can differ by barangay.",
            section=residency,
        ),
        _field(
            "years_residing",
            "Years living in the barangay",
            "Enter how many years you have lived there. Use 0 if it is less than one year.",
            field_type="number",
            max_length=3,
            section=residency,
        ),
        _field(
            "purpose",
            "Purpose of the clearance",
            "Example: employment, a business permit, or a school requirement.",
            field_type="textarea",
            max_length=400,
            section=purpose_section,
        ),
    ]
    if profile["require_nationality"]:
        fields.insert(
            6,
            _field(
                "nationality",
                "Nationality",
                "This barangay asks for your nationality.",
                section=applicant,
            ),
        )
    documents = (
        _document(
            "valid_id",
            "Valid government-issued ID",
            "Upload a clear PDF or photo of one government ID. The name should match this application.",
            required=bool(profile["documents"].get("valid_id", True)),
        ),
        _document(
            "residency_proof",
            "Proof of residency",
            "Upload a bill, lease, or other document that shows you live in this barangay.",
            required=bool(profile["documents"].get("residency_proof", True)),
        ),
        _document(
            "cedula",
            "Community Tax Certificate (Cedula)",
            "This barangay requires a community tax certificate."
            if profile["documents"].get("cedula")
            else "Upload a cedula only if this barangay asks for one. Leave it out when the barangay does not require it.",
            required=bool(profile["documents"].get("cedula", False)),
        ),
    )
    if profile["verified"] and barangay and city:
        document_note = (
            f"This checklist follows the verified requirements on file for {barangay}, {city}. "
            "Another barangay can ask for a different set of documents."
        )
    elif barangay and city:
        document_note = (
            f"OneGov PH does not have a verified requirement list for {barangay}, {city}. "
            "The checklist below is a starting list. Confirm it with the barangay, because requirements are not the same everywhere."
        )
    else:
        document_note = (
            "Document requirements depend on the barangay that will issue the clearance. "
            "This starting list can change when a verified requirement list is on file."
        )
    fee_amount = profile.get("fee_amount")
    if profile["verified"] and fee_amount is not None:
        fee_note = (
            f"Processing Fee: ₱{fee_amount} for this barangay. "
            "Please confirm the actual amount with your barangay before proceeding. "
            "OneGov PH does not collect this payment."
        )
    else:
        fee_note = BARANGAY_FEE_NOTE
    office = {
        "barangay": barangay,
        "city": city,
        "note": ""
        if profile["verified"]
        else "OneGov PH does not have a verified office address, contact number, or office hours for this barangay. Confirm those details with the barangay before you visit.",
    }
    for source_key, office_key in (
        ("address", "address"),
        ("contact_number", "contact_number"),
        ("office_hours", "office_hours"),
        ("instructions", "instructions"),
    ):
        if profile["verified"] and profile.get(source_key):
            office[office_key] = profile[source_key]
    return {
        "kind": "barangay",
        "kicker": "Local government request",
        "department_label": "Barangay assistance",
        "process": "Prepare a barangay clearance request for the barangay you name below. That barangay still reviews the request and issues the clearance.",
        "fields": fields,
        "documents": documents,
        "document_note": document_note,
        "fee_note": fee_note,
        "catalog_fee": BARANGAY_FEE_NOTE,
        "disclaimer": BARANGAY_DISCLAIMER,
        "local_office": office,
        "show_submitted_details": True,
        "step_labels": (
            "1. Application details",
            "2. Documents",
            "3. Review",
            "4. Confirmation",
        ),
        "terms": "I confirm that the information and documents in this request are accurate. " + BARANGAY_DISCLAIMER,
        "next_steps": [
            "Keep your reference number and use it when you ask the barangay about this request.",
            "Confirm the processing fee and the documents with the barangay. OneGov PH does not collect the fee.",
            "The barangay reviews the request and issues the official clearance. OneGov PH does not mark this request approved or completed.",
            "Open Application tracking to follow status changes and any instructions recorded on your account.",
        ],
        "submit_event": (
            "Barangay clearance request saved for assistance and tracking. "
            "The barangay has not reviewed it, and OneGov PH has not marked it approved or completed."
        ),
        "submit_notice": (
            "Your Barangay Clearance request {reference} was submitted in OneGov PH. "
            "It is not an official filing. The barangay remains responsible for reviewing it and issuing the clearance."
        ),
        "status_labels": {
            "submitted": "Submitted",
            "pending_documents": "Additional documents required",
            "ready_for_release": "Ready for pickup",
        },
    }


RESIDENCY_DISCLAIMER = (
    "OneGov PH keeps this request for assistance and tracking. "
    "It is not sent to the agency as an official filing. "
    "The barangay or city government remains responsible for verifying residency and issuing the official certificate."
)
RESIDENCY_FEE_NOTE = (
    "Processing Fee: Depends on the issuing barangay or city. "
    "Please confirm the actual fee with your local government office. "
    "OneGov PH does not collect this payment."
)

# Add a record only after that barangay or city confirms its fee, documents, and office details.
# Keys are "city|barangay" in lowercase, with extra spaces removed.
VERIFIED_RESIDENCY_OFFICES = {}


def residency_profile(values):
    """Return verified local rules, or a starting list when none are on file."""
    key = _place_key(values.get("city"), values.get("barangay"))
    verified = VERIFIED_RESIDENCY_OFFICES.get(key) if key else None
    if verified:
        return {"verified": True, **verified}
    return {
        "verified": False,
        "require_date_of_birth": False,
        "require_sex": False,
        "require_civil_status": False,
        "require_nationality": False,
        "require_previous_address": False,
        "documents": {
            "valid_id": True,
            "proof_of_address": True,
            "barangay_clearance": False,
            "affidavit": False,
        },
        "extra_documents": [],
        "fee_amount": None,
        "address": None,
        "contact_number": None,
        "office_hours": None,
        "instructions": None,
    }


def _extra_documents(profile):
    extras = []
    for item in profile.get("extra_documents") or []:
        key = str(item.get("key") or "")
        label = " ".join(str(item.get("label") or "").split())
        if not key.isidentifier() or not label:
            continue
        extras.append(
            _document(
                key,
                label,
                item.get("help") or "Upload this supporting document named by the local government.",
                required=bool(item.get("required", True)),
            )
        )
    return tuple(extras)


def compose_certificate_of_residency(values=None):
    """Certificate of Residency rules. Barangay Clearance keeps its own form."""
    answers = values or {}
    profile = residency_profile(answers)
    city = " ".join(str(answers.get("city") or "").split())
    barangay = " ".join(str(answers.get("barangay") or "").split())
    personal = "Personal information"
    residential = "Residential information"
    duration = "Residency duration"
    purpose_section = "Purpose of certificate"
    fields = [
        _field(
            "first_name",
            "First name",
            "Enter your first name as it appears on your identification.",
            section=personal,
        ),
        _field(
            "middle_name",
            "Middle name",
            "Leave this blank if you have no middle name.",
            required=False,
            section=personal,
        ),
        _field(
            "last_name",
            "Last name",
            "Enter your last name as it appears on your identification.",
            section=personal,
        ),
        _field(
            "date_of_birth",
            "Date of birth",
            "This local government asks for your date of birth."
            if profile["require_date_of_birth"]
            else "Enter your date of birth if the issuing barangay or city asks for it. Leave this blank when it does not.",
            field_type="date",
            required=profile["require_date_of_birth"],
            section=personal,
        ),
        _field(
            "sex",
            "Sex",
            "This local government asks for the sex recorded on your identification."
            if profile["require_sex"]
            else "Select this only if the issuing barangay or city asks for it.",
            field_type="select",
            required=profile["require_sex"],
            options=_SEX,
            section=personal,
        ),
        _field(
            "civil_status",
            "Civil status",
            "This local government asks for your civil status."
            if profile["require_civil_status"]
            else "Select this only if the issuing barangay or city asks for it.",
            field_type="select",
            required=profile["require_civil_status"],
            options=_CIVIL_STATUS,
            section=personal,
        ),
        _field(
            "contact_number",
            "Contact number",
            "Enter a mobile or telephone number the office can use. Include the area code for a landline.",
            field_type="tel",
            max_length=20,
            section=personal,
        ),
        _field(
            "email",
            "Email address",
            "Enter an email address you can open. Status messages are also shown in OneGov PH.",
            field_type="email",
            max_length=255,
            section=personal,
        ),
        _field(
            "address",
            "Complete residential address",
            "Enter the house or building, street, and province where you live now. This is your current residential address. City and barangay are entered below.",
            field_type="textarea",
            max_length=500,
            section=residential,
        ),
        _field(
            "city",
            "City or municipality",
            "Enter the city or municipality that covers your current address.",
            section=residential,
        ),
        _field(
            "barangay",
            "Barangay",
            "Enter the barangay of your current address. Requirements and fees can differ by barangay or city.",
            section=residential,
        ),
        _field(
            "previous_address",
            "Previous address",
            "Enter the address where you lived before this one, if you have it. Leave this blank if you do not need to provide it."
            if not profile["require_previous_address"]
            else "This local government asks for the address where you lived before your current one.",
            field_type="textarea",
            required=profile["require_previous_address"],
            max_length=500,
            section=residential,
        ),
        _field(
            "residency_started",
            "Date started living at current address",
            "Enter the date you began living at the address above. OneGov PH uses it to calculate how long you have lived there.",
            field_type="date",
            section=duration,
        ),
        _field(
            "length_of_residency",
            "Length of residency",
            "This is calculated from the date you started living at your current address. You do not need to type it.",
            field_type="computed",
            required=False,
            source="residency_started",
            empty="Enter the date you started living at this address.",
            section=duration,
        ),
        _field(
            "purpose",
            "Purpose of the certificate",
            "Example: school enrollment, employment, a bank account, or a government transaction.",
            field_type="textarea",
            max_length=400,
            section=purpose_section,
        ),
    ]
    if profile["require_nationality"]:
        fields.insert(
            6,
            _field(
                "nationality",
                "Nationality",
                "This local government asks for your nationality.",
                section=personal,
            ),
        )
    documents = [
        _document(
            "valid_id",
            "Valid government-issued ID",
            "Upload a clear PDF or photo of one government ID. The name should match this application.",
            required=bool(profile["documents"].get("valid_id", True)),
        ),
        _document(
            "proof_of_address",
            "Proof of address",
            "Upload a bill, lease, or other document that shows your current residential address.",
            required=bool(profile["documents"].get("proof_of_address", True)),
        ),
        _document(
            "barangay_clearance",
            "Barangay clearance",
            "This local government requires a barangay clearance."
            if profile["documents"].get("barangay_clearance")
            else "Upload a barangay clearance only if the issuing barangay or city asks for one.",
            required=bool(profile["documents"].get("barangay_clearance", False)),
        ),
        _document(
            "affidavit",
            "Affidavit of residency",
            "This local government requires an affidavit of residency."
            if profile["documents"].get("affidavit")
            else "Upload an affidavit of residency only if the issuing barangay or city asks for one.",
            required=bool(profile["documents"].get("affidavit", False)),
        ),
    ]
    documents.extend(_extra_documents(profile))
    if profile["verified"] and barangay and city:
        document_note = (
            f"This checklist follows the verified requirements on file for {barangay}, {city}. "
            "Another barangay or city can ask for different documents."
        )
    elif barangay and city:
        document_note = (
            f"OneGov PH does not have a verified requirement list for {barangay}, {city}. "
            "The checklist below is a starting list. Confirm it with the barangay or city, because requirements are not the same everywhere."
        )
    else:
        document_note = (
            "Document requirements depend on the barangay or city that will issue the certificate. "
            "This starting list can change when a verified requirement list is on file."
        )
    fee_amount = profile.get("fee_amount")
    if profile["verified"] and fee_amount is not None:
        fee_note = (
            f"Processing Fee: ₱{fee_amount} for this local government office. "
            "Please confirm the actual fee with your local government office. "
            "OneGov PH does not collect this payment."
        )
    else:
        fee_note = RESIDENCY_FEE_NOTE
    office = {
        "heading": "Issuing office",
        "address_label": "Office address",
        "instructions_heading": "Instructions from the local government",
        "barangay": barangay,
        "city": city,
        "note": ""
        if profile["verified"]
        else "OneGov PH does not have a verified office address, contact number, or office hours for this barangay or city. Confirm those details with the local government office before you visit.",
    }
    for source_key, office_key in (
        ("address", "address"),
        ("contact_number", "contact_number"),
        ("office_hours", "office_hours"),
        ("instructions", "instructions"),
    ):
        if profile["verified"] and profile.get(source_key):
            office[office_key] = profile[source_key]
    return {
        "kind": "residency",
        "process": "Prepare a certificate of residency for the barangay or city you name below. That office still verifies your residency and issues the certificate.",
        "fields": fields,
        "documents": tuple(documents),
        "document_note": document_note,
        "fee_note": fee_note,
        "catalog_fee": RESIDENCY_FEE_NOTE,
        "disclaimer": RESIDENCY_DISCLAIMER,
        "local_office": office,
        "show_submitted_details": True,
        "terms": "I confirm that the information and documents in this request are accurate. " + RESIDENCY_DISCLAIMER,
        "next_steps": [
            "Keep your reference number and use it when you ask the barangay or city about this request.",
            "Confirm the processing fee and the documents with the local government office. OneGov PH does not collect the fee.",
            "The barangay or city verifies residency and issues the official certificate. OneGov PH does not mark this request approved or completed.",
            "Open Application tracking to follow status changes. Only authorized personnel can update the status after you submit.",
        ],
        "submit_event": (
            "Certificate of residency request saved for assistance and tracking. "
            "The local government has not reviewed it, and OneGov PH has not marked it approved or completed."
        ),
        "submit_notice": (
            "Your Certificate of Residency request {reference} was submitted in OneGov PH. "
            "It is not an official filing. The barangay or city government remains responsible for verifying residency and issuing the certificate."
        ),
        "status_labels": {
            "submitted": "Submitted",
            "pending_documents": "Additional documents required",
            "ready_for_release": "Ready for pickup",
        },
    }


SENIOR_DISCLAIMER = (
    "OneGov PH keeps this request for assistance and tracking. "
    "It is not sent to the agency as an official filing. "
    "The local government and OSCA remain responsible for verifying eligibility, processing applications, and issuing official Senior Citizen IDs."
)
SENIOR_FEE_NOTE = (
    "No processing fee is listed for standard new Senior Citizen ID issuance. "
    "Please confirm the applicable requirements and fees with your local OSCA office."
)
_CITIZENSHIP = ("Filipino Citizen", "Dual Citizen")

# Add a record only after that OSCA office confirms its requirements, fee, and contact details.
# Keys are "city|barangay" in lowercase, with extra spaces removed.
VERIFIED_OSCA_OFFICES = {}


def senior_profile(values):
    """Return verified OSCA rules, or a starting list when none are on file."""
    key = _place_key(values.get("city"), values.get("barangay"))
    verified = VERIFIED_OSCA_OFFICES.get(key) if key else None
    if verified:
        return {"verified": True, **verified}
    return {
        "verified": False,
        "require_sex": False,
        "require_civil_status": False,
        "citizenship_options": _CITIZENSHIP,
        "documents": {},
        "fee_amount": None,
        "address": None,
        "contact_number": None,
        "office_hours": None,
        "instructions": None,
    }


def _senior_document(profile, key, label, help_text, default_required=False, required_when=None):
    configured = (profile.get("documents") or {}).get(key)
    required = default_required if configured is None else bool(configured)
    return _document(
        key,
        label,
        help_text,
        required=required,
        required_when=None if required else required_when,
    )


def compose_senior_citizen_id(values=None):
    """Senior Citizen ID rules. Other LGU services keep their own forms."""
    answers = values or {}
    profile = senior_profile(answers)
    city = " ".join(str(answers.get("city") or "").split())
    barangay = " ".join(str(answers.get("barangay") or "").split())
    citizenship_options = tuple(profile.get("citizenship_options") or _CITIZENSHIP)
    personal = "Personal information"
    residential = "Residential information"
    contact = "Contact information"
    emergency = "Emergency contact"
    request_type = "Request type"
    fields = [
        _field("first_name", "First name", "Enter your first name as it appears on your identification.", section=personal),
        _field(
            "middle_name",
            "Middle name",
            "Leave this blank if you have no middle name.",
            required=False,
            section=personal,
        ),
        _field("last_name", "Last name", "Enter your last name as it appears on your identification.", section=personal),
        _field(
            "date_of_birth",
            "Date of birth",
            "You must be 60 years old or older. A future date is not accepted.",
            field_type="date",
            section=personal,
            min_age=60,
        ),
        _field(
            "age",
            "Age",
            "This is calculated from your date of birth. You can continue when the age is 60 or older.",
            field_type="computed",
            required=False,
            source="date_of_birth",
            calc="age",
            empty="Enter your date of birth.",
            section=personal,
        ),
        _field(
            "sex",
            "Sex",
            "This OSCA office asks for the sex recorded on your identification."
            if profile["require_sex"]
            else "Select this only if your OSCA office asks for it.",
            field_type="select",
            required=profile["require_sex"],
            options=_SEX,
            section=personal,
        ),
        _field(
            "civil_status",
            "Civil status",
            "This OSCA office asks for your civil status."
            if profile["require_civil_status"]
            else "Select this only if your OSCA office asks for it.",
            field_type="select",
            required=profile["require_civil_status"],
            options=_CIVIL_STATUS,
            section=personal,
        ),
        _field(
            "citizenship_status",
            "Citizenship status",
            "Choose Filipino Citizen or Dual Citizen. Confirm any extra citizenship rule with your OSCA office.",
            field_type="select",
            options=citizenship_options,
            section=personal,
        ),
        _field(
            "address",
            "Complete address",
            "Enter the house or building, street, and subdivision where you live now.",
            field_type="textarea",
            max_length=500,
            section=residential,
        ),
        _field("barangay", "Barangay", "Enter the barangay of your current address.", section=residential),
        _field(
            "city",
            "City or municipality",
            "Enter the city or municipality of the OSCA office for this address.",
            section=residential,
        ),
        _field("province", "Province", "Enter the province of your current address.", section=residential),
        _field(
            "contact_number",
            "Contact number",
            "Enter a mobile or telephone number OSCA can use. Include the area code for a landline.",
            field_type="tel",
            max_length=20,
            section=contact,
        ),
        _field(
            "email",
            "Email address",
            "Enter an email address you can open. Status messages are also shown in OneGov PH.",
            field_type="email",
            max_length=255,
            section=contact,
        ),
        _field(
            "emergency_contact_name",
            "Contact name",
            "Optional. Enter a relative or friend OSCA can call. Leave this blank if you do not want to add one.",
            required=False,
            section=emergency,
        ),
        _field(
            "emergency_relationship",
            "Relationship",
            "Optional. Example: spouse, child, or sibling.",
            required=False,
            max_length=80,
            section=emergency,
        ),
        _field(
            "emergency_contact_number",
            "Contact number",
            "Optional. Enter a mobile or telephone number for that emergency contact.",
            field_type="tel",
            required=False,
            max_length=20,
            section=emergency,
        ),
        _field(
            "representative",
            "Applying through a representative",
            "Choose Yes only if another person will submit or claim this request for you.",
            field_type="select",
            options=("No", "Yes"),
            section=request_type,
        ),
        _field(
            "id_transfer",
            "Transfer of an existing Senior Citizen ID",
            "Choose Yes if you are transferring an ID you already have. Choose No for a new ID.",
            field_type="select",
            options=("No", "Yes"),
            section=request_type,
        ),
    ]
    documents = (
        _senior_document(
            profile,
            "valid_id",
            "Valid government-issued ID",
            "Upload a clear PDF or photo of one government ID. The name should match this application.",
            default_required=True,
        ),
        _senior_document(
            profile,
            "age_proof",
            "Proof of age",
            "Upload a PSA birth certificate or another proof of age your OSCA office accepts.",
            default_required=True,
        ),
        _senior_document(
            profile,
            "residency_proof",
            "Proof of residency",
            "Upload a barangay certification or another proof of residency your OSCA office accepts.",
            default_required=True,
        ),
        _senior_document(
            profile,
            "photo",
            "Recent ID photo",
            "Upload a recent photo of your face. Ask your OSCA office whether it should be 1x1 or 2x2. OneGov PH does not measure the photo.",
            default_required=True,
        ),
        _senior_document(
            profile,
            "dual_citizenship",
            "Dual citizenship certificate",
            "Required when you choose Dual Citizen. Upload the certificate or recognition of dual citizenship.",
            required_when=("citizenship_status", "Dual Citizen"),
        ),
        _senior_document(
            profile,
            "marriage_certificate",
            "Marriage certificate",
            "Upload this only if your OSCA office asks for it.",
        ),
        _senior_document(
            profile,
            "voters_certification",
            "Voter's certification",
            "Upload this only if your OSCA office asks for it.",
        ),
        _senior_document(
            profile,
            "authorization",
            "Authorization letter",
            "Required when a representative will submit or claim this request. Upload a signed authorization letter.",
            required_when=("representative", "Yes"),
        ),
        _senior_document(
            profile,
            "representative_id",
            "Representative's government-issued ID",
            "Required with the authorization letter. Upload a clear PDF or photo of the representative's government ID.",
            required_when=("representative", "Yes"),
        ),
        _senior_document(
            profile,
            "previous_senior_id",
            "Previous Senior Citizen ID",
            "Required when this is a transfer. Upload a copy of the Senior Citizen ID issued by the previous office.",
            required_when=("id_transfer", "Yes"),
        ),
    )
    if profile["verified"] and barangay and city:
        document_note = (
            f"This checklist follows the verified OSCA requirements on file for {barangay}, {city}. "
            "Another city or OSCA office can ask for different documents."
        )
    elif barangay and city:
        document_note = (
            f"OneGov PH does not have a verified OSCA requirement list for {barangay}, {city}. "
            "The checklist below is a starting list. Confirm the citizenship, residency, and document rules with that OSCA office."
        )
    else:
        document_note = (
            "Document requirements depend on the OSCA office for your city or barangay. "
            "This starting list can change when a verified requirement list is on file."
        )
    fee_amount = profile.get("fee_amount")
    if profile["verified"] and fee_amount is not None:
        fee_note = (
            f"Recorded OSCA fee: ₱{fee_amount}. "
            "Please confirm the applicable requirements and fees with your local OSCA office. "
            "OneGov PH does not collect this payment."
        )
    else:
        fee_note = SENIOR_FEE_NOTE
    office = {
        "heading": "OSCA office",
        "address_label": "Office address",
        "instructions_heading": "Instructions from OSCA",
        "barangay": barangay,
        "city": city,
        "note": ""
        if profile["verified"]
        else "OneGov PH does not have a verified OSCA office address, contact number, or office hours for this barangay or city. Confirm those details with the OSCA office before you visit.",
    }
    for source_key, office_key in (
        ("address", "address"),
        ("contact_number", "contact_number"),
        ("office_hours", "office_hours"),
        ("instructions", "instructions"),
    ):
        if profile["verified"] and profile.get(source_key):
            office[office_key] = profile[source_key]
    return {
        "kind": "senior",
        "process": "Prepare a Senior Citizen ID request for the OSCA office that covers your address. You must be 60 or older. That office still verifies eligibility and issues the ID.",
        "fields": fields,
        "documents": documents,
        "document_note": document_note,
        "fee_note": fee_note,
        "catalog_fee": SENIOR_FEE_NOTE,
        "disclaimer": SENIOR_DISCLAIMER,
        "local_office": office,
        "show_submitted_details": True,
        "reminders": [
            "You must be 60 years old or older on the day you submit this request.",
            "Confirm the citizenship and residency requirements with your OSCA office. OneGov PH does not apply a local residency rule unless a verified OSCA requirement is on file.",
        ],
        "terms": "I confirm that the information and documents in this request are accurate. " + SENIOR_DISCLAIMER,
        "next_steps": [
            "Keep your reference number and use it when you ask the OSCA office about this request.",
            "Confirm the requirements and any fee with your OSCA office. OneGov PH does not collect a payment.",
            "The local government and OSCA verify eligibility and issue the Senior Citizen ID. OneGov PH does not mark this request approved or completed.",
            "Open Application tracking to follow status changes and any instructions recorded from OSCA. Only authorized personnel can update the status after you submit.",
        ],
        "submit_event": (
            "Senior Citizen ID request saved for assistance and tracking. "
            "OSCA has not reviewed it, and OneGov PH has not marked it approved or completed."
        ),
        "submit_notice": (
            "Your Senior Citizen ID request {reference} was submitted in OneGov PH. "
            "It is not an official filing. The local government and OSCA remain responsible for verifying eligibility and issuing the ID."
        ),
        "status_labels": {
            "submitted": "Submitted",
            "pending_documents": "Additional documents required",
            "ready_for_release": "Ready for pickup",
        },
    }


NBI_DISCLAIMER = (
    "OneGov PH keeps this request for assistance and tracking. "
    "It is not sent to the agency as an official filing. "
    "OneGov PH only prepares and monitors NBI clearance requests. "
    "Official registration, appointment scheduling, payment, biometric capture, verification, and clearance issuance remain under the National Bureau of Investigation."
)
NBI_FEE_NOTE = (
    "Listed Clearance Fee: ₱130.00. Additional electronic payment service charges may apply. "
    "Payment must be completed through official NBI payment channels. OneGov PH does not collect this payment."
)
_EDUCATION = ("Elementary", "High school", "Senior high school", "Vocational", "College", "Postgraduate")
_EMPLOYMENT = ("Employed", "Self-employed", "Unemployed", "Student", "Retired", "Overseas worker")
_RECORDED_PAYMENT = ("Not yet paid", "Paid through an official NBI channel", "Not sure")

# Add a record only after an NBI requirement is confirmed. This does not connect to NBI.
VERIFIED_NBI_REQUIREMENTS = {}


def nbi_profile():
    """Return confirmed NBI field rules, or the starting form when none are on file."""
    verified = VERIFIED_NBI_REQUIREMENTS.get("nbi")
    defaults = {
        "verified": False,
        "require_nationality": False,
        "require_sex": True,
        "require_civil_status": True,
        "require_father": True,
        "require_mother": True,
        "require_educational_attainment": True,
        "require_occupation": True,
        "require_employment_status": True,
        "education_options": _EDUCATION,
        "employment_options": _EMPLOYMENT,
        "documents": {},
        "instructions": None,
    }
    if not verified:
        return defaults
    merged = {**defaults, **verified, "verified": True}
    merged["documents"] = {**defaults["documents"], **(verified.get("documents") or {})}
    return merged


def _nbi_document(profile, key, label, help_text):
    required = bool((profile.get("documents") or {}).get(key))
    return _document(key, label, help_text, required=required)


def compose_nbi_clearance(values=None):
    """NBI clearance monitoring form. Other services keep their own questions."""
    profile = nbi_profile()
    applicant = "Applicant information"
    father = "Father"
    mother = "Mother"
    background = "Education and employment"
    appointment = "Existing NBI appointment"
    fields = [
        _field("first_name", "First name", "Enter your first name as it appears on your identification.", section=applicant),
        _field(
            "middle_name",
            "Middle name",
            "Leave this blank if you have no middle name.",
            required=False,
            section=applicant,
        ),
        _field("last_name", "Last name", "Enter your last name as it appears on your identification.", section=applicant),
        _field(
            "date_of_birth",
            "Date of birth",
            "Use the date of birth on your birth record. A future date is not accepted.",
            field_type="date",
            section=applicant,
        ),
        _field(
            "sex",
            "Sex",
            "Select the sex recorded on your identification.",
            field_type="select",
            required=profile["require_sex"],
            options=_SEX,
            section=applicant,
        ),
        _field(
            "civil_status",
            "Civil status",
            "Select your civil status today.",
            field_type="select",
            required=profile["require_civil_status"],
            options=_CIVIL_STATUS,
            section=applicant,
        ),
        _field(
            "address",
            "Complete address",
            "Include the house number, street, barangay, city or municipality, and province.",
            field_type="textarea",
            max_length=500,
            section=applicant,
        ),
        _field(
            "contact_number",
            "Contact number",
            "Enter a mobile or telephone number where you can be reached.",
            field_type="tel",
            max_length=20,
            section=applicant,
        ),
        _field(
            "email",
            "Email address",
            "Enter an email address you can open. Status messages are also shown in OneGov PH.",
            field_type="email",
            max_length=255,
            section=applicant,
        ),
        _field("place_of_birth", "Place of birth", "Enter the city or municipality and province of birth.", section=applicant),
        _field(
            "purpose",
            "Purpose of clearance",
            "Example: local employment, travel, or a business requirement. Confirm the purpose choices with NBI when you register.",
            field_type="textarea",
            max_length=400,
            section=applicant,
        ),
        _field(
            "previous_name",
            "Other names used",
            "Enter a maiden name or another name you have used. Leave this blank if none.",
            required=False,
            max_length=200,
            section=applicant,
        ),
    ]
    if profile["require_nationality"]:
        fields.append(
            _field(
                "nationality",
                "Nationality",
                "Enter your nationality. A confirmed NBI requirement asks for this.",
                section=applicant,
            )
        )
    fields.extend(
        [
            _field(
                "father_first_name",
                "First name",
                "Enter your father's first name.",
                required=profile["require_father"],
                section=father,
            ),
            _field(
                "father_middle_name",
                "Middle name",
                "Leave this blank if your father has no middle name.",
                required=False,
                section=father,
            ),
            _field(
                "father_last_name",
                "Last name",
                "Enter your father's last name.",
                required=profile["require_father"],
                section=father,
            ),
            _field(
                "mother_first_name",
                "First name",
                "Enter your mother's first name.",
                required=profile["require_mother"],
                section=mother,
            ),
            _field(
                "mother_middle_name",
                "Middle name",
                "Leave this blank if your mother has no middle name.",
                required=False,
                section=mother,
            ),
            _field(
                "mother_maiden_last_name",
                "Maiden last name",
                "Enter your mother's last name before marriage.",
                required=profile["require_mother"],
                section=mother,
            ),
            _field(
                "educational_attainment",
                "Educational attainment",
                "Select the highest level you completed. Confirm the wording NBI asks for when you register.",
                field_type="select",
                required=profile["require_educational_attainment"],
                options=tuple(profile.get("education_options") or _EDUCATION),
                section=background,
            ),
            _field(
                "occupation",
                "Occupation",
                "Enter your current occupation. Leave this blank only when a confirmed NBI rule says it is not required.",
                required=profile["require_occupation"],
                section=background,
            ),
            _field(
                "employment_status",
                "Employment status",
                "Select the status that applies to you today. Confirm this with NBI when you register.",
                field_type="select",
                required=profile["require_employment_status"],
                options=tuple(profile.get("employment_options") or _EMPLOYMENT),
                section=background,
            ),
            _field(
                "employer_name",
                "Employer name",
                "Optional. Enter your employer only if you have one and want it on this request.",
                required=False,
                section=background,
            ),
            _field(
                "preferred_branch",
                "Preferred NBI branch",
                "Optional. Enter a branch only if you already chose one or NBI already assigned one. OneGov PH does not assign a branch.",
                required=False,
                section=appointment,
            ),
            _field(
                "appointment_date",
                "Appointment date",
                "Optional. Enter the appointment date NBI already gave you. OneGov PH does not schedule an appointment.",
                field_type="date",
                required=False,
                allow_future=True,
                section=appointment,
            ),
            _field(
                "appointment_time",
                "Appointment time",
                "Optional. Enter the appointment time NBI already gave you.",
                field_type="time",
                required=False,
                section=appointment,
            ),
            _field(
                "nbi_reference",
                "NBI reference number",
                "Optional. Enter the reference number NBI already gave you. OneGov PH does not create an NBI reference number.",
                required=False,
                max_length=40,
                section=appointment,
            ),
            _field(
                "recorded_payment_status",
                "Recorded payment status",
                "Optional. Record a payment only if you already made it through an official NBI channel. OneGov PH does not collect or confirm it.",
                field_type="select",
                required=False,
                options=_RECORDED_PAYMENT,
                section=appointment,
            ),
        ]
    )
    documents = (
        _nbi_document(
            profile,
            "valid_id_primary",
            "First valid government-issued ID",
            "Optional unless a confirmed NBI requirement asks for the file. Upload a clear PDF or photo of one government ID.",
        ),
        _nbi_document(
            profile,
            "valid_id_secondary",
            "Second valid government-issued ID",
            "Optional unless a confirmed NBI requirement asks for the file. Upload a second government ID if you want it kept with this request.",
        ),
        _nbi_document(
            profile,
            "transaction_reference",
            "NBI transaction reference",
            "Optional. Upload this only if NBI already registered your transaction and gave you a reference.",
        ),
        _nbi_document(
            profile,
            "payment_confirmation",
            "Payment confirmation",
            "Optional. Upload this only if you already paid through an official NBI channel. OneGov PH does not confirm the payment.",
        ),
    )
    if profile["verified"] and (profile.get("documents") or {}).get("photo"):
        documents = documents + (
            _nbi_document(
                profile,
                "photo",
                "Recent photo",
                "A confirmed requirement asks for this file. NBI still captures the photograph and biometrics at the branch.",
            ),
        )
    if profile["verified"]:
        document_note = (
            "This checklist follows the confirmed NBI requirements on file. "
            "Uploads stay optional unless one of those requirements says a file is required. "
            "NBI captures the photograph and biometrics at the branch for an ordinary local application."
        )
    else:
        document_note = (
            "These uploads are optional. OneGov PH does not have a confirmed NBI file requirement that makes them mandatory. "
            "NBI captures the photograph and biometrics at the branch, so this form does not ask for a recent photo on an ordinary local application."
        )
    office = {
        "heading": "National Bureau of Investigation",
        "note": (
            "OneGov PH does not assign an NBI branch, appointment, or reference number, and it has no live connection to NBI. "
            "Confirm the branch and the current requirements through NBI."
        ),
    }
    if profile["verified"] and profile.get("instructions"):
        office["instructions"] = profile["instructions"]
        office["instructions_heading"] = "Instructions"
    return {
        "kind": "nbi",
        "process": (
            "Prepare and monitor an NBI clearance request in OneGov PH. "
            "NBI still handles registration, the appointment, payment, biometrics, verification, and issuance of the clearance."
        ),
        "fields": fields,
        "documents": documents,
        "document_note": document_note,
        "fee_note": NBI_FEE_NOTE,
        "catalog_fee": NBI_FEE_NOTE,
        "disclaimer": NBI_DISCLAIMER,
        "reference_label": "OneGov PH reference number",
        "local_office": office,
        "show_submitted_details": True,
        "reminders": [
            "OneGov PH does not register this request with NBI.",
            "Record a branch, appointment, NBI reference number, or payment only when NBI has already given it to you.",
            "NBI takes the photograph and biometrics at the branch for an ordinary local application.",
            "After you submit, only authorized personnel can change the monitoring status. Those statuses are notes in OneGov PH, not a live update from NBI.",
        ],
        "terms": "I confirm that the information and documents in this request are accurate. " + NBI_DISCLAIMER,
        "next_steps": [
            "Keep your OneGov PH reference number. It is separate from any reference number NBI gives you.",
            "Register, schedule, pay, and give biometrics through NBI. OneGov PH does not do those steps and does not collect the ₱130.00 clearance fee.",
            "If NBI already gave you an appointment or reference number, you can save it on this request. OneGov PH does not check it with NBI.",
            "Open Application tracking to follow monitoring updates such as Submitted, Under review, Appointment scheduled, Payment pending, Payment completed, For biometrics, With hit, Ready for release, Completed, Rejected, or Cancelled.",
        ],
        "submit_event": (
            "NBI clearance request saved for assistance and monitoring. "
            "NBI has not received this as an official filing, and OneGov PH has not marked it approved or completed."
        ),
        "submit_notice": (
            "Your NBI clearance request {reference} was submitted in OneGov PH for monitoring. "
            "It is not an official NBI registration. Appointment, payment, biometrics, verification, and clearance issuance remain with NBI."
        ),
        "status_labels": {
            "submitted": "Submitted",
            "under_review": "Under review",
            "scheduled": "Appointment scheduled",
            "for_payment": "Payment pending",
            "paid": "Payment completed",
            "for_biometrics": "For biometrics",
            "with_hit": "With hit",
            "ready_for_release": "Ready for release",
        },
    }


CENOMAR_DISCLAIMER = (
    "OneGov PH assists citizens in preparing and monitoring their CENOMAR requests. "
    "Official issuance, verification, and processing are handled by the Philippine Statistics Authority."
)
CENOMAR_FEE_NOTE = (
    "The Philippine Statistics Authority charges the official CENOMAR fee. "
    "Confirm the current amount and pay through an authorized PSA channel, such as PSA Serbilis. "
    "OneGov PH does not collect this payment."
)
CENOMAR_URL = "https://www.psaserbilis.com.ph/"
_CENOMAR_PURPOSE = ("Marriage", "Employment", "Legal Purposes", "Immigration", "Personal Records", "Other")
_CENOMAR_REQUESTER = ("Self", "Child", "Parent", "Spouse")
_CENOMAR_DELIVERY = ("Door-to-door delivery", "Pick up at a collection location")
CENOMAR_PAYMENT_OPTIONS = ("Not yet paid", "Paid through an official PSA channel", "Not sure")
CENOMAR_RECORDED_STATUSES = (
    "Official application recorded",
    "Waiting for payment",
    "Payment confirmed",
    "Processing at PSA",
    "Processed",
    "Dispatched",
    "Out for delivery",
    "Delivered",
    "Rejected / needs attention",
)
CENOMAR_TRACKING_FIELDS = (
    "psa_reference",
    "psa_application_date",
    "psa_payment_status",
    "psa_payment_date",
    "psa_expected_delivery",
    "psa_recorded_status",
)


def cenomar_incomplete_step(values):
    """Return the first CENOMAR step that is still missing a required answer."""
    answers = values or {}
    required = {
        1: ("first_name", "last_name", "date_of_birth", "sex", "civil_status", "place_of_birth"),
        2: ("father_name", "mother_maiden_name", "copies", "purpose"),
        3: (
            "requester_relationship",
            "requester_name",
            "contact_number",
            "email",
            "delivery_method",
            "delivery_address",
            "house_number",
            "street",
            "barangay",
            "city",
            "province",
            "postal_code",
        ),
    }
    for step, keys in required.items():
        for key in keys:
            if not str(answers.get(key) or "").strip():
                return step
    if answers.get("purpose") == "Other" and not str(answers.get("purpose_other") or "").strip():
        return 2
    return None


def compose_cenomar(values=None):
    """CENOMAR preparation and monitoring. PSA Serbilis still takes the official application."""
    applicant = "Applicant information"
    family = "Family information"
    request = "Request details"
    party = "Requesting party"
    delivery = "Delivery information"
    fields = [
        _field("first_name", "First name", "Enter the first name of the person named on the CENOMAR.", section=applicant, step=1),
        _field("middle_name", "Middle name", "Leave this blank if that person has no middle name.", required=False, section=applicant, step=1),
        _field("last_name", "Last name", "Enter the last name of the person named on the CENOMAR.", section=applicant, step=1),
        _field(
            "date_of_birth",
            "Date of birth",
            "Use the date of birth on the birth record. A future date is not accepted.",
            field_type="date",
            section=applicant,
            step=1,
        ),
        _field("sex", "Sex", "Select the sex recorded for the person named on the CENOMAR.", field_type="select", options=_SEX, section=applicant, step=1),
        _field(
            "civil_status",
            "Civil status",
            "Select the civil status of the person named on the CENOMAR.",
            field_type="select",
            options=_CIVIL_STATUS,
            section=applicant,
            step=1,
        ),
        _field(
            "place_of_birth",
            "Place of birth",
            "Enter the city or municipality and province of birth.",
            section=applicant,
            step=1,
        ),
        _field(
            "father_name",
            "Father's complete name",
            "Enter the father's first, middle, and last name.",
            max_length=160,
            section=family,
            step=2,
        ),
        _field(
            "mother_maiden_name",
            "Mother's complete maiden name",
            "Enter the mother's first, middle, and maiden last name.",
            max_length=160,
            section=family,
            step=2,
        ),
        _field(
            "copies",
            "Number of copies",
            "Enter how many copies you plan to order, from 1 to 5. Confirm the current limit on the official PSA channel.",
            field_type="number",
            max_length=1,
            default="1",
            section=request,
            step=2,
        ),
        _field(
            "purpose",
            "Purpose of request",
            "Select why the certificate is being requested.",
            field_type="select",
            options=_CENOMAR_PURPOSE,
            section=request,
            step=2,
        ),
        _field(
            "purpose_other",
            "Other purpose",
            "Describe the purpose. This is shown only when you select Other.",
            required=False,
            max_length=200,
            section=request,
            step=2,
            show_when=("purpose", "Other"),
            required_when_shown=True,
        ),
        _field(
            "requester_relationship",
            "Who is requesting the certificate",
            "PSA generally accepts a request from the person named on the CENOMAR, or from that person's child, parent, or spouse. PSA still decides whether the requester is eligible.",
            field_type="select",
            options=_CENOMAR_REQUESTER,
            section=party,
            step=3,
        ),
        _field(
            "requester_name",
            "Requesting party's complete name",
            "Enter the full name of the person who will request the certificate on the official PSA channel.",
            max_length=160,
            section=party,
            step=3,
        ),
        _field(
            "contact_number",
            "Contact number",
            "Enter a mobile or telephone number for the requesting party.",
            field_type="tel",
            max_length=20,
            section=party,
            step=3,
        ),
        _field(
            "email",
            "Email address",
            "Enter an email address the requesting party can open.",
            field_type="email",
            max_length=255,
            section=party,
            step=3,
        ),
        _field(
            "delivery_method",
            "Delivery option",
            "Choose door-to-door delivery, or pickup only if the official PSA channel offers a collection location. OneGov PH does not assign a pickup site.",
            field_type="select",
            options=_CENOMAR_DELIVERY,
            section=delivery,
            step=3,
        ),
        _field(
            "delivery_address",
            "Complete delivery address",
            "Enter the full address for door-to-door delivery. For pickup, enter the address you will use while the collection location is chosen on the official channel.",
            field_type="textarea",
            max_length=500,
            section=delivery,
            step=3,
        ),
        _field("house_number", "House number / building", "Enter the house number, unit, or building name.", max_length=80, section=delivery, step=3),
        _field("street", "Street", "Enter the street name.", max_length=120, section=delivery, step=3),
        _field("barangay", "Barangay", "Enter the barangay.", section=delivery, step=3),
        _field("city", "City / municipality", "Enter the city or municipality.", section=delivery, step=3),
        _field("province", "Province", "Enter the province. For Metro Manila, you may enter Metro Manila.", section=delivery, step=3),
        _field(
            "postal_code",
            "Postal code",
            "Enter the 4-digit postal code.",
            max_length=4,
            section=delivery,
            step=3,
        ),
    ]
    return {
        "kind": "cenomar",
        "service_title": "Certificate of No Marriage Record (CENOMAR)",
        "process": (
            "A CENOMAR is an official certification issued by the Philippine Statistics Authority confirming that "
            "no marriage record has been found under the specified person’s name in the PSA civil registry."
        ),
        "department_label": "Philippine Statistics Authority (PSA)",
        "fields": fields,
        "documents": (),
        "fee_note": CENOMAR_FEE_NOTE,
        "catalog_fee": CENOMAR_FEE_NOTE,
        "disclaimer": CENOMAR_DISCLAIMER,
        "official_url": CENOMAR_URL,
        "psa_payment_options": CENOMAR_PAYMENT_OPTIONS,
        "psa_recorded_statuses": CENOMAR_RECORDED_STATUSES,
        "reference_label": "OneGov PH reference number",
        "show_submitted_details": True,
        "step_labels": (
            "1. Applicant information",
            "2. Family and request",
            "3. Requesting party and delivery",
            "4. Review and confirmation",
        ),
        "reminders": [
            "An official PSA application is completed on PSA Serbilis. This OneGov PH form does not submit the application to PSA.",
            "The person named on the certificate, or that person's child, parent, or spouse, can prepare a request. PSA decides who is eligible.",
            "If PSA asks for an authorization letter, a guardian, or a court order, complete that on the official channel. OneGov PH does not collect those papers.",
            "OneGov PH does not collect the PSA fee and does not create a PSA reference number.",
        ],
        "terms": "I confirm that the information in this request is accurate. " + CENOMAR_DISCLAIMER,
        "next_steps": [
            "Open PSA Serbilis and complete the official CENOMAR application and payment there.",
            "Keep your OneGov PH reference number. It is not a PSA reference number.",
            "When PSA gives you a 16-digit reference number, record it on this request. OneGov PH does not receive that number from PSA.",
            "Update the PSA status only with what the official channel shows. OneGov PH does not mark the certificate issued.",
        ],
        "submit_event": (
            "CENOMAR request saved for assistance and monitoring. "
            "This is not an official PSA application, and OneGov PH has not sent it to PSA."
        ),
        "submit_notice": (
            "Your CENOMAR preparation {reference} was saved in OneGov PH. "
            "It is not an official PSA application. Complete the request and payment on PSA Serbilis, then record the 16-digit PSA reference here."
        ),
        "status_labels": {
            "draft": "Draft",
            "submitted": "Awaiting official PSA application",
            "under_review": "Official application recorded",
            "rejected": "Rejected / needs attention",
        },
    }


SSS_PATH_NEW = "First-time SS Number registration"
SSS_PATH_EXISTING = "Existing SS Number concern"
SSS_HAS_NO = "No, I am registering for the first time."
SSS_HAS_YES = "Yes, I already have an SSS Number."
SSS_URL = "https://www.sss.gov.ph/become-an-sss-member"
SSS_SITE = "https://www.sss.gov.ph/"
SSS_NOTICE = (
    "Official SS Number registration and issuance are performed through the SSS online registration system. "
    "OneGov PH does not directly generate or issue SS Numbers."
)
SSS_DESCRIPTION = (
    "OneGov PH helps a first-time applicant prepare an SS Number registration, and helps a citizen who already has an SS Number organize a concern. "
    "SSS issues the number and handles the official record. OneGov PH does not generate or assign an SS Number."
)
SSS_FEE_NOTE = (
    "SS Number registration has no SSS processing fee. "
    "OneGov PH does not collect a payment and does not issue an SS Number."
)
SSS_PURPOSES = (
    "Employment",
    "Self-Employment",
    "Overseas Filipino Worker (OFW)",
    "Non-Working Spouse",
)
SSS_CATEGORIES = {
    "Employment": "Employed",
    "Self-Employment": "Self-employed",
    "Overseas Filipino Worker (OFW)": "Overseas Filipino Worker",
    "Non-Working Spouse": "Non-working spouse",
}
SSS_BENEFICIARY_RELATIONSHIPS = ("Father", "Mother", "Spouse", "Child", "Other eligible beneficiary")
SSS_CONCERNS = (
    "SS Number Verification Assistance",
    "Lost or Forgotten SS Number",
    "UMID / SSS ID Concern",
    "Personal Information Correction",
    "Membership Record Concern",
    "Other SSS Concerns",
)
SSS_CONCERN_GUIDANCE = {
    "SS Number Verification Assistance": {
        "url": SSS_SITE,
        "action": "Open the official SSS website",
        "text": "SSS verifies a previously issued SS Number at an SSS office. Do not start a new registration, and do not apply for a second number.",
        "next": "Ask SSS to verify the SS Number you already have. OneGov PH cannot look it up or issue another one.",
    },
    "Lost or Forgotten SS Number": {
        "url": SSS_SITE,
        "action": "Open the official SSS website",
        "text": "An SS Number is a lifetime number. If you cannot remember it, request verification at the nearest SSS office. Do not apply for another SS Number.",
        "next": "Request verification of your existing number at an SSS office. Do not open a first-time registration.",
    },
    "UMID / SSS ID Concern": {
        "url": SSS_SITE,
        "action": "Open the official SSS website",
        "text": "UMID and SSS ID concerns are handled by SSS. OneGov PH does not issue an ID or a new SS Number.",
        "next": "Continue the UMID or SSS ID concern through SSS. This record does not apply for a new SS Number.",
    },
    "Personal Information Correction": {
        "url": "https://www.sss.gov.ph/wp-content/uploads/2024/10/E4-Member-Data-Change-Request.pdf",
        "action": "Open SSS Form E-4",
        "text": "SSS uses Member Data Change Request (SS Form E-4) for a membership data correction. Simple corrections can also be filed in My.SSS. OneGov PH does not change the membership record.",
        "next": "Complete SS Form E-4, or the simple-correction request in My.SSS, and submit it to SSS with the documents SSS requires.",
    },
    "Membership Record Concern": {
        "url": SSS_SITE,
        "action": "Open the official SSS website",
        "text": "Membership records are viewed and updated through My.SSS or an SSS office. OneGov PH does not change the SSS record.",
        "next": "Sign in to My.SSS or visit an SSS office for the membership record. OneGov PH does not update it.",
    },
    "Other SSS Concerns": {
        "url": SSS_SITE,
        "action": "Open the official SSS website",
        "text": "Continue this concern on the official SSS website or at an SSS office. OneGov PH does not submit it to SSS and does not issue an SS Number.",
        "next": "Use the official SSS channel for this concern. OneGov PH only keeps your notes.",
    },
}
SSS_RECORDED_STATUSES = (
    "Awaiting SS Number issuance",
    "SS Number issued",
    "Supporting documents pending",
    "Supporting documents submitted",
    "Completed",
    "Needs attention",
)
SSS_DOCUMENT_STATUSES = (
    "Not yet submitted on the official SSS channel",
    "Submitted on the official SSS channel",
    "Not sure",
)
SSS_PRIVATE_KEYS = (
    "documents_seen",
    "ss_number",
    "sss_transaction_number",
    "sss_registration_date",
    "sss_recorded_status",
    "sss_issue_date",
    "sss_document_status",
    "sss_path",
)
SSS_MAX_BYTES = 3 * 1024 * 1024
SSS_FILE_RULES = {
    "extensions": {".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff", ".pdf": b"%PDF"},
    "max_bytes": SSS_MAX_BYTES,
    "type_error": "Upload a JPEG, JPG, or PDF file.",
    "size_error": "The file is larger than the 3 MB limit used by the SSS online application.",
}
SSS_DOCUMENT_EXAMPLES = (
    "PSA birth certificate. SSS prefers this document.",
    "If you do not have a birth certificate: a baptismal certificate, or one government ID such as a driver's license, passport, PhilSys ID or ePhilID, PRC card, SSS digitized ID, seaman's book, or UMID.",
    "If you have none of those, SSS may ask for two other documents. Use the list on the official SSS website.",
    "A non-working spouse should also be ready to show the marriage record and the member spouse's existing SS Number.",
)


def parse_beneficiaries(value):
    """Return beneficiary rows stored as JSON. Invalid text becomes an empty list."""
    import json

    if not value or not str(value).strip():
        return []
    try:
        data = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    people = []
    for item in data:
        if not isinstance(item, dict):
            continue
        people.append(
            {
                "name": item.get("name") or "",
                "relationship": item.get("relationship") or "",
                "birth_date": item.get("birth_date") or "",
                "note": item.get("note") or "",
            }
        )
    return people


def _sss_choice(answers):
    """Return the Step 1 answer, including a saved request from an earlier draft."""
    choice = str(answers.get("has_ss_number") or "").strip()
    if choice in (SSS_HAS_NO, SSS_HAS_YES):
        return choice
    legacy = str(answers.get("sss_path") or "").strip()
    if legacy in (SSS_PATH_NEW, "new"):
        return SSS_HAS_NO
    if legacy in (SSS_PATH_EXISTING, "existing"):
        return SSS_HAS_YES
    return ""


def _existing_document_examples(concern):
    """Examples taken from the official SSS instructions for that concern."""
    if concern == "Personal Information Correction":
        return (
            "Birth certificate or passport, when SS Form E-4 asks for it.",
            "If you have neither, use the documents listed on the official E-4 form.",
            "A file saved here is for your preparation. Submit it to SSS yourself.",
        )
    if concern in {"SS Number Verification Assistance", "Lost or Forgotten SS Number"}:
        return (
            "A government-issued ID you will present when SSS verifies the existing number.",
            "A file saved here is not sent to SSS.",
        )
    if concern == "UMID / SSS ID Concern":
        return (
            "A government-issued ID you will present to SSS for this ID concern.",
            "A file saved here is not sent to SSS.",
        )
    return (
        "A document SSS asked you to bring for this concern, if you already have it.",
        "A file saved here is not submitted to SSS.",
    )


def _sss_common(choice, concern):
    existing = choice == SSS_HAS_YES
    guidance = SSS_CONCERN_GUIDANCE.get(concern) if existing else None
    if existing and guidance is None:
        guidance = {
            "url": SSS_SITE,
            "action": "Open the official SSS website",
            "text": "Continue this existing SS Number concern through SSS. OneGov PH does not issue a new number.",
            "next": "Use the official SSS channel. Do not apply for a second SS Number.",
        }
    return {
        "kind": "sss",
        "service_title": "SS Number Registration Assistance and Tracking",
        "department_label": "Social Security System (SSS)",
        "process": SSS_DESCRIPTION,
        "disclaimer": SSS_NOTICE,
        "fee_note": (
            "This request has no processing fee. OneGov PH does not collect a payment and does not issue an SS Number."
            if existing
            else SSS_FEE_NOTE
        ),
        "reference_label": "OneGov PH reference number",
        "private_keys": SSS_PRIVATE_KEYS,
        "official_url": guidance["url"] if guidance else (SSS_URL if choice == SSS_HAS_NO else ""),
        "official_heading": "Official SSS service" if existing else "Official SSS registration",
        "official_action": guidance["action"] if guidance else "Continue to Official SSS Registration",
        "official_text": (
            guidance["text"]
            if guidance
            else "Finish the registration on the SSS website. SSS verifies the registrant, checks the email address, validates the information, generates the SS Number, and receives the supporting document."
        ),
        "official_next": guidance["next"] if guidance else "",
        "status_labels": {
            "draft": "Draft",
            "submitted": "Existing SS Number concern recorded" if existing else "Awaiting official SSS registration",
            "under_review": "Official registration recorded",
        },
        "recorded_statuses": SSS_RECORDED_STATUSES,
        "document_statuses": SSS_DOCUMENT_STATUSES,
        "file_rules": SSS_FILE_RULES,
    }


def compose_sss(values=None):
    """One four-step SSS form. Yes keeps an existing number; No prepares a first registration."""
    answers = values or {}
    choice = _sss_choice(answers)
    concern = str(answers.get("concern_type") or "").strip()
    asked = ("has_ss_number",)
    new_member = ("has_ss_number", SSS_HAS_NO)
    existing_member = ("has_ss_number", SSS_HAS_YES)
    personal = "Personal information"
    contact = "Contact information"
    address = "Address"
    family = "Social status and place of birth"
    purpose = "Registration information"
    benefits = "Beneficiary information"
    member = "Existing SSS member"
    fields = [
        _field(
            "has_ss_number",
            "Do you already have an SSS Number?",
            "An SS Number is issued once. Choose Yes if SSS already issued one to you. That choice does not start a second registration.",
            field_type="select",
            options=(SSS_HAS_NO, SSS_HAS_YES),
            section="SS Number",
            placeholder="Select an answer",
        ),
        _field(
            "existing_ss_number",
            "Existing SS Number",
            "Enter the 10-digit SS Number SSS already issued. Dashes are optional. OneGov PH does not create or replace this number.",
            max_length=14,
            section=member,
            show_when=existing_member,
        ),
        _field(
            "concern_type",
            "Purpose of request",
            "Choose the SSS service you need. This does not apply for a second SS Number.",
            field_type="select",
            options=SSS_CONCERNS,
            section=member,
            show_when=existing_member,
        ),
        _field(
            "concern_details",
            "Description",
            "Describe the SSS concern. Do not enter a My.SSS password.",
            field_type="textarea",
            max_length=500,
            section=member,
            show_when=(existing_member, ("concern_type", "Other SSS Concerns")),
            required_when_shown=True,
        ),
        _field(
            "first_name",
            "First name",
            "Enter your first name. For a first-time registration, use the civil registry record.",
            section=personal,
            show_if_set=asked,
        ),
        _field("middle_name", "Middle name", "Leave this blank if there is no middle name.", required=False, section=personal, show_if_set=asked),
        _field("last_name", "Last name", "Enter your last name. For a first-time registration, use the civil registry record.", section=personal, show_if_set=asked),
        _field(
            "suffix",
            "Suffix",
            "Select a suffix only if it appears on the civil registry record.",
            field_type="select",
            required=False,
            options=("Jr.", "Sr.", "II", "III", "IV", "V"),
            section=personal,
            show_when=new_member,
        ),
        _field(
            "date_of_birth",
            "Date of birth",
            "Use your date of birth. A future date is not accepted.",
            field_type="date",
            section=personal,
            show_if_set=asked,
        ),
        _field("sex", "Sex", "Select the sex on the civil registry record.", field_type="select", options=_SEX, section=personal, show_when=new_member),
        _field(
            "civil_status",
            "Civil status",
            "Select your civil status. A non-working spouse registration requires Married.",
            field_type="select",
            options=_CIVIL_STATUS,
            section=personal,
            show_when=new_member,
        ),
        _field(
            "citizenship",
            "Citizenship",
            "Select the citizenship SSS should use for this registration.",
            field_type="select",
            options=("Filipino", "Dual Citizen", "Foreign National"),
            section=personal,
            show_when=new_member,
        ),
        _field(
            "nationality",
            "Nationality",
            "Enter your nationality. This is required for a foreign national.",
            required=False,
            section=personal,
            show_when=(new_member, ("citizenship", "Foreign National")),
            required_when_shown=True,
        ),
        _field(
            "mobile_number",
            "Mobile number",
            "Enter a Philippine mobile number, such as 09171234567.",
            field_type="tel",
            max_length=20,
            section=contact,
            show_if_set=asked,
        ),
        _field(
            "email",
            "Email address",
            "Enter an email address you can open. For a first-time registration, SSS sends its verification link to this address. OneGov PH does not send or confirm that email.",
            field_type="email",
            max_length=255,
            section=contact,
            show_if_set=asked,
        ),
        _field(
            "complete_address",
            "Complete address",
            "Enter the complete address SSS should use for this existing-member concern.",
            field_type="textarea",
            max_length=300,
            section=address,
            show_when=existing_member,
        ),
        _field("house_number", "House / lot number", "Enter the house, lot, unit, or building number.", max_length=80, section=address, show_when=new_member),
        _field("street", "Street", "Enter the street name.", max_length=120, section=address, show_when=new_member),
        _field("subdivision", "Subdivision", "Leave this blank if there is no subdivision.", required=False, max_length=120, section=address, show_when=new_member),
        _field("barangay", "Barangay", "Enter the barangay.", section=address, show_when=new_member),
        _field("city", "City / municipality", "Enter the city or municipality.", section=address, show_when=new_member),
        _field("province", "Province", "Enter the province. For Metro Manila, you may enter Metro Manila.", section=address, show_when=new_member),
        _field("home_zip", "ZIP code", "For a Philippine address, enter the 4-digit ZIP code.", max_length=12, section=address, show_when=new_member),
        _field("country", "Country", "Enter the country of this home address.", max_length=60, section=address, show_when=new_member),
        _field(
            "father_name",
            "Father's complete name",
            "Enter the father's first, middle, and last name.",
            max_length=160,
            section=family,
            show_when=new_member,
        ),
        _field(
            "mother_maiden_name",
            "Mother's complete maiden name",
            "Enter the mother's first, middle, and maiden last name.",
            max_length=160,
            section=family,
            show_when=new_member,
        ),
        _field("place_of_birth", "Place of birth", "Enter the place of birth shown on the civil registry record.", section=family, show_when=new_member),
        _field("birth_country", "Country of birth", "Enter the country of birth.", max_length=60, section=family, show_when=new_member),
        _field(
            "registration_purpose",
            "Purpose of registration",
            "Employment is for an employee. Self-employment is for a person with their own income. OFW is for a Filipino citizen working overseas. Non-working spouse is for a person married to an SSS member. SSS confirms eligibility.",
            field_type="select",
            options=SSS_PURPOSES,
            section=purpose,
            show_when=new_member,
        ),
        _field(
            "membership_category",
            "Membership category",
            "This follows the purpose you select. SSS confirms the category on the official website.",
            field_type="output",
            section=purpose,
            source="registration_purpose",
            lookup=SSS_CATEGORIES,
            empty="Select a purpose to show the membership category.",
            show_when=new_member,
        ),
        _field(
            "spouse_member_name",
            "Member spouse's complete name",
            "Enter the name of the SSS member you are married to. This appears only for a non-working spouse.",
            required=False,
            max_length=160,
            section=purpose,
            show_when=(new_member, ("registration_purpose", "Non-Working Spouse")),
            required_when_shown=True,
        ),
        _field(
            "spouse_member_ss_number",
            "Member spouse's SS Number",
            "Enter the 10-digit SS Number SSS already issued to your spouse. OneGov PH does not create it.",
            required=False,
            max_length=14,
            section=purpose,
            show_when=(new_member, ("registration_purpose", "Non-Working Spouse")),
            required_when_shown=True,
        ),
        _field(
            "mysss_user_id",
            "Preferred My.SSS user ID",
            "Enter 6 to 20 letters or numbers. SSS checks whether it is available. OneGov PH does not reserve it or ask for the My.SSS password.",
            max_length=20,
            section=purpose,
            show_when=new_member,
        ),
        _field("height_cm", "Height (cm)", "Enter your height in centimeters.", max_length=6, section=purpose, show_when=new_member),
        _field("weight_kg", "Weight (kg)", "Enter your weight in kilograms.", max_length=6, section=purpose, show_when=new_member),
        _field(
            "beneficiaries",
            "Beneficiaries",
            "Add a father, mother, child, or other eligible beneficiary when one applies. A spouse can be added only when your civil status is Married. You can add up to 10 beneficiaries.",
            field_type="beneficiaries",
            required=False,
            options=SSS_BENEFICIARY_RELATIONSHIPS,
            section=benefits,
            show_when=new_member,
        ),
    ]
    spec = _sss_common(choice, concern)
    if choice == SSS_HAS_YES:
        guidance_next = spec.get("official_next") or "Use the official SSS channel for this concern."
        documents = (
            _document(
                "supporting_document",
                "Supporting document for this concern",
                "Optional. Upload a JPEG, JPG, or PDF no larger than 3 MB when you have a document for this SSS concern. A file saved here is not submitted to SSS.",
                required=False,
            ),
        )
        examples = _existing_document_examples(concern)
        examples_heading = "Documents you may need for this concern"
        note = "Upload a supporting document only when it applies to the concern you selected. SSS receives the document through its own office or online service, not from OneGov PH."
        intro = "Prepare a JPEG, JPG, or PDF no larger than 3 MB if you have a document for this concern. OneGov PH stores the copy you choose. It is not submitted to SSS."
        submit_event = "Existing SS Number concern saved for monitoring. OneGov PH did not issue an SS Number or change the SSS record."
        submit_notice = "Your existing SS Number concern {reference} was saved in OneGov PH. No new SS Number was created."
        next_steps = [
            guidance_next,
            "Keep the OneGov PH reference number. It is not an SS Number or an SSS transaction number.",
            "Opening the official SSS link does not submit this concern and does not change the OneGov PH status.",
        ]
    elif choice == SSS_HAS_NO:
        documents = (
            _document(
                "supporting_document",
                "Supporting document you are preparing",
                "Optional in OneGov PH. On the SSS website, upload one readable color JPEG, JPG, or PDF no larger than 3 MB. A file saved here has not been submitted to SSS.",
                required=False,
            ),
        )
        examples = SSS_DOCUMENT_EXAMPLES
        examples_heading = "Examples of documents SSS accepts"
        note = "SSS lets an applicant continue without a document, but the SS Number can remain temporary until SSS approves a supporting document. Upload that document on the SSS website."
        intro = "Prepare a JPEG, JPG, or PDF no larger than 3 MB. OneGov PH stores the copy you choose. It is not submitted to SSS."
        submit_event = "SS Number preparation saved. This is not an SSS registration, and OneGov PH has not generated an SS Number."
        submit_notice = "Your SS Number preparation {reference} was saved in OneGov PH. Continue on the official SSS website. OneGov PH has not generated an SS Number."
        next_steps = [
            "Open the official SSS registration page and complete every SSS step there, including email verification.",
            "Keep the OneGov PH reference number. It is not an SS Number or an SSS transaction number.",
            "When SSS gives you an SS Number, a transaction number, or the E-1/E-6 form, record those details here.",
            "Opening the SSS website does not change the OneGov PH status.",
        ]
    else:
        documents = ()
        examples = ()
        examples_heading = ""
        note = ""
        intro = "Choose whether you already have an SSS Number before uploading a document."
        submit_event = "SSS request saved. OneGov PH has not generated an SS Number."
        submit_notice = "Your SSS request {reference} was saved in OneGov PH. OneGov PH has not generated an SS Number."
        next_steps = [
            "Keep the OneGov PH reference number. It is not an SS Number.",
        ]
    spec.update(
        {
            "fields": fields,
            "documents": documents,
            "document_examples": examples,
            "document_examples_heading": examples_heading,
            "document_note": note,
            "upload_intro": intro,
            "upload_accept": ".pdf,.jpg,.jpeg,application/pdf,image/jpeg",
            "reminders": [
                "An SS Number is issued once. If you already have one, answer Yes. Do not start a second registration.",
                "OneGov PH does not generate an SS Number, assign a number, or send this form to SSS.",
            ],
            "terms": "I certify that the information I provided is accurate and complete to the best of my knowledge.",
            "submit_event": submit_event,
            "submit_notice": submit_notice,
            "next_steps": next_steps,
        }
    )
    return spec


def specification_for(service, values=None):
    """Return the form for a catalog service, or None when Apply now is not available."""
    from app.services.philsys_national_id import SERVICE_NAMES, specification

    if service.service_name in SERVICE_NAMES:
        return specification(values or {})
    spec = SERVICE_FORMS.get(service.service_name)
    if spec is None:
        return None
    if spec.get("compose") == "barangay":
        return compose_barangay_clearance(values or {})
    if spec.get("compose") == "residency":
        return compose_certificate_of_residency(values or {})
    if spec.get("compose") == "senior":
        return compose_senior_citizen_id(values or {})
    if spec.get("compose") == "nbi":
        return compose_nbi_clearance(values or {})
    if spec.get("compose") == "cenomar":
        return compose_cenomar(values or {})
    if spec.get("compose") == "sss":
        return compose_sss(values or {})
    result = {
        "process": spec["process"],
        "fields": PERSONAL_FIELDS + spec["fields"],
        "documents": spec["documents"],
    }
    for extra in (
        "kind",
        "document_note",
        "upload_intro",
        "disclaimer",
        "kicker",
        "department_label",
        "step_labels",
        "confirmation_step",
        "status_labels",
        "submit_event",
        "submit_notice",
        "next_steps",
        "documents_first",
    ):
        if spec.get(extra):
            result[extra] = spec[extra]
    return result


def applicable_service_names():
    from app.services.philsys_national_id import SERVICE_NAMES

    names = set(SERVICE_FORMS)
    names.update(SERVICE_NAMES)
    return frozenset(names)
