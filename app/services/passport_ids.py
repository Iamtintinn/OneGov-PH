"""Valid IDs for the DFA passport documents step. The text check is not DFA acceptance."""

import re
from datetime import date, datetime


def _item(key, label, markers):
    return {"key": key, "label": label, "markers": markers}


# Titles printed on these cards. The check looks for these words.
_CORE = (
    _item(
        "philid",
        "Philippine Identification (PhilID / National ID)",
        ("PHILIPPINE IDENTIFICATION", "PHILID", "NATIONAL ID", "PHILSYS"),
    ),
    _item(
        "ephilid",
        "Electronic Philippine Identification (ePhilID)",
        ("EPHILID", "ELECTRONIC PHILIPPINE IDENTIFICATION", "ELECTRONIC PHILID"),
    ),
    _item(
        "digital_national_id",
        "Digital National ID (Printed Copy)",
        ("DIGITAL NATIONAL ID", "DIGITAL PHILIPPINE IDENTIFICATION", "DIGITAL PHILID"),
    ),
    _item("sss_id", "Social Security System (SSS) ID / Card", ("SOCIAL SECURITY SYSTEM", "SSS ID", "SSS")),
    _item(
        "gsis_id",
        "Government Service Insurance System (GSIS) ID / Card",
        ("GOVERNMENT SERVICE INSURANCE", "GSIS ID", "GSIS"),
    ),
    _item("umid", "Unified Multi-Purpose ID (UMID)", ("UNIFIED MULTI-PURPOSE", "UNIFIED MULTIPURPOSE", "UMID")),
    _item(
        "drivers_license",
        "LTO Driver's License",
        ("DRIVER'S LICENSE", "DRIVERS LICENSE", "DRIVER LICENSE", "LAND TRANSPORTATION"),
    ),
    _item("student_permit", "LTO Student Permit (Card Format Only)", ("STUDENT PERMIT", "STUDENT'S PERMIT")),
    _item("prc_id", "Professional Regulation Commission (PRC) ID", ("PROFESSIONAL REGULATION COMMISSION", "PRC ID", "PRC")),
    _item("owwa_id", "Overseas Workers Welfare Administration (OWWA) E-Card", ("OVERSEAS WORKERS WELFARE", "OWWA")),
    _item("voters_id", "COMELEC Voter's ID", ("VOTER'S ID", "VOTERS ID", "VOTER'S IDENTIFICATION", "COMELEC")),
    _item(
        "voters_certificate",
        "COMELEC Voter's Certificate (Issued by COMELEC Main Office)",
        ("VOTER'S CERTIFICATE", "VOTERS CERTIFICATE", "VOTER'S CERTIFICATION", "VOTERS CERTIFICATION"),
    ),
    _item("senior_id", "Senior Citizen ID", ("SENIOR CITIZEN", "OSCA")),
    _item(
        "postal_id",
        "Philippine Postal ID (Issued November 2016 onwards)",
        ("POSTAL ID", "POSTAL IDENTITY", "PHILPOST", "PHILIPPINE POSTAL"),
    ),
    _item(
        "marina_srb",
        "MARINA Seafarer's Record Book (SRB)",
        ("SEAFARER'S RECORD BOOK", "SEAFARERS RECORD BOOK", "RECORD BOOK", "MARINA"),
    ),
    _item(
        "marina_sid",
        "MARINA Seafarer's Identity Document (SID)",
        ("SEAFARER'S IDENTITY DOCUMENT", "SEAFARERS IDENTITY DOCUMENT", "SEAFARER'S IDENTITY"),
    ),
    _item("airman_license", "Airman License (Issued August 2016 onwards)", ("AIRMAN LICENSE", "AIRMAN")),
    _item(
        "ptcfor",
        "PNP Permit to Carry Firearms Outside Residence",
        ("PERMIT TO CARRY", "FIREARMS OUTSIDE RESIDENCE", "PTCFOR"),
    ),
)
_RENEWAL = (
    _item("philippine_passport", "Valid or Latest Philippine Passport", ("PASSPORT", "PHILIPPINE PASSPORT", "DEPARTMENT OF FOREIGN AFFAIRS")),
)
_MINOR = (
    _item("school_id", "School ID", ("SCHOOL ID", "STUDENT ID", "UNIVERSITY", "COLLEGE", "ACADEMY")),
    _item(
        "enrollment_certificate",
        "Certificate of Enrollment with Photo (with school's dry seal, if no School ID)",
        ("CERTIFICATE OF ENROLLMENT", "CERTIFICATE OF REGISTRATION", "ENROLLMENT CERTIFICATE"),
    ),
)
_ALL = {item["key"]: item for item in _CORE + _RENEWAL + _MINOR}
# A more specific card can also contain the shorter title. Prefer the specific card.
_MORE_SPECIFIC = {
    "philid": ("ephilid", "digital_national_id"),
    "sss_id": ("umid",),
    "gsis_id": ("umid",),
    "drivers_license": ("student_permit",),
    "voters_id": ("voters_certificate",),
    "marina_srb": ("marina_sid",),
    "school_id": ("enrollment_certificate",),
}
def _born(value):
    text = str(value or "").strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def is_minor(date_of_birth, today=None):
    """A passport applicant under 18 can use a school ID or enrollment certificate."""
    born = _born(date_of_birth)
    if born is None:
        return False
    today = today or date.today()
    years = today.year - born.year
    if (today.month, today.day) < (born.month, born.day):
        years -= 1
    return years < 18


