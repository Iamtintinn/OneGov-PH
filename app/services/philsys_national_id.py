"""PhilSys National ID preparation. PSA still performs registration."""

from app.services.application_forms import _document, _field

SERVICE_NAMES = frozenset({
    "PhilSys National ID Registration Assistance",
    "National ID Tracking and Concern Management",
})

DEPARTMENT_LABEL = "Philippine Statistics Authority (PSA)"
DISCLAIMER = (
    "OneGov PH helps citizens prepare their National ID registration information and supporting documents. "
    "Official PhilSys registration, identity verification, biometric capture, and National ID issuance are handled "
    "by authorized Philippine Statistics Authority registration personnel."
)
PROCESS = (
    "Prepare your National ID registration information and supporting documents in OneGov PH. "
    "An authorized PSA registration center still registers you, checks your identity, captures your biometrics, and issues the National ID."
)
REMINDERS = (
    "National ID registration is free.",
    "Submitting this request does not register you with PhilSys and does not issue a National ID.",
    "A front-facing photograph, fingerprints, and an iris scan are captured in person at an authorized registration center.",
    "You can record a PhilSys transaction reference after PSA gives you one. Saving that number does not mark you as registered.",
)
TERMS = "I confirm that the information and documents in this request are accurate. " + DISCLAIMER
FEE_NOTE = (
    "National ID registration is free. OneGov PH does not collect a fee and does not issue a National ID."
)
BIOMETRICS = (
    "These are captured personally at an authorized PhilSys registration center: a front-facing photograph, fingerprints, and an iris scan. "
    "Do not upload a photograph, fingerprint, or iris scan through OneGov PH."
)
STEP_LABELS = (
    "1. Documents",
    "2. Application details",
    "3. Review",
    "4. Scheduling",
    "5. Payment",
    "6. Confirmation",
)
NEXT_STEPS = (
    "Keep your OneGov PH reference number. It is not a PhilSys transaction number.",
    "Attend the demonstration registration appointment you scheduled, then complete identity verification and biometrics at an authorized PSA center.",
    "Do not send biometric data through OneGov PH.",
    "Registration at the center is free. OneGov PH has not registered you with PhilSys.",
    "When PSA gives you a transaction reference, save it on this request. Saving it does not change your status to Registered.",
)

