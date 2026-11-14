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


BIRTH_DISCLAIMER = (
    "OneGov PH keeps this request for assistance and tracking. "
    "It is not sent to PSA as an official filing. PSA still issues the certificate."
)
BIRTH_FEE_NOTE = (
    "Demonstration total: ₱365.00 per copy "
    "(PSA Document Fee ₱155.00 + Processing, Convenience & Service Fees ₱160.00 + Courier / Delivery Fee ₱50.00). "
    "Two copies are charged ×2 (₱730.00). "
    "Pay online through OneGov PH after review (Maya sandbox or other demonstration methods). "
    "Confirm the current PSA fee and ordering rules on the official PSA channel."
)


def compose_birth_certificate(values=None):
    """PSA Birth Certificate request form with type-based document uploads."""
    from app.services.birth_requirements import document_requirements_for

    answers = values or {}
    selected_type = answers.get("application_type") or ""
    request_type = "Request type"
    certificate = "Certificate details"
    parents = "Parents"
    request_details = "Request details"
    representative = "Representative details"
    fields = [
        _field(
            "application_type",
            "Application type",
            "Selected on step 1. This determines the documents you must upload.",
            field_type="hidden",
            required=True,
            section=request_type,
        ),
        _field(
            "certificate_for",
            "Who is named on the certificate",
            "Choose Self if the certificate is yours. Choose another option if you are requesting it for a relative.",
            field_type="select",
            options=("Self", "Child", "Parent", "Spouse", "Other relative"),
            section=certificate,
        ),
        _field(
            "owner_first_name",
            "Certificate owner's first name",
            "Enter the first name printed on the birth record.",
            section=certificate,
        ),
        _field(
            "owner_middle_name",
            "Certificate owner's middle name",
            "Leave this blank if the birth record has no middle name.",
            required=False,
            section=certificate,
        ),
        _field(
            "owner_last_name",
            "Certificate owner's last name",
            "Enter the last name printed on the birth record.",
            section=certificate,
        ),
        _field(
            "owner_birth_date",
            "Certificate owner's date of birth",
            "Use the date of birth on the birth record.",
            field_type="date",
            section=certificate,
        ),
        _field(
            "place_of_birth",
            "Place of birth",
            "Enter the city or municipality and province of birth.",
            section=certificate,
        ),
        _field(
            "father_name",
            "Father's complete name",
            "Enter the father's name as it should appear on the record.",
            section=parents,
        ),
        _field(
            "mother_maiden_name",
            "Mother's complete maiden name",
            "Enter the mother's maiden name, not her married name.",
            section=parents,
        ),
        _field(
            "copies",
            "Number of copies",
            "Enter how many copies you are preparing to request, from 1 to 5.",
            field_type="number",
            max_length=1,
            section=request_details,
        ),
        _field(
            "representative",
            "Applying through a representative",
            "Choose Yes only if another person will submit or claim this request for you.",
            field_type="select",
            options=("No", "Yes"),
            section=representative,
        ),
        _field(
            "representative_name",
            "Representative’s full name",
            "Enter the complete name of the person who will submit or claim this request.",
            section=representative,
            show_when=("representative", "Yes"),
            required_when_shown=True,
        ),
        _field(
            "representative_relationship",
            "Relationship to the certificate owner",
            "Example: parent, child, spouse, sibling, or authorized relative.",
            max_length=80,
            section=representative,
            show_when=("representative", "Yes"),
            required_when_shown=True,
        ),
        _field(
            "representative_contact",
            "Representative’s contact number",
            "Enter a mobile or telephone number for the representative.",
            field_type="tel",
            max_length=20,
            section=representative,
            show_when=("representative", "Yes"),
            required_when_shown=True,
        ),
        _field(
            "representative_details",
            "Additional representative details",
            "Optional. Add any extra notes about the representative or how the request will be claimed.",
            field_type="textarea",
            required=False,
            max_length=500,
            section=representative,
            show_when=("representative", "Yes"),
        ),
    ]
    type_docs = document_requirements_for(selected_type)
    documents = tuple(
        _document(
            item["key"],
            item["label"],
            item["help"],
            required=bool(item.get("required", True)),
            id_choices=item.get("id_choices"),
        )
        for item in type_docs["documents"]
    )
    personal = []
    for field in PERSONAL_FIELDS:
        item = dict(field)
        item["section"] = "Requester information"
        personal.append(item)
    return {
        "kind": "birth",
        "kicker": "Civil registry assistance",
        "department_label": "PSA assistance",
        "service_title": "Birth Certificate",
        "process": (
            "OneGov PH records your PSA birth certificate request so you can track the details and documents you prepared. "
            "PSA still issues the certificate."
        ),
        "fields": tuple(personal) + tuple(fields),
        "documents": documents,
        "document_note": type_docs.get("note")
        or "Upload the required documents for your selected birth certificate request type.",
        "fee_note": BIRTH_FEE_NOTE,
        "catalog_fee": BIRTH_FEE_NOTE,
        "disclaimer": BIRTH_DISCLAIMER,
        "step_labels": (
            "1. Application type",
            "2. Application details",
            "3. Documents",
            "4. Review",
            "5. Payment",
            "6. Confirmation",
        ),
        "type_first": True,
        "payment_after_review": True,
        "online_payment_only": True,
        "submit_label": "Continue to payment",
        "confirmation_step": 6,
        "reminders": [
            "OneGov PH does not submit this request to PSA.",
            "Upload the documents required for your selected request type.",
            "Pay the demonstration total of ₱365.00 per copy after review (×2 for two copies), then keep your reference for tracking.",
        ],
        "terms": (
            "I confirm that the information and documents in this request are accurate. " + BIRTH_DISCLAIMER
        ),
        "next_steps": [
            "Keep your reference number and use it when you ask about this birth certificate request.",
            "The OneGov PH demonstration total (₱365.00 per copy) was recorded on payment. Confirm any separate PSA charges on the official channel.",
            "PSA still issues the official certificate. OneGov PH does not mark this request approved or completed.",
            "Open Application tracking to follow status changes and any instructions recorded on your account.",
        ],
        "submit_event": (
            "Birth certificate request and payment were saved for assistance and tracking. "
            "PSA has not reviewed it, and OneGov PH has not marked it approved or completed."
        ),
        "submit_notice": (
            "Your Birth Certificate request {reference} was submitted in OneGov PH. "
            "It is not an official filing. PSA remains responsible for issuing the certificate."
        ),
        "status_labels": {
            "paid": "Paid",
            "submitted": "Submitted",
            "pending_documents": "Additional documents required",
            "ready_for_release": "Ready for pickup",
        },
    }