def passport_id_groups(application_type=None, date_of_birth=None):
    """IDs this applicant may select. School ID options stay listed for every applicant."""
    from app.services.passport_requirements import is_passport_renewal_type, normalize_passport_type

    groups = [{"title": "Valid government IDs", "items": list(_CORE)}]
    app_type = normalize_passport_type(application_type)
    # Include latest-passport options for renewals and related non-first-time types.
    if not app_type or is_passport_renewal_type(app_type) or app_type == "Renewal":
        groups.append({"title": "For renewal and replacement applicants", "items": list(_RENEWAL)})
    groups.append({"title": "For minor applicants", "items": list(_MINOR)})
    return groups


def passport_id_by_key(application_type, date_of_birth, key):
    selected = _ALL.get(str(key or "").strip())
    if selected is None:
        return None
    allowed = {item["key"] for group in passport_id_groups(application_type, date_of_birth) for item in group["items"]}
    if selected["key"] not in allowed:
        return None
    return selected


_MONTHS = {
    "JAN": 1,
    "JANUARY": 1,
    "FEB": 2,
    "FEBRUARY": 2,
    "MAR": 3,
    "MARCH": 3,
    "APR": 4,
    "APRIL": 4,
    "MAY": 5,
    "JUN": 6,
    "JUNE": 6,
    "JUL": 7,
    "JULY": 7,
    "AUG": 8,
    "AUGUST": 8,
    "SEP": 9,
    "SEPT": 9,
    "SEPTEMBER": 9,
    "OCT": 10,
    "OCTOBER": 10,
    "NOV": 11,
    "NOVEMBER": 11,
    "DEC": 12,
    "DECEMBER": 12,
}


def _clean_person_name(value):
    text = re.sub(r"[^A-Za-zÑñ'’.\-\s]", " ", value or "")
    text = re.sub(r"\s+", " ", text).strip(" .'-")
    if len(text) < 2:
        return ""
    return " ".join(part.capitalize() for part in text.split())


def _iso_date(year, month, day):
    try:
        year = int(year)
        month = int(month)
        day = int(day)
        parsed = date(year, month, day)
    except (TypeError, ValueError):
        return ""
    if parsed.year < 1900 or parsed > date.today():
        return ""
    return parsed.isoformat()