_SEX = ("Female", "Male")
_BLOOD = ("Unknown", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
_MARITAL = ("Single", "Married", "Widowed", "Separated", "Divorced")
_CITIZENSHIP = ("Filipino Citizen", "Resident Alien")
_BIRTH_RECORD_KEYS = frozenset({
    "psa_birth_certificate",
    "birth_bren",
    "lcro_birth",
    "report_of_birth",
    "foundling_certificate",
})

_PRIMARY_ALT = "Any other primary document. If you have none, a secondary document may be used instead."
_SECONDARY_ALT = "Use a secondary document only when you cannot present a primary document."
_CONDITIONAL_ALT = (
    "These count only when you have no primary document, and only when the ID shows the details PSA requires."
)


def _doc(key, label, description, requirement, alternatives, instructions):
    return {
        "key": key,
        "label": label,
        "description": description,
        "requirement": requirement,
        "alternatives": alternatives,
        "instructions": instructions,
    }


def is_resident_alien(citizenship):
    return (citizenship or "").casefold() == "resident alien"


def fields():
    """Demographic details for registration preparation. Biometrics are not collected here."""
    personal = "Personal information"
    address = "Address information"
    contact = "Contact information"
    reference = "PhilSys transaction reference"
    return (
        _field("first_name", "First name", "Enter your first name as it should appear for registration.", max_length=80, section=personal),
        _field(
            "middle_name",
            "Middle name",
            "Leave this blank if you have no middle name.",
            required=False,
            max_length=80,
            section=personal,
        ),
        _field("last_name", "Last name", "Enter your last name as it should appear for registration.", max_length=80, section=personal),
        _field("sex", "Sex", "Select Female or Male.", field_type="select", options=_SEX, section=personal),
        _field(
            "date_of_birth",
            "Date of birth",
            "Use the date of birth on your birth record. A future date is not accepted.",
            field_type="date",
            section=personal,
        ),
        _field(
            "place_of_birth",
            "Place of birth",
            "Enter the city or municipality and province. If you were born abroad, enter the place shown on your birth record.",
            max_length=160,
            section=personal,
        ),
        _field(
            "blood_type",
            "Blood type",
            "Select your blood type. Choose Unknown if you do not know it.",
            field_type="select",
            options=_BLOOD,
            section=personal,
        ),
        _field(
            "citizenship",
            "Citizenship status",
            "Choose Filipino Citizen or Resident Alien. This chooses which supporting identification documents apply.",
            field_type="select",
            options=_CITIZENSHIP,
            section=personal,
        ),
        _field(
            "marital_status",
            "Marital status",
            "Optional. Leave this blank if you will confirm it at the registration center.",
            field_type="select",
            required=False,
            options=_MARITAL,
            section=personal,
        ),
        _field(
            "permanent_address",
            "Permanent address",
            "Enter your permanent house or building, street, barangay, city or municipality, and province.",
            field_type="textarea",
            max_length=500,
            section=address,
        ),
        _field(
            "present_address",
            "Present address",
            "Optional. Enter your present address only if it is different from your permanent address.",
            field_type="textarea",
            required=False,
            max_length=500,
            section=address,
        ),
        _field(
            "mobile_number",
            "Mobile number",
            "Optional. Enter a Philippine mobile number, such as 09171234567, if you want the center to use it.",
            field_type="tel",
            required=False,
            max_length=16,
            section=contact,
        ),
        _field(
            "email",
            "Email address",
            "Optional. Enter an email address you can open. Status messages are also shown in OneGov PH.",
            field_type="email",
            required=False,
            max_length=255,
            section=contact,
        ),
        _field(
            "philsys_reference",
            "PhilSys transaction reference number",
            "Optional. Enter this only after PSA gives you a transaction reference. OneGov PH does not create this number, and saving it does not mean you are registered.",
            required=False,
            max_length=40,
            section=reference,
        ),
    )


def filipino_groups():
    """Supporting documents published at philsys.gov.ph/supporting-documents/."""
    primary = "Primary — bring any one"
    paired = "Primary — bring with the other item in this pair, or choose another primary document"
    secondary = "Secondary — only if you have no primary document"
    conditional = "Secondary — only if you have no primary document and the ID shows the details PSA requires"
    bring = "Bring the original to the registration center. OneGov PH does not check this document."
    return (
        {
            "title": "Primary supporting documents",
            "intro": (
                "PSA asks you to bring the original of any one primary document. "
                "The birth certificate counts as primary only when you also bring one government-issued ID "
                "with your full name, a front-facing photo, and your signature or thumb mark. "
                "If those two records disagree, PSA uses the birth certificate. "
                "A passport, UMID, or LTO student or driver's license can be used instead of that pair."
            ),
            "items": (
                _doc(
                    "psa_birth_certificate",
                    "PSA-issued Certificate of Live Birth",
                    "The civil registry birth certificate issued by the Philippine Statistics Authority.",
                    paired,
                    "Philippine passport or ePassport, UMID, or an LTO student or driver's license.",
                    bring + " If you use this, also bring one government-issued photo ID.",
                ),
                _doc(
                    "government_id",
                    "Government-issued identification document",
                    "An ID with your full name, a front-facing photograph, and your signature or thumb mark.",
                    paired,
                    "Philippine passport or ePassport, UMID, or an LTO student or driver's license.",
                    bring + " Present this together with the PSA birth certificate.",
                ),
                _doc(
                    "passport",
                    "Philippine Passport or ePassport",
                    "Issued by the Department of Foreign Affairs.",
                    primary,
                    _PRIMARY_ALT,
                    bring,
                ),
                _doc(
                    "umid",
                    "Unified Multi-purpose Identification (UMID) Card",
                    "Issued by the GSIS or the SSS.",
                    primary,
                    _PRIMARY_ALT,
                    bring,
                ),
                _doc(
                    "drivers_license",
                    "LTO student license or driver's license",
                    "A student's license permit, or a non-professional or professional driver's license issued by the LTO.",
                    primary,
                    _PRIMARY_ALT,
                    bring,
                ),
            ),
        },
        {
            "title": "Secondary supporting documents",
            "intro": (
                "Use this list only when you cannot present a primary document. "
                "Bring the original of one accepted secondary document. "
                "A person who has none of the accepted documents may still be registered by PSA through a qualified introducer. "
                "OneGov PH cannot assign or verify an introducer."
            ),
            "items": (
                _doc("birth_bren", "PSA or NSO Certificate of Live Birth with Birth Reference Number", "A PSA-issued birth certificate, or an NSO-issued birth certificate that shows the birth reference number (BreN).", secondary, _SECONDARY_ALT, bring),
                _doc("lcro_birth", "LCRO-issued Certificate of Live Birth", "Issued by the Local Civil Registry Office.", secondary, _SECONDARY_ALT, bring),
                _doc("report_of_birth", "PSA-issued Report of Birth", "The PSA report of birth for a Filipino born abroad.", secondary, _SECONDARY_ALT, bring),
                _doc("foundling_certificate", "PSA-issued Certificate of Foundling", "The PSA certificate issued for a foundling.", secondary, _SECONDARY_ALT, bring),
                _doc("ibp_id", "Integrated Bar of the Philippines ID", "Identification card issued by the Integrated Bar of the Philippines.", secondary, _SECONDARY_ALT, bring),
                _doc("prc_id", "PRC ID", "Identification card issued by the Professional Regulation Commission.", secondary, _SECONDARY_ALT, bring),
                _doc("seamans_book", "Seaman's Book", "Seafarer's Record Book.", secondary, _SECONDARY_ALT, bring),
                _doc("owwa_id", "OWWA ID", "Issued by the Overseas Workers Welfare Administration.", secondary, _SECONDARY_ALT, bring),
                _doc("senior_id", "Senior Citizen ID", "Issued by the Office of Senior Citizens Affairs or a local government.", secondary, _SECONDARY_ALT, bring),
                _doc("sss_id", "SSS ID", "Issued by the Social Security System.", secondary, _SECONDARY_ALT, bring),
                _doc("four_ps_id", "4Ps ID", "Pantawid Pamilyang Pilipino Program identification card.", secondary, _SECONDARY_ALT, bring),
                _doc("ltopf", "License to Own or Possess Firearms", "The firearms license itself.", secondary, _SECONDARY_ALT, bring),
                _doc("nbi_clearance", "NBI Clearance", "Issued by the National Bureau of Investigation.", secondary, _SECONDARY_ALT, bring),
                _doc("police_clearance", "Police Clearance or Police ID", "A police clearance or police identification card.", secondary, _SECONDARY_ALT, bring),
                _doc("solo_parent_id", "Solo Parent ID", "Solo parent identification card.", secondary, _SECONDARY_ALT, bring),
                _doc("pwd_id", "PWD ID", "Issued by the NCDA or its regional office, the Office of the Mayor, a DSWD office, or an organization with a Department of Health agreement.", secondary, _SECONDARY_ALT, bring),
                _doc("voters_id", "Voter's ID", "Issued by the Commission on Elections.", secondary, _SECONDARY_ALT, bring),
                _doc("postal_id", "Postal ID", "Issued by the Philippine Postal Corporation.", secondary, _SECONDARY_ALT, bring),
                _doc("tin_id", "TIN ID", "Taxpayer Identification Number card.", secondary, _SECONDARY_ALT, bring),
                _doc("philhealth_id", "PhilHealth ID", "Issued by PhilHealth.", secondary, _SECONDARY_ALT, bring),
                _doc("srrv", "Special Resident Retiree's Visa", "Issued by the Philippine Retirement Authority.", secondary, _SECONDARY_ALT, bring),
                _doc("foreign_national_id", "National ID from another country", "A national identification document issued by another country.", secondary, _SECONDARY_ALT, bring),
                _doc("foreign_residence_id", "Residence ID from another country", "A residence identification document issued by another country.", secondary, _SECONDARY_ALT, bring),
                _doc("marina_id", "MARINA professional identification card", "Issued by the Maritime Industry Authority.", secondary, _SECONDARY_ALT, bring),
                _doc("csc_eligibility", "Civil Service eligibility card", "Issued by the Civil Service Commission.", secondary, _SECONDARY_ALT, bring),
                _doc("dependent_id", "AFP or PNP dependent ID", "Dependent identification issued by the Armed Forces of the Philippines or the Philippine National Police.", secondary, _SECONDARY_ALT, bring),
                _doc("retiree_id", "PNP, AFP, or PCG retiree ID", "Retiree identification issued by the Philippine National Police, Armed Forces of the Philippines, or Philippine Coast Guard.", secondary, _SECONDARY_ALT, bring),
                _doc("conductors_license", "LTO conductor's license", "Issued by the Land Transportation Office.", secondary, _SECONDARY_ALT, bring),
                _doc("pvao_id", "PVAO pensioner's ID", "A veteran or dependent pensioner card issued by the Philippine Veterans Affairs Office.", secondary, _SECONDARY_ALT, bring),
                _doc("seafarer_id", "Seafarer's Identity Document", "Also called a seaman's ID.", secondary, _SECONDARY_ALT, bring),
                _doc("tribal_id", "Tribal certificate or ID", "Issued by the Tribal Affairs Office under the Office of the Mayor, when that applies.", secondary, _SECONDARY_ALT, bring),
                _doc("ncip_certificate", "NCIP confirmation or indigenous membership certificate", "A Certificate of Confirmation from the NCIP, or a Certificate of ICC/IP Membership issued by the tribal leader.", secondary, _SECONDARY_ALT, bring),
                _doc("ncmf_certificate", "NCMF certificate of tribal membership", "Issued by the National Commission on Muslim Filipinos.", secondary, _SECONDARY_ALT, bring),
            ),
        },
        {
            "title": "Secondary IDs accepted only with required details",
            "intro": (
                "PSA accepts these as secondary documents only when the ID has a front-facing photograph, "
                "a signature or thumb mark, your full name, your permanent address, and your date of birth. "
                "A school ID for pre-school or elementary does not need a signature or thumb mark."
            ),
            "items": (
                _doc("employee_id", "Employee ID", "An employee identification card that shows the details PSA requires.", conditional, _CONDITIONAL_ALT, bring),
                _doc("school_id", "School ID", "For pre-school or elementary, a signature or thumb mark is not required. Other school IDs still need the details PSA lists.", conditional, _CONDITIONAL_ALT, bring),
                _doc("city_id", "City or municipal ID", "Issued by a city or municipality and showing the details PSA requires.", conditional, _CONDITIONAL_ALT, bring),
                _doc("barangay_clearance", "Barangay clearance or certificate", "Accepted as a secondary document when it shows the details PSA requires.", conditional, _CONDITIONAL_ALT, bring),
                _doc("barangay_id", "Barangay ID", "A barangay identification card showing the details PSA requires.", conditional, _CONDITIONAL_ALT, bring),
                _doc("voters_certification", "Voter's certification", "Issued by the Commission on Elections.", conditional, _CONDITIONAL_ALT, bring),
                _doc("prison_record", "Prison record", "Listed by PSA with the secondary documents in this group.", conditional, _CONDITIONAL_ALT, bring),
                _doc("detention_certificate", "Certificate of detention", "Listed by PSA with the secondary documents in this group.", conditional, _CONDITIONAL_ALT, bring),
            ),
        },
    )


def resident_groups():
    """Resident-alien documents from the Revised IRR of Republic Act No. 11055."""
    requirement = "Required for a resident alien"
    return (
        {
            "title": "Resident alien supporting documents",
            "intro": (
                "The Revised IRR of Republic Act No. 11055 says a resident alien presents an Alien Certificate "
                "of Registration (ACR) or ACR ID, and a sworn certification that their stay in the Philippines "
                "was more than 180 days in total during the year before the application. "
                "PSA may ask for other documents. OneGov PH does not check these papers."
            ),
            "items": (
                _doc(
                    "acr",
                    "Alien Certificate of Registration",
                    "The ACR issued for your stay in the Philippines.",
                    requirement,
                    "ACR ID, together with the sworn certification of your length of stay.",
                    "Bring the original. Either the ACR or the ACR ID may be presented.",
                ),
                _doc(
                    "acr_id",
                    "ACR ID",
                    "The ACR identification card.",
                    requirement,
                    "Alien Certificate of Registration, together with the sworn certification of your length of stay.",
                    "Bring the original. Either the ACR or the ACR ID may be presented.",
                ),
                _doc(
                    "sworn_stay",
                    "Sworn certification of length of stay",
                    "Your sworn statement that you stayed in the Philippines for more than 180 days in total during the year before you apply.",
                    requirement,
                    "This is presented together with the ACR or ACR ID.",
                    "Bring the signed certification to the registration center.",
                ),
            ),
        },
    )


def checklist_groups(citizenship):
    if is_resident_alien(citizenship):
        return resident_groups()
    return filipino_groups()


def supporting_id_groups(citizenship):
    """Identification documents from the published list. Birth records have their own upload."""
    groups = []
    for group in checklist_groups(citizenship):
        items = tuple(item for item in group["items"] if item["key"] not in _BIRTH_RECORD_KEYS)
        if items:
            groups.append({**group, "items": items})
    return groups


def registration_documents(citizenship):
    return (
        _document(
            "supporting_id",
            "Valid supporting identification document",
            "Select the supporting ID in the list, then upload a clear PDF or photo of that same document. OneGov PH checks the visible title. This is not PSA acceptance.",
        ),
    )


def specification(values=None):
    answers = values or {}
    resident = is_resident_alien(answers.get("citizenship"))
    if resident:
        document_note = (
            "A resident alien selects the Alien Certificate of Registration or ACR ID, and can also upload the sworn certification of length of stay. "
            "OneGov PH does not capture biometrics and does not accept them as uploads."
        )
    else:
        document_note = (
            "Upload one valid supporting identification document. "
            "OneGov PH does not capture biometrics and does not accept a photograph, fingerprint, or iris scan as an upload."
        )
    return {
        "kind": "philsys",
        "kicker": "National ID assistance",
        "service_title": "PhilSys National ID Registration Assistance",
        "process": PROCESS,
        "department_label": DEPARTMENT_LABEL,
        "include_personal": False,
        "fields": fields(),
        "documents": registration_documents(answers.get("citizenship")),
        "document_note": document_note,
        "upload_intro": (
            "Upload one supporting identification document first. "
            "Citizenship chosen later may change which documents apply."
        ),
        "checklist": False,
        "reminders": REMINDERS,
        "biometrics": BIOMETRICS,
        "step_labels": STEP_LABELS,
        "fee_note": FEE_NOTE,
        "disclaimer": DISCLAIMER,
        "reference_label": "OneGov PH reference number",
        "show_submitted_details": True,
        "documents_first": True,
        "review_before_schedule": True,
        "review_back": "details",
        "submit_label": "Continue to scheduling",
        "confirmation_step": 6,
        "terms": TERMS,
        "next_steps": NEXT_STEPS,
        "submit_event": (
            "National ID preparation, demonstration appointment, and free payment step were saved for assistance and tracking. "
            "The person is not registered with PhilSys, and no National ID has been issued."
        ),
        "submit_notice": (
            "Your National ID preparation {reference} was submitted in OneGov PH. "
            "It is not PhilSys registration. Official registration, identity verification, biometric capture, and National ID issuance remain with authorized PSA personnel."
        ),
        "status_labels": {
            "submitted": "Submitted",
            "under_review": "Under review",
            "pending_documents": "Additional documents required",
            "scheduled": "Ready for registration",
            "approved": "Registered",
            "completed": "Completed",
            "cancelled": "Cancelled",
        },
    }


def document_choices(citizenship):
    """Every accepted document, in the order shown in the dropdown."""
    choices = []
    for group in checklist_groups(citizenship):
        for item in group["items"]:
            choices.append({**item, "group": group["title"]})
    return choices


def document_by_key(citizenship, key):
    return next((item for item in document_choices(citizenship) if item["key"] == key), None)


# Words that are printed on that document. The photo check looks for these words.
DOCUMENT_MARKERS = {
    "psa_birth_certificate": ("CERTIFICATE OF LIVE BIRTH", "LIVE BIRTH"),
    "government_id": (),
    "passport": ("PASSPORT",),
    "umid": ("UMID", "UNIFIED MULTI-PURPOSE", "UNIFIED MULTIPURPOSE"),
    "drivers_license": ("DRIVER'S LICENSE", "DRIVERS LICENSE", "DRIVER LICENSE", "STUDENT PERMIT", "STUDENT'S LICENSE"),
    "birth_bren": ("BIRTH REFERENCE NUMBER", "BREN", "CERTIFICATE OF LIVE BIRTH"),
    "lcro_birth": ("LOCAL CIVIL REGISTRY", "LCRO", "CERTIFICATE OF LIVE BIRTH"),
    "report_of_birth": ("REPORT OF BIRTH",),
    "foundling_certificate": ("CERTIFICATE OF FOUNDLING", "FOUNDLING"),
    "ibp_id": ("INTEGRATED BAR OF THE PHILIPPINES", "IBP"),
    "prc_id": ("PROFESSIONAL REGULATION COMMISSION", "PRC"),
    "seamans_book": ("SEAMAN'S BOOK", "SEAMANS BOOK", "SEAFARER'S RECORD", "SEAFARERS RECORD"),
    "owwa_id": ("OVERSEAS WORKERS WELFARE", "OWWA"),
    "senior_id": ("SENIOR CITIZEN", "OSCA"),
    "sss_id": ("SOCIAL SECURITY SYSTEM", "SSS"),
    "four_ps_id": ("PANTAWID PAMILYANG PILIPINO", "4PS"),
    "ltopf": ("LICENSE TO OWN", "POSSESS FIREARMS", "LTOPF"),
    "nbi_clearance": ("NATIONAL BUREAU OF INVESTIGATION", "NBI CLEARANCE"),
    "police_clearance": ("POLICE CLEARANCE", "PHILIPPINE NATIONAL POLICE"),
    "solo_parent_id": ("SOLO PARENT",),
    "pwd_id": ("PERSON WITH DISABILITY", "PWD"),
    "voters_id": ("VOTER'S ID", "VOTERS ID", "COMMISSION ON ELECTIONS"),
    "postal_id": ("POSTAL", "PHILPOST"),
    "tin_id": ("TAXPAYER IDENTIFICATION", "TIN"),
    "philhealth_id": ("PHILHEALTH",),
    "srrv": ("SPECIAL RESIDENT RETIREE", "SRRV"),
    "foreign_national_id": ("NATIONAL IDENTITY", "NATIONAL ID"),
    "foreign_residence_id": ("RESIDENCE PERMIT", "RESIDENCE ID"),
    "marina_id": ("MARITIME INDUSTRY AUTHORITY", "MARINA"),
    "csc_eligibility": ("CIVIL SERVICE COMMISSION", "ELIGIBILITY"),
    "dependent_id": ("DEPENDENT", "ARMED FORCES", "PHILIPPINE NATIONAL POLICE"),
    "retiree_id": ("RETIREE",),
    "conductors_license": ("CONDUCTOR", "LAND TRANSPORTATION"),
    "pvao_id": ("VETERANS AFFAIRS", "PVAO", "PENSIONER"),
    "seafarer_id": ("SEAFARER'S IDENTITY", "SEAFARERS IDENTITY", "SEAMAN'S ID"),
    "tribal_id": ("TRIBAL",),
    "ncip_certificate": ("INDIGENOUS PEOPLES", "NCIP", "CERTIFICATE OF CONFIRMATION"),
    "ncmf_certificate": ("MUSLIM FILIPINOS", "NCMF"),
    "employee_id": ("EMPLOYEE",),
    "school_id": ("SCHOOL", "STUDENT", "UNIVERSITY", "COLLEGE"),
    "city_id": ("CITY GOVERNMENT", "MUNICIPAL", "CITY OF"),
    "barangay_clearance": ("BARANGAY CLEARANCE", "BARANGAY CERTIFICATE"),
    "barangay_id": ("BARANGAY ID", "BARANGAY IDENTIFICATION"),
    "voters_certification": ("VOTER'S CERTIFICATION", "VOTERS CERTIFICATION"),
    "prison_record": ("PRISON",),
    "detention_certificate": ("CERTIFICATE OF DETENTION", "DETENTION"),
    "acr": ("ALIEN CERTIFICATE OF REGISTRATION",),
    "acr_id": ("ACR I-CARD", "ACR ID", "ALIEN CERTIFICATE"),
    "sworn_stay": ("SWORN", "180"),
}

# A photo of one of these can satisfy the generic "government-issued ID" choice.
GOVERNMENT_ID_KEYS = frozenset({
    "passport",
    "umid",
    "drivers_license",
    "ibp_id",
    "prc_id",
    "owwa_id",
    "senior_id",
    "sss_id",
    "four_ps_id",
    "nbi_clearance",
    "police_clearance",
    "solo_parent_id",
    "pwd_id",
    "voters_id",
    "postal_id",
    "tin_id",
    "philhealth_id",
    "marina_id",
    "csc_eligibility",
    "dependent_id",
    "retiree_id",
    "conductors_license",
    "pvao_id",
    "employee_id",
    "school_id",
    "city_id",
    "barangay_id",
    "acr",
    "acr_id",
})


def _flat_text(value):
    return "".join(character for character in (value or "").upper() if character.isalnum())


def _marker_hit(text, marker):
    return _flat_text(marker) in _flat_text(text)


def _scores(text, citizenship):
    scored = []
    for item in document_choices(citizenship):
        if item["key"] == "government_id":
            continue
        hits = [marker for marker in DOCUMENT_MARKERS.get(item["key"], ()) if _marker_hit(text, marker)]
        if hits:
            scored.append((len("".join(hits)), item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored


def check_document_text(citizenship, document_key, text):
    """Return an error when the visible words do not match the selected document."""
    selected = document_by_key(citizenship, document_key)
    if selected is None:
        return "Select a document from the list."
    readable = " ".join((text or "").split())
    if len(_flat_text(readable)) < 4:
        return (
            "The words on this photo could not be read. Upload a clearer, straight photo "
            "or PDF of the full document, with its title visible."
        )
    scored = _scores(readable, citizenship)
    best = scored[0][1] if scored else None
    if document_key == "government_id":
        if any(item["key"] in GOVERNMENT_ID_KEYS for _, item in scored):
            return None
        if best is not None:
            return (
                f"This photo looks like {best['label']}, not a government-issued identification document. "
                "Select that document in the list, or upload the ID you selected."
            )
        return (
            "This photo does not show a government-issued ID that OneGov PH can recognize. "
            "Upload a clearer photo of the ID, with its title visible."
        )
    if any(_marker_hit(readable, marker) for marker in DOCUMENT_MARKERS.get(document_key, ())):
        return None
    if best is not None:
        return (
            f"This photo looks like {best['label']}, not {selected['label']}. "
            "Select the matching document, or upload a photo of the document you selected."
        )
    return (
        f"This photo does not look like {selected['label']}. "
        "Upload a clearer photo of that document, with its title visible."
    )


def readiness_message(citizenship, saved):
    """No extra warning once a matching document photo has been stored."""
    if any(item.get("value") == "matched" for item in saved):
        return ""
    return ""