SERVICE_FORMS = {
    "Birth Certificate": {"compose": "birth"},
    "CENOMAR": {"compose": "cenomar"},
    "Passport Application Assistance and Tracking": {
        **_service(
            "OneGov PH records passport demonstration details for portfolio tracking. "
            "This is not an official DFA application.",
            (
                _field(
                    "application_type",
                    "Application type",
                    "Selected on step 1. This determines the physical documents you need to bring.",
                    field_type="hidden",
                    required=True,
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
        "service_title": "Passport Application",
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
            "1. Application type",
            "2. Documents",
            "3. Application details",
            "4. Review",
            "5. Scheduling",
            "6. Payment",
            "7. Confirmation",
        ),
        "type_first": True,
        "documents_first": True,
        "review_before_schedule": True,
        "review_back": "details",
        "submit_label": "Continue to scheduling",
        "terms": (
            "I confirm that the application details and uploaded ID in this demonstration are accurate. "
            "I understand that OneGov PH is not affiliated with or authorized by the Department of Foreign Affairs (DFA), "
            "and that appointment schedules, payments, and confirmations here are simulated."
        ),
        "fee_note": "Demonstration passport fee: ₱1,150.00. You choose Maya sandbox or onsite payment after scheduling.",
        "confirmation_step": 7,
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
            "Bring the physical documents listed for your application type to your appointment.",
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
    "Processing fee: ₱50.00. "
    "Pay online through OneGov PH after scheduling (Maya sandbox or other demonstration methods). "
    "The barangay may still ask for separate local charges when you claim the clearance."
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
            "application_type",
            "Application type",
            "Selected on step 1. This determines the required documents you must upload.",
            field_type="hidden",
            required=True,
            section=purpose_section,
        ),
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
            "purpose_notes",
            "Additional purpose notes",
            "Optional. Add any extra detail the barangay may need beyond the application type selected on step 1.",
            field_type="textarea",
            required=False,
            max_length=400,
            section=purpose_section,
        ),
    ]
    if profile["require_nationality"]:
        fields.insert(
            7,
            _field(
                "nationality",
                "Nationality",
                "This barangay asks for your nationality.",
                section=applicant,
            ),
        )
    from app.services.barangay_requirements import document_requirements_for

    type_docs = document_requirements_for(answers.get("application_type"))
    documents = tuple(
        _document(
            item["key"],
            item["label"],
            item["help"],
            required=bool(item.get("required", True)),
            id_choices=item.get("id_choices"),
        )
        for item in type_docs["documents"]
    )
    selected_type = type_docs.get("application_type") or "your selected application type"
    if type_docs.get("note"):
        document_note = type_docs["note"]
    elif profile["verified"] and barangay and city:
        document_note = (
            f"Upload every required document for {selected_type}. "
            f"This checklist follows the verified requirements on file for {barangay}, {city}."
        )
    elif barangay and city:
        document_note = (
            f"Upload every required document for {selected_type}. "
            f"Confirm the final list with {barangay}, {city}, because requirements can differ by barangay."
        )
    else:
        document_note = (
            f"Upload every required document for {selected_type}. "
            "Confirm the final list with the issuing barangay before you visit."
        )
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
        "online_payment_only": True,
        "fee_note": fee_note,
        "catalog_fee": BARANGAY_FEE_NOTE,
        "disclaimer": BARANGAY_DISCLAIMER,
        "local_office": office,
        "show_submitted_details": True,
        "step_labels": (
            "1. Application type",
            "2. Application details",
            "3. Documents",
            "4. Review",
            "5. Scheduling",
            "6. Payment",
            "7. Confirmation",
        ),
        "type_first": True,
        "review_before_schedule": True,
        "payment_after_review": False,
        "submit_label": "Continue to scheduling",
        "confirmation_step": 7,
        "terms": "I confirm that the information and documents in this request are accurate. " + BARANGAY_DISCLAIMER,
        "next_steps": [
            "Keep your reference number and use it when you ask the barangay about this request.",
            "The ₱50.00 OneGov PH demonstration fee was recorded on payment. Confirm any separate barangay charges before pickup.",
            "The barangay reviews the request and issues the official clearance. OneGov PH does not mark this request approved or completed.",
            "Open Application tracking to follow status changes and any instructions recorded on your account.",
        ],
        "submit_event": (
            "Barangay clearance request and payment were saved for assistance and tracking. "
            "The barangay has not reviewed it, and OneGov PH has not marked it approved or completed."
        ),
        "submit_notice": (
            "Your Barangay Clearance request {reference} was submitted in OneGov PH. "
            "It is not an official filing. The barangay remains responsible for reviewing it and issuing the clearance."
        ),
        "status_labels": {
            "paid": "Paid",
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
    "Processing fee: ₱50.00. "
    "Pay online through OneGov PH after scheduling (Maya sandbox or other demonstration methods). "
    "The barangay or city may still ask for separate local charges when you claim the certificate."
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
            "application_type",
            "Application type",
            "Selected on step 1. This determines the required documents you must upload.",
            field_type="hidden",
            required=True,
            section=purpose_section,
        ),
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
            "purpose_notes",
            "Additional purpose notes",
            "Optional. Add any extra detail the issuing office may need beyond the application type selected on step 1.",
            field_type="textarea",
            required=False,
            max_length=400,
            section=purpose_section,
        ),
    ]
    if profile["require_nationality"]:
        fields.insert(
            7,
            _field(
                "nationality",
                "Nationality",
                "This local government asks for your nationality.",
                section=personal,
            ),
        )
    from app.services.residency_requirements import document_requirements_for

    type_docs = document_requirements_for(answers.get("application_type"))
    documents = [
        _document(
            item["key"],
            item["label"],
            item["help"],
            required=bool(item.get("required", True)),
            id_choices=item.get("id_choices"),
        )
        for item in type_docs["documents"]
    ]
    documents.extend(_extra_documents(profile))
    selected_type = type_docs.get("application_type") or "your selected application type"
    if type_docs.get("note"):
        document_note = (
            f"Upload every required document for {selected_type}. {type_docs['note']}"
        )
    elif profile["verified"] and barangay and city:
        document_note = (
            f"Upload every required document for {selected_type}. "
            f"This checklist follows the verified requirements on file for {barangay}, {city}."
        )
    elif barangay and city:
        document_note = (
            f"Upload every required document for {selected_type}. "
            f"Confirm the final list with {barangay}, {city}, because requirements can differ by barangay or city."
        )
    else:
        document_note = (
            f"Upload every required document for {selected_type}. "
            "Confirm the final list with the issuing barangay or city before you visit."
        )
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
        "kicker": "Local government request",
        "department_label": "Barangay assistance",
        "service_title": "Certificate of Residency",
        "process": "Prepare a certificate of residency for the barangay or city you name below. That office still verifies your residency and issues the certificate.",
        "fields": fields,
        "documents": tuple(documents),
        "document_note": document_note,
        "online_payment_only": True,
        "fee_note": fee_note,
        "catalog_fee": RESIDENCY_FEE_NOTE,
        "disclaimer": RESIDENCY_DISCLAIMER,
        "local_office": office,
        "show_submitted_details": True,
        "step_labels": (
            "1. Application type",
            "2. Application details",
            "3. Documents",
            "4. Review",
            "5. Scheduling",
            "6. Payment",
            "7. Confirmation",
        ),
        "type_first": True,
        "review_before_schedule": True,
        "payment_after_review": False,
        "submit_label": "Continue to scheduling",
        "confirmation_step": 7,
        "terms": "I confirm that the information and documents in this request are accurate. " + RESIDENCY_DISCLAIMER,
        "next_steps": [
            "Keep your reference number and use it when you ask the barangay or city about this request.",
            "The ₱50.00 OneGov PH demonstration fee was recorded on payment. Confirm any separate local charges before pickup.",
            "The barangay or city verifies residency and issues the official certificate. OneGov PH does not mark this request approved or completed.",
            "Open Application tracking to follow status changes. Only authorized personnel can update the status after you submit.",
        ],
        "submit_event": (
            "Certificate of residency request and payment were saved for assistance and tracking. "
            "The local government has not reviewed it, and OneGov PH has not marked it approved or completed."
        ),
        "submit_notice": (
            "Your Certificate of Residency request {reference} was submitted in OneGov PH. "
            "It is not an official filing. The barangay or city government remains responsible for verifying residency and issuing the certificate."
        ),
        "status_labels": {
            "paid": "Paid",
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
    "New application fee: ₱0.00. Payment is not required for a first-time Senior Citizen ID. "
    "Lost or damaged ID replacements use an admin-configurable fee. "
    "An official receipt is issued only if a payment is collected."
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


def _senior_document(
    profile,
    key,
    label,
    help_text,
    default_required=False,
    required_when=None,
    id_choices=None,
    status_label=None,
):
    configured = (profile.get("documents") or {}).get(key)
    required = default_required if configured is None else bool(configured)
    item = _document(
        key,
        label,
        help_text,
        required=required,
        required_when=None if required else required_when,
        id_choices=id_choices,
    )
    item["status_label"] = status_label or ("Required" if required and required_when is None else "Conditional")
    return item


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
        _field(
            "application_type",
            "Application type",
            "Selected on step 1. This determines the physical documents you need to bring to OSCA.",
            field_type="hidden",
            required=True,
            section=request_type,
        ),
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
            "Valid Government-Issued ID",
            "Choose one valid government ID, then upload a clear PDF or photo of that same ID. The name should match this application.",
            default_required=True,
            id_choices="barangay",
            status_label="Required",
        ),
        _senior_document(
            profile,
            "age_proof",
            "Proof of Age",
            "Upload a PSA birth certificate or another proof of age your OSCA office accepts.",
            default_required=True,
            status_label="Required",
        ),
        _senior_document(
            profile,
            "residency_proof",
            "Proof of Residency",
            "Upload a barangay certification or another proof of residency your OSCA office accepts.",
            default_required=True,
            status_label="Required",
        ),
        _senior_document(
            profile,
            "photo",
            "Recent ID Photo",
            "Upload a recent photo of your face. Ask your OSCA office whether it should be 1x1 or 2x2. OneGov PH does not measure the photo.",
            default_required=True,
            status_label="Required",
        ),
        _senior_document(
            profile,
            "authorization",
            "Authorization Letter",
            "Needed when a representative will submit or claim this request. Upload a signed authorization letter.",
            required_when=("representative", "Yes"),
            status_label="Conditional",
        ),
        _senior_document(
            profile,
            "representative_id",
            "Representative’s Government ID",
            "Needed with the authorization letter. Upload a clear PDF or photo of the representative’s government ID.",
            required_when=("representative", "Yes"),
            status_label="Conditional",
        ),
        _senior_document(
            profile,
            "previous_senior_id",
            "Previous Senior Citizen ID",
            "Needed for a transfer. Upload a copy of the Senior Citizen ID issued by the previous office.",
            required_when=("id_transfer", "Yes"),
            status_label="Conditional",
        ),
        _senior_document(
            profile,
            "cancellation_transfer",
            "Certificate of Cancellation/Transfer",
            "Needed for a transfer. Upload the certificate of cancellation or transfer from the previous OSCA office.",
            required_when=("id_transfer", "Yes"),
            status_label="Conditional",
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
        "kicker": "Local government request",
        "department_label": "OSCA assistance",
        "service_title": "Senior Citizen ID",
        "process": "Prepare a Senior Citizen ID request for the OSCA office that covers your address. You must be 60 or older. That office still verifies eligibility and issues the ID.",
        "fields": fields,
        "documents": documents,
        "document_note": document_note,
        "fee_note": fee_note,
        "catalog_fee": SENIOR_FEE_NOTE,
        "disclaimer": SENIOR_DISCLAIMER,
        "local_office": office,
        "show_submitted_details": True,
        "step_labels": (
            "1. Application type",
            "2. Application details",
            "3. Documents",
            "4. Review",
            "5. Scheduling",
            "6. Payment",
            "7. Confirmation",
        ),
        "type_first": True,
        "review_before_schedule": True,
        "payment_after_review": False,
        "submit_label": "Continue to scheduling",
        "confirmation_step": 7,
        "reminders": [
            "You must be 60 years old or older on the day you submit this request.",
            "Confirm the citizenship and residency requirements with your OSCA office. OneGov PH does not apply a local residency rule unless a verified OSCA requirement is on file.",
        ],
        "terms": "I confirm that the information and documents in this request are accurate. " + SENIOR_DISCLAIMER,
        "next_steps": [
            "Keep your reference number and use it when you ask the OSCA office about this request.",
            "Bring the physical documents listed on your confirmation page and receipt for OSCA verification.",
            "New applications are free (₱0.00). Lost or damaged replacements may use an admin-configurable fee.",
            "The local government and OSCA verify eligibility and issue the Senior Citizen ID. OneGov PH does not mark this request approved or completed.",
            "Open Application tracking to follow status changes and any instructions recorded from OSCA. Only authorized personnel can update the status after you submit.",
        ],
        "submit_event": (
            "Senior Citizen ID request saved for assistance and tracking. "
            "No payment was required for this new application. "
            "OSCA has not reviewed it, and OneGov PH has not marked it approved or completed."
        ),
        "submit_notice": (
            "Your Senior Citizen ID request {reference} was submitted in OneGov PH. "
            "It is not an official filing. No payment was collected for this new application. "
            "The local government and OSCA remain responsible for verifying eligibility and issuing the ID."
        ),
        "status_labels": {
            "not_applicable": "Not applicable",
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
    "Regular NBI Clearance: ₱130.00. Online payment convenience fee: ₱30.00. "
    "Regular online application total: ₱160.00."
)
_EDUCATION = ("Elementary", "High school", "Senior high school", "Vocational", "College", "Postgraduate")
_EMPLOYMENT = ("Employed", "Self-employed", "Unemployed", "Student", "Retired", "Overseas worker")

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
        "require_employment_status": False,
        "education_options": _EDUCATION,
        "employment_options": _EMPLOYMENT,
        "documents": {
            "valid_id": True,
            "valid_id_secondary": True,
        },
        "instructions": None,
    }
    if not verified:
        return defaults
    merged = {**defaults, **verified, "verified": True}
    merged["documents"] = {**defaults["documents"], **(verified.get("documents") or {})}
    return merged