def _extract_date_of_birth(text):
    upper = text.upper()
    labeled = re.search(
        r"(?:DATE OF BIRTH|BIRTH DATE|BIRTHDAY|DOB|BIRTH)\s*[:\-]?\s*"
        r"([0-3]?\d[\/\-.][01]?\d[\/\-.](?:19|20)\d{2}|"
        r"(?:19|20)\d{2}[\/\-.][01]?\d[\/\-.][0-3]?\d|"
        r"[0-3]?\d\s+[A-Z]{3,9}\s+(?:19|20)\d{2}|"
        r"[A-Z]{3,9}\s+[0-3]?\d,?\s+(?:19|20)\d{2})",
        upper,
    )
    candidates = []
    if labeled:
        candidates.append(labeled.group(1))
    candidates.extend(
        match.group(0)
        for match in re.finditer(
            r"\b([0-3]?\d)[\/\-.]([01]?\d)[\/\-.]((?:19|20)\d{2})\b",
            upper,
        )
    )
    candidates.extend(
        match.group(0)
        for match in re.finditer(
            r"\b((?:19|20)\d{2})[\/\-.]([01]?\d)[\/\-.]([0-3]?\d)\b",
            upper,
        )
    )
    candidates.extend(
        match.group(0)
        for match in re.finditer(
            r"\b([0-3]?\d)\s+([A-Z]{3,9})\s+((?:19|20)\d{2})\b",
            upper,
        )
    )
    candidates.extend(
        match.group(0)
        for match in re.finditer(
            r"\b([A-Z]{3,9})\s+([0-3]?\d),?\s+((?:19|20)\d{2})\b",
            upper,
        )
    )
    for raw in candidates:
        value = str(raw).strip(" :-")
        slash = re.fullmatch(r"([0-3]?\d)[\/\-.]([01]?\d)[\/\-.]((?:19|20)\d{2})", value)
        if slash:
            iso = _iso_date(slash.group(3), slash.group(2), slash.group(1))
            if iso:
                return iso
        ymd = re.fullmatch(r"((?:19|20)\d{2})[\/\-.]([01]?\d)[\/\-.]([0-3]?\d)", value)
        if ymd:
            iso = _iso_date(ymd.group(1), ymd.group(2), ymd.group(3))
            if iso:
                return iso
        dmon = re.fullmatch(r"([0-3]?\d)\s+([A-Z]{3,9})\s+((?:19|20)\d{2})", value)
        if dmon and dmon.group(2) in _MONTHS:
            iso = _iso_date(dmon.group(3), _MONTHS[dmon.group(2)], dmon.group(1))
            if iso:
                return iso
        mon = re.fullmatch(r"([A-Z]{3,9})\s+([0-3]?\d),?\s+((?:19|20)\d{2})", value)
        if mon and mon.group(1) in _MONTHS:
            iso = _iso_date(mon.group(3), _MONTHS[mon.group(1)], mon.group(2))
            if iso:
                return iso
    return ""


def _extract_sex(text):
    upper = text.upper()
    labeled = re.search(r"\b(?:SEX|GENDER)\s*[:\-]?\s*(F(?:EMALE)?|M(?:ALE)?)\b", upper)
    if labeled:
        token = labeled.group(1)
        return "Female" if token.startswith("F") else "Male"
    if re.search(r"\bFEMALE\b", upper):
        return "Female"
    if re.search(r"\bMALE\b", upper):
        return "Male"
    return ""


def _extract_names(text):
    """Pull name parts from common Philippine ID layouts when labels are readable."""
    compact_lines = [re.sub(r"\s+", " ", line).strip() for line in (text or "").splitlines()]
    compact_lines = [line for line in compact_lines if line]
    joined = "\n".join(compact_lines)
    upper = joined.upper()

    last = first = middle = ""

    last_match = re.search(
        r"(?:LAST\s*NAME|SURNAME|FAMILY\s*NAME)\s*[:\-]?\s*([A-ZÑ][A-ZÑ'’.\- ]{1,60})",
        upper,
    )
    first_match = re.search(
        r"(?:FIRST\s*NAME|GIVEN\s*NAME(?:S)?)\s*[:\-]?\s*([A-ZÑ][A-ZÑ'’.\- ]{1,60})",
        upper,
    )
    middle_match = re.search(
        r"(?:MIDDLE\s*NAME|M\.?\s*I\.?|MIDDLE\s*INITIAL)\s*[:\-]?\s*([A-ZÑ][A-ZÑ'’.\- ]{0,60})",
        upper,
    )
    if last_match:
        last = _clean_person_name(last_match.group(1).split("  ")[0])
    if first_match:
        first = _clean_person_name(first_match.group(1).split("  ")[0])
    if middle_match:
        middle = _clean_person_name(middle_match.group(1).split("  ")[0])

    if not (last and first):
        full = re.search(
            r"(?:FULL\s*NAME|NAME)\s*[:\-]?\s*([A-ZÑ][A-ZÑ'’.\- ]+,\s*[A-ZÑ][A-ZÑ'’.\- ]+)",
            upper,
        )
        if full:
            left, right = [part.strip() for part in full.group(1).split(",", 1)]
            last = last or _clean_person_name(left)
            parts = _clean_person_name(right).split()
            if parts and not first:
                first = parts[0]
            if len(parts) > 1 and not middle:
                middle = " ".join(parts[1:])
        else:
            comma = re.search(
                r"\b([A-ZÑ]{2,}(?:\s+[A-ZÑ]{2,})?),\s*([A-ZÑ]{2,}(?:\s+[A-ZÑ]{2,}){0,3})\b",
                upper,
            )
            if comma:
                last = last or _clean_person_name(comma.group(1))
                parts = _clean_person_name(comma.group(2)).split()
                if parts and not first:
                    first = parts[0]
                if len(parts) > 1 and not middle:
                    middle = " ".join(parts[1:])

    result = {}
    if first:
        result["first_name"] = first
    if middle:
        result["middle_name"] = middle
    if last:
        result["last_name"] = last
    return result