def _nbi_document(profile, key, label, help_text, default_required=False, id_choices=None, status_label=None):
    configured = (profile.get("documents") or {}).get(key)
    required = default_required if configured is None else bool(configured)
    item = _document(key, label, help_text, required=required, id_choices=id_choices)
    item["status_label"] = status_label or ("Required" if required else "Optional")
    return item


def compose_nbi_clearance(values=None):
    """NBI clearance monitoring form. Other services keep their own questions."""
    from app.services.nbi_requirements import (
        document_requirements_for,
        is_nbi_new_application,
        requires_nbi_schedule,
    )

    answers = values or {}
    profile = nbi_profile()
    applicant = "Applicant information"
    father = "Father"
    mother = "Mother"
    background = "Education and employment"
    application_section = "Application type"
    selected_type = answers.get("application_type") or ""
    needs_schedule = requires_nbi_schedule(selected_type)
    is_new = is_nbi_new_application(selected_type)
    fields = [
        _field(
            "application_type",
            "Application type",
            "Selected on step 1. This determines whether you schedule an NBI visit or continue fully online.",
            field_type="hidden",
            required=True,
            section=application_section,
        ),
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
                "Optional. Select the status that applies to you today if you want it on this request.",
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
        ]
    )
    type_docs = document_requirements_for(selected_type)
    documents = tuple(
        _nbi_document(
            profile,
            item["key"],
            item["label"],
            item["help"],
            default_required=bool(item.get("required", True)),
            id_choices=item.get("id_choices"),
        )
        for item in type_docs["documents"]
    )
    if is_new and profile["verified"] and (profile.get("documents") or {}).get("photo"):
        documents = documents + (
            _nbi_document(
                profile,
                "photo",
                "Recent photo",
                "A confirmed requirement asks for this file. NBI still captures the photograph and biometrics at the branch.",
                default_required=True,
            ),
        )
    document_note = type_docs.get("note") or (
        "Upload the required documents for your selected NBI application type."
    )
    office = {
        "heading": "National Bureau of Investigation",
        "note": (
            "OneGov PH schedules a demonstration appointment only for New Application monitoring requests. "
            "It has no live connection to NBI. Confirm current requirements through NBI."
            if needs_schedule
            else (
                "This request continues online without a demonstration appointment. "
                "OneGov PH has no live connection to NBI. Confirm current requirements through NBI."
            )
        ),
    }
    if profile["verified"] and profile.get("instructions"):
        office["instructions"] = profile["instructions"]
        office["instructions_heading"] = "Instructions"
    if needs_schedule:
        step_labels = (
            "1. Application type",
            "2. Application details",
            "3. Documents",
            "4. Review",
            "5. Scheduling",
            "6. Payment",
            "7. Confirmation",
        )
        confirmation_step = 7
        submit_label = "Continue to scheduling"
        next_steps = [
            "Keep your OneGov PH reference number. It is separate from any reference number NBI gives you.",
            "Bring the physical documents listed on your confirmation page and receipt to the NBI Clearance Center.",
            "Attend the demonstration appointment you scheduled, then complete biometrics and clearance issuance through NBI.",
            "The regular online application total shown here is ₱160.00 (₱130.00 clearance + ₱30.00 convenience fee).",
            "Open Application tracking to follow monitoring updates such as Submitted, Under review, Appointment scheduled, Payment pending, Payment completed, For biometrics, With hit, Ready for release, Completed, Rejected, or Cancelled.",
        ]
        reminders = [
            "OneGov PH does not register this request with NBI.",
            "New applicants must personally appear at an NBI Clearance Center for biometric registration.",
            "The appointment you schedule here is a demonstration booking for monitoring only.",
            "NBI takes the photograph and biometrics at the branch for an ordinary local application.",
            "After you submit, only authorized personnel can change the monitoring status. Those statuses are notes in OneGov PH, not a live update from NBI.",
        ]
    else:
        step_labels = (
            "1. Application type",
            "2. Application details",
            "3. Documents",
            "4. Review",
            "5. Payment",
            "6. Confirmation",
        )
        confirmation_step = 6
        submit_label = "Continue to payment"
        next_steps = [
            "Keep your OneGov PH reference number. It is separate from any reference number NBI gives you.",
            "This request continues online. NBI may still instruct you to appear for additional verification.",
            "The regular online application total shown here is ₱160.00 (₱130.00 clearance + ₱30.00 convenience fee).",
            "Open Application tracking to follow monitoring updates such as Submitted, Under review, Payment pending, Payment completed, For biometrics, With hit, Ready for release, Completed, Rejected, or Cancelled.",
        ]
        reminders = [
            "OneGov PH does not register this request with NBI.",
            "Eligible renewal, lost, or damaged requests may continue online when NBI does not require an immediate visit.",
            "Original identification documents must be presented when physical verification is required.",
            "After you submit, only authorized personnel can change the monitoring status. Those statuses are notes in OneGov PH, not a live update from NBI.",
        ]
    return {
        "kind": "nbi",
        "kicker": "Clearance monitoring",
        "department_label": "NBI assistance",
        "service_title": "NBI Clearance",
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
        "step_labels": step_labels,
        "type_first": True,
        "review_before_schedule": needs_schedule,
        "payment_after_review": not needs_schedule,
        "online_payment_only": not needs_schedule,
        "submit_label": submit_label,
        "confirmation_step": confirmation_step,
        "reminders": reminders,
        "terms": "I confirm that the information and documents in this request are accurate. " + NBI_DISCLAIMER,
        "next_steps": next_steps,
        "submit_event": (
            "NBI clearance request and payment were saved for assistance and monitoring. "
            "NBI has not received this as an official filing, and OneGov PH has not marked it approved or completed."
        ),
        "submit_notice": (
            "Your NBI clearance request {reference} was submitted in OneGov PH for monitoring. "
            "It is not an official NBI registration. Biometrics, verification, and clearance issuance remain with NBI."
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
    "Demonstration total: ₱365.00 per copy "
    "(PSA Document Fee ₱155.00 + Processing, Convenience & Service Fees ₱160.00 + Courier / Delivery Fee ₱50.00). "
    "Two copies are charged ×2 (₱730.00). "
    "Pay through OneGov PH after review (Maya sandbox or onsite demonstration). "
    "Confirm the current PSA fee and ordering rules on the official PSA channel."
)
CENOMAR_URL = "https://www.psaserbilis.com.ph/"
_CENOMAR_PURPOSE = ("Marriage", "Employment", "Legal Purposes", "Immigration", "Personal Records", "Other")
_CENOMAR_REQUESTER = ("Self", "Child", "Parent", "Spouse")
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
    """Return True when any required CENOMAR answer is still missing."""
    answers = values or {}
    required = (
        "first_name",
        "last_name",
        "date_of_birth",
        "sex",
        "civil_status",
        "nationality",
        "address",
        "contact_number",
        "email",
        "certificate_for",
        "owner_first_name",
        "owner_last_name",
        "owner_birth_date",
        "owner_sex",
        "owner_civil_status",
        "place_of_birth",
        "father_name",
        "mother_maiden_name",
        "copies",
        "purpose",
    )
    for key in required:
        if not str(answers.get(key) or "").strip():
            return True
    if answers.get("purpose") == "Other" and not str(answers.get("purpose_other") or "").strip():
        return True
    return None


def compose_cenomar(values=None):
    """CENOMAR preparation and monitoring. PSA Serbilis still takes the official application."""
    requester = "Requester information"
    certificate = "Certificate details"
    parents = "Parents"
    request = "Request details"
    fields = []
    for field in PERSONAL_FIELDS:
        item = dict(field)
        item["section"] = requester
        fields.append(item)
    fields.extend(
        [
            _field(
                "certificate_for",
                "Who is named on the CENOMAR",
                "Choose Self if the CENOMAR is yours. Choose another option if you are requesting it for a relative.",
                field_type="select",
                options=_CENOMAR_REQUESTER,
                section=certificate,
            ),
            _field(
                "owner_first_name",
                "Certificate owner's first name",
                "Enter the first name of the person named on the CENOMAR.",
                section=certificate,
            ),
            _field(
                "owner_middle_name",
                "Certificate owner's middle name",
                "Leave this blank if that person has no middle name.",
                required=False,
                section=certificate,
            ),
            _field(
                "owner_last_name",
                "Certificate owner's last name",
                "Enter the last name of the person named on the CENOMAR.",
                section=certificate,
            ),
            _field(
                "owner_birth_date",
                "Certificate owner's date of birth",
                "Use the date of birth on the birth record. A future date is not accepted.",
                field_type="date",
                section=certificate,
            ),
            _field(
                "owner_sex",
                "Certificate owner's sex",
                "Select the sex recorded for the person named on the CENOMAR.",
                field_type="select",
                options=_SEX,
                section=certificate,
            ),
            _field(
                "owner_civil_status",
                "Certificate owner's civil status",
                "Select the civil status of the person named on the CENOMAR.",
                field_type="select",
                options=_CIVIL_STATUS,
                section=certificate,
            ),
            _field(
                "place_of_birth",
                "Place of birth",
                "Enter the city or municipality and province of birth.",
                section=certificate,
            ),
            _field(
                "father_name",
                "Father's complete name",
                "Enter the father's name as it should appear on the record.",
                max_length=160,
                section=parents,
            ),
            _field(
                "mother_maiden_name",
                "Mother's complete maiden name",
                "Enter the mother's maiden name, not her married name.",
                max_length=160,
                section=parents,
            ),
            _field(
                "copies",
                "Number of copies",
                "Enter how many copies you are preparing to request, from 1 to 5. Confirm the current limit on the official PSA channel.",
                field_type="number",
                max_length=1,
                default="1",
                section=request,
            ),
            _field(
                "purpose",
                "Purpose of Request",
                "Select why the certificate is being requested.",
                field_type="select",
                options=_CENOMAR_PURPOSE,
                section=request,
            ),
            _field(
                "purpose_other",
                "Other purpose",
                "Enter your purpose. This is shown only when you select Other.",
                required=False,
                max_length=200,
                section=request,
                show_when=("purpose", "Other"),
                required_when_shown=True,
            ),
        ]
    )
    return {
        "kind": "cenomar",
        "kicker": "Civil registry assistance",
        "service_title": "Certificate of No Marriage Record (CENOMAR)",
        "process": (
            "A CENOMAR is an official certification issued by the Philippine Statistics Authority confirming that "
            "no marriage record has been found under the specified person’s name in the PSA civil registry."
        ),
        "department_label": "PSA assistance",
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
            "1. Application details",
            "2. Review",
            "3. Payment",
            "4. Confirmation",
        ),
        "payment_after_review": True,
        "review_back": "details",
        "submit_label": "Continue to payment",
        "confirmation_step": 4,
        "reminders": [
            "OneGov PH prepares and tracks this CENOMAR request. PSA still issues the official certificate.",
            "The person named on the certificate, or that person's child, parent, or spouse, can prepare a request. PSA decides who is eligible.",
            "Pay the demonstration total of ₱365.00 per copy after review (×2 for two copies), then keep your reference for tracking.",
            "You can still open PSA Serbilis for the official channel. OneGov PH does not create a PSA reference number.",
        ],
        "terms": "I confirm that the information in this request is accurate. " + CENOMAR_DISCLAIMER,
        "next_steps": [
            "Keep your OneGov PH reference number and use it when you ask about this CENOMAR request.",
            "The OneGov PH demonstration total (₱365.00 per copy) was recorded on payment. Confirm any separate PSA charges on the official channel.",
            "PSA still issues the official CENOMAR. OneGov PH does not mark this request approved or completed.",
            "When PSA gives you a 16-digit reference number, you can record it on this request later.",
        ],
        "submit_event": (
            "CENOMAR request and payment were saved for assistance and tracking. "
            "PSA has not reviewed it, and OneGov PH has not marked it approved or completed."
        ),
        "submit_notice": (
            "Your CENOMAR request {reference} was submitted in OneGov PH. "
            "It is not an official filing. PSA remains responsible for issuing the certificate."
        ),
        "status_labels": {
            "draft": "Draft",
            "paid": "Paid",
            "submitted": "Submitted",
            "under_review": "Official application recorded",
            "rejected": "Rejected / needs attention",
            "ready_for_release": "Ready for pickup",
        },
    }


SSS_PATH_NEW = "First-time SS Number registration"
SSS_URL = "https://www.sss.gov.ph/become-an-sss-member"
SSS_SITE = "https://www.sss.gov.ph/"
SSS_NOTICE = (
    "Official SS Number registration and issuance are performed through the SSS online registration system. "
    "OneGov PH does not directly generate or issue SS Numbers."
)
SSS_DESCRIPTION = (
    "OneGov PH helps a first-time applicant prepare an SS Number registration. "
    "SSS issues the number and handles the official record. OneGov PH does not generate or assign an SS Number."
)
SSS_FEE_NOTE = (
    "SS Number registration has no SSS processing fee. "
    "OneGov PH does not collect a payment and does not issue an SS Number."
)
SSS_HAS_PRIMARY_YES = "Yes, I have a primary government ID"
SSS_HAS_PRIMARY_NO = "No, I will upload alternative identification"
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


def _sss_document(key, label, help_text, required=False, required_when=None, id_choices=None, status_label=None):
    item = _document(
        key,
        label,
        help_text,
        required=required,
        required_when=required_when,
        id_choices=id_choices,
    )
    if status_label:
        item["status_label"] = status_label
    return item


def compose_sss(values=None):
    """SS Number registration assistance: details, ID documents, review, free payment, confirmation."""
    answers = values or {}
    personal = "Personal information"
    contact = "Contact information"
    address = "Address"
    family = "Family and place of birth"
    purpose = "Registration information"
    benefits = "Beneficiary information"
    identification = "Identification"
    primary_yes = ("has_primary_id", SSS_HAS_PRIMARY_YES)
    primary_no = ("has_primary_id", SSS_HAS_PRIMARY_NO)
    fields = [
        _field(
            "sss_path",
            "Request type",
            "First-time SS Number registration assistance.",
            field_type="hidden",
            required=False,
            default=SSS_PATH_NEW,
        ),
        _field(
            "first_name",
            "First name",
            "Enter your first name as it appears on the civil registry record.",
            section=personal,
        ),
        _field(
            "middle_name",
            "Middle name",
            "Leave this blank if there is no middle name.",
            required=False,
            section=personal,
        ),
        _field(
            "last_name",
            "Last name",
            "Enter your last name as it appears on the civil registry record.",
            section=personal,
        ),
        _field(
            "suffix",
            "Suffix",
            "Select a suffix only if it appears on the civil registry record.",
            field_type="select",
            required=False,
            options=("Jr.", "Sr.", "II", "III", "IV", "V"),
            section=personal,
        ),
        _field(
            "date_of_birth",
            "Date of birth",
            "Use your date of birth. A future date is not accepted.",
            field_type="date",
            section=personal,
        ),
        _field(
            "sex",
            "Sex",
            "Select the sex on the civil registry record.",
            field_type="select",
            options=_SEX,
            section=personal,
        ),
        _field(
            "civil_status",
            "Civil status",
            "Select your civil status. A non-working spouse registration requires Married.",
            field_type="select",
            options=_CIVIL_STATUS,
            section=personal,
        ),
        _field(
            "citizenship",
            "Citizenship",
            "Select the citizenship SSS should use for this registration.",
            field_type="select",
            options=("Filipino", "Dual Citizen", "Foreign National"),
            section=personal,
        ),
        _field(
            "nationality",
            "Nationality",
            "Enter your nationality. This is required for a foreign national.",
            required=False,
            section=personal,
            show_when=("citizenship", "Foreign National"),
            required_when_shown=True,
        ),
        _field(
            "mobile_number",
            "Mobile number",
            "Enter a Philippine mobile number, such as 09171234567.",
            field_type="tel",
            max_length=20,
            section=contact,
        ),
        _field(
            "email",
            "Email address",
            "Enter an email address you can open. SSS sends its verification link to this address. OneGov PH does not send or confirm that email.",
            field_type="email",
            max_length=255,
            section=contact,
        ),
        _field(
            "house_number",
            "House / lot number",
            "Enter the house, lot, unit, or building number.",
            max_length=80,
            section=address,
        ),
        _field("street", "Street", "Enter the street name.", max_length=120, section=address),
        _field(
            "subdivision",
            "Subdivision",
            "Leave this blank if there is no subdivision.",
            required=False,
            max_length=120,
            section=address,
        ),
        _field("barangay", "Barangay", "Enter the barangay.", section=address),
        _field("city", "City / municipality", "Enter the city or municipality.", section=address),
        _field(
            "province",
            "Province",
            "Enter the province. For Metro Manila, you may enter Metro Manila.",
            section=address,
        ),
        _field(
            "home_zip",
            "ZIP code",
            "For a Philippine address, enter the 4-digit ZIP code.",
            max_length=12,
            section=address,
        ),
        _field(
            "country",
            "Country",
            "Enter the country of this home address.",
            max_length=60,
            section=address,
            default="Philippines",
        ),
        _field(
            "father_name",
            "Father's complete name",
            "Enter the father's first, middle, and last name.",
            max_length=160,
            section=family,
        ),
        _field(
            "mother_maiden_name",
            "Mother's complete maiden name",
            "Enter the mother's first, middle, and maiden last name.",
            max_length=160,
            section=family,
        ),
        _field(
            "place_of_birth",
            "Place of birth",
            "Enter the place of birth shown on the civil registry record.",
            section=family,
        ),
        _field(
            "birth_country",
            "Country of birth",
            "Enter the country of birth.",
            max_length=60,
            section=family,
            default="Philippines",
        ),
        _field(
            "registration_purpose",
            "Purpose of registration",
            "Employment is for an employee. Self-employment is for a person with their own income. OFW is for a Filipino citizen working overseas. Non-working spouse is for a person married to an SSS member. SSS confirms eligibility.",
            field_type="select",
            options=SSS_PURPOSES,
            section=purpose,
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
        ),
        _field(
            "spouse_member_name",
            "Member spouse's complete name",
            "Enter the name of the SSS member you are married to. This appears only for a non-working spouse.",
            required=False,
            max_length=160,
            section=purpose,
            show_when=("registration_purpose", "Non-Working Spouse"),
            required_when_shown=True,
        ),
        _field(
            "spouse_member_ss_number",
            "Member spouse's SS Number",
            "Enter the 10-digit SS Number SSS already issued to your spouse. OneGov PH does not create it.",
            required=False,
            max_length=14,
            section=purpose,
            show_when=("registration_purpose", "Non-Working Spouse"),
            required_when_shown=True,
        ),
        _field(
            "mysss_user_id",
            "Preferred My.SSS user ID",
            "Enter 6 to 20 letters or numbers. SSS checks whether it is available. OneGov PH does not reserve it or ask for the My.SSS password.",
            max_length=20,
            section=purpose,
        ),
        _field("height_cm", "Height (cm)", "Enter your height in centimeters.", max_length=6, section=purpose),
        _field("weight_kg", "Weight (kg)", "Enter your weight in kilograms.", max_length=6, section=purpose),
        _field(
            "beneficiaries",
            "Beneficiaries",
            "Add a father, mother, child, or other eligible beneficiary when one applies. A spouse can be added only when your civil status is Married. You can add up to 10 beneficiaries.",
            field_type="beneficiaries",
            required=False,
            options=SSS_BENEFICIARY_RELATIONSHIPS,
            section=benefits,
        ),
        _field(
            "has_primary_id",
            "Can you provide a primary government ID?",
            "Choose Yes if you can upload one primary ID from the SSS list. Choose No only when you cannot provide a primary ID and will upload two alternative documents instead.",
            field_type="select",
            options=(SSS_HAS_PRIMARY_YES, SSS_HAS_PRIMARY_NO),
            section=identification,
            placeholder="Select an answer",
        ),
    ]
    documents = (
        _sss_document(
            "valid_id",
            "Section A: Primary identification",
            "Choose one primary ID (Driver’s License, Philippine Passport, PhilSys National ID / ePhilID, PRC ID, UMID Card, or Seaman’s Book), then upload a clear PDF or photo of that same ID.",
            required_when=primary_yes,
            id_choices="sss",
            status_label="Required",
        ),
        _sss_document(
            "alt_id_1",
            "Section B: Alternative identification — first document",
            "Shown only when you cannot provide a primary ID. Upload the first of two alternative documents (for example Barangay ID, NBI Clearance, School ID, Birth Certificate, TIN ID, or Police Clearance).",
            required_when=primary_no,
            id_choices="sss_alt",
            status_label="Required",
        ),
        _sss_document(
            "alt_id_2",
            "Section B: Alternative identification — second document",
            "Upload a second alternative document that differs from the first. Common pairs: Barangay ID + NBI Clearance, School ID + Birth Certificate, or TIN ID + Police Clearance.",
            required_when=primary_no,
            id_choices="sss_alt",
            status_label="Required",
        ),
    )
    return {
        "kind": "sss",
        "kicker": "Social Security assistance",
        "department_label": "Social Security System (SSS)",
        "service_title": "SS Number Registration Assistance and Tracking",
        "process": SSS_DESCRIPTION,
        "disclaimer": SSS_NOTICE,
        "fee_note": SSS_FEE_NOTE,
        "fields": fields,
        "documents": documents,
        "document_note": (
            "Section A accepts one primary government ID. "
            "Section B appears only when you cannot provide a primary ID, and then two alternative documents are required. "
            "Files saved here are not submitted to SSS."
        ),
        "upload_intro": (
            "Upload a clear PDF or photo of each required identification document. "
            "OneGov PH stores the copy you choose. It is not submitted to SSS."
        ),
        "upload_accept": ".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png",
        "reference_label": "OneGov PH reference number",
        "private_keys": SSS_PRIVATE_KEYS,
        "official_url": SSS_URL,
        "official_heading": "Official SSS registration",
        "official_action": "Continue to Official SSS Registration",
        "official_text": (
            "Finish the registration on the SSS website. SSS verifies the registrant, checks the email address, "
            "validates the information, generates the SS Number, and receives the supporting document."
        ),
        "show_submitted_details": True,
        "step_labels": (
            "1. Application details",
            "2. Documents",
            "3. Review",
            "4. Payment",
            "5. Confirmation",
        ),
        "payment_after_review": True,
        "submit_label": "Continue to payment",
        "confirmation_step": 5,
        "reminders": [
            "An SS Number is issued once. Do not start a second registration if SSS already issued one to you.",
            "OneGov PH does not generate an SS Number, assign a number, or send this form to SSS.",
            "Upload one primary ID when you have one. Otherwise upload two alternative documents.",
        ],
        "terms": (
            "I certify that the information and documents I provided are accurate and complete to the best of my knowledge. "
            + SSS_NOTICE
        ),
        "submit_event": (
            "SSS request saved for assistance and tracking. "
            "No payment was required. "
            "SSS has not received this as an official filing, and OneGov PH has not issued an SS Number."
        ),
        "submit_notice": (
            "Your SSS request {reference} was submitted in OneGov PH. "
            "No payment was collected. Continue on the official SSS website. "
            "OneGov PH has not generated an SS Number."
        ),
        "next_steps": [
            "Open the official SSS registration page and complete every SSS step there, including email verification.",
            "Keep the OneGov PH reference number. It is not an SS Number or an SSS transaction number.",
            "When SSS gives you an SS Number, a transaction number, or the E-1/E-6 form, record those details here.",
            "Opening the SSS website does not change the OneGov PH status.",
        ],
        "status_labels": {
            "not_applicable": "Not applicable",
            "submitted": "Awaiting official SSS registration",
            "under_review": "Official registration recorded",
        },
        "recorded_statuses": SSS_RECORDED_STATUSES,
        "document_statuses": SSS_DOCUMENT_STATUSES,
        "file_rules": SSS_FILE_RULES,
    }



def specification_for(service, values=None):
    """Return the form for a catalog service, or None when Apply now is not available."""
    from app.services.philsys_national_id import SERVICE_NAMES, specification

    if service.service_name in SERVICE_NAMES:
        return specification(values or {})
    spec = SERVICE_FORMS.get(service.service_name)
    if spec is None:
        return None
    if spec.get("compose") == "birth":
        return compose_birth_certificate(values or {})
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
        "service_title",
        "step_labels",
        "confirmation_step",
        "status_labels",
        "submit_event",
        "submit_notice",
        "next_steps",
        "reminders",
        "documents_first",
        "type_first",
        "review_before_schedule",
        "review_back",
        "submit_label",
        "terms",
        "fee_note",
        "payment_after_review",
        "online_payment_only",
    ):
        if spec.get(extra):
            result[extra] = spec[extra]
    return result


def applicable_service_names():
    from app.services.philsys_national_id import SERVICE_NAMES

    names = set(SERVICE_FORMS)
    names.update(SERVICE_NAMES)
    return frozenset(names)