def _extract_address(text):
    match = re.search(
        r"(?:ADDRESS|RESIDENCE|PRESENT\s+ADDRESS)\s*[:\-]?\s*(.+)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    value = re.sub(r"\s+", " ", match.group(1)).strip(" :-")
    value = re.split(
        r"\b(?:DATE OF BIRTH|SEX|GENDER|CIVIL STATUS|NATIONALITY|BLOOD|HEIGHT|WEIGHT)\b",
        value,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" :-")
    if len(value) < 8:
        return ""
    return value[:500]


def _extract_nationality(text):
    match = re.search(
        r"(?:NATIONALITY|CITIZENSHIP)\s*[:\-]?\s*([A-Za-zÑñ ]{3,40})",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    value = _clean_person_name(match.group(1))
    return value[:160]


def _extract_civil_status(text):
    match = re.search(
        r"(?:CIVIL\s*STATUS|STATUS)\s*[:\-]?\s*(SINGLE|MARRIED|WIDOWED|SEPARATED|DIVORCED)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    return match.group(1).capitalize()


def extract_id_fields(text):
    """Best-effort personal fields from OCR text. Missing values stay blank."""
    readable = " ".join((text or "").split())
    if len(readable) < 4:
        return {}
    fields = {}
    fields.update(_extract_names(text))
    dob = _extract_date_of_birth(text)
    if dob:
        fields["date_of_birth"] = dob
    sex = _extract_sex(text)
    if sex:
        fields["sex"] = sex
    civil = _extract_civil_status(text)
    if civil:
        fields["civil_status"] = civil
    nationality = _extract_nationality(text)
    if nationality:
        fields["nationality"] = nationality
    address = _extract_address(text)
    if address:
        fields["address"] = address
    return fields


def _compact(value):
    return "".join(character for character in (value or "").upper() if character.isalnum())


def _marker_hit(text, marker):
    compact_text = _compact(text)
    compact_marker = _compact(marker)
    if compact_marker == "PHILID":
        return "PHILID" in compact_text and "EPHILID" not in compact_text
    if compact_marker == "SSS":
        return "SSS" in compact_text and "UMID" not in compact_text
    if compact_marker == "GSIS":
        return "GSIS" in compact_text and "UMID" not in compact_text
    return compact_marker in compact_text


def _matched_keys(text):
    found = []
    for item in _ALL.values():
        if any(_marker_hit(text, marker) for marker in item["markers"]):
            found.append(item["key"])
    return found


def check_passport_id_text(id_key, text):
    """Return an error when the visible words do not match the selected ID."""
    selected = _ALL.get(id_key)
    if selected is None:
        return "Select one valid government ID from the list."
    readable = " ".join((text or "").split())
    if len(_compact(readable)) < 4:
        return (
            "The words on this file could not be read. Upload a clearer, straight PDF or photo "
            "of the full ID, with its title visible."
        )
    found = _matched_keys(readable)
    if id_key in found:
        specific = next((key for key in _MORE_SPECIFIC.get(id_key, ()) if key in found), None)
        if specific is not None:
            other = _ALL[specific]["label"]
            return (
                f"This file looks like {other}, not {selected['label']}. "
                "Select the matching ID, or upload a clear copy of the ID you selected."
            )
        return None
    if found:
        other = _ALL[found[0]]["label"]
        return (
            f"This file looks like {other}, not {selected['label']}. "
            "Select the matching ID, or upload a clear copy of the ID you selected."
        )
    return (
        f"This file does not look like {selected['label']}. "
        "Upload a clearer copy of that ID, with its title visible."
    )
