"""Accepted identification documents for SSS assistance and tracking uploads."""


def _item(key, label, markers=()):
    return {"key": key, "label": label, "markers": markers}


SSS_PRIMARY_IDS = (
    _item(
        "drivers_license",
        "Driver's License",
        ("DRIVER'S LICENSE", "DRIVERS LICENSE", "DRIVER LICENSE", "LAND TRANSPORTATION"),
    ),
    _item(
        "passport",
        "Philippine Passport",
        ("PASSPORT", "PHILIPPINE PASSPORT", "DEPARTMENT OF FOREIGN AFFAIRS"),
    ),
    _item(
        "philsys_national_id",
        "PhilSys National ID / ePhilID",
        ("PHILIPPINE IDENTIFICATION", "PHILID", "EPHILID", "NATIONAL ID", "PHILSYS"),
    ),
    _item(
        "prc_id",
        "PRC ID",
        ("PROFESSIONAL REGULATION COMMISSION", "PRC ID", "PRC"),
    ),
    _item(
        "umid",
        "UMID Card",
        ("UNIFIED MULTI-PURPOSE", "UNIFIED MULTIPURPOSE", "UMID"),
    ),
    _item(
        "seamans_book",
        "Seaman's Book",
        ("SEAMAN", "SEAFARER", "SID", "SEAMAN'S BOOK", "SEAMANS BOOK"),
    ),
)

SSS_ALTERNATIVE_IDS = (
    _item("barangay_id", "Barangay ID", ("BARANGAY", "BARANGAY ID")),
    _item("nbi_clearance", "NBI Clearance", ("NBI", "NATIONAL BUREAU OF INVESTIGATION", "CLEARANCE")),
    _item("school_id", "School ID", ("SCHOOL ID", "STUDENT ID", "UNIVERSITY", "COLLEGE")),
    _item(
        "birth_certificate",
        "Birth Certificate",
        ("CERTIFICATE OF LIVE BIRTH", "LIVE BIRTH", "BIRTH CERTIFICATE"),
    ),
    _item("tin_id", "TIN ID", ("TIN", "TAXPAYER", "BUREAU OF INTERNAL REVENUE", "BIR")),
    _item("police_clearance", "Police Clearance", ("POLICE CLEARANCE", "PNP", "POLICE")),
)

_PRIMARY = {item["key"]: item for item in SSS_PRIMARY_IDS}
_ALTERNATIVE = {item["key"]: item for item in SSS_ALTERNATIVE_IDS}
_ALL = {**_PRIMARY, **_ALTERNATIVE}


def sss_primary_groups():
    return [{"title": "Primary identification", "items": list(SSS_PRIMARY_IDS)}]


def sss_alternative_groups():
    return [{"title": "Alternative identification", "items": list(SSS_ALTERNATIVE_IDS)}]


def sss_id_by_key(key, pool="primary"):
    table = _PRIMARY if pool == "primary" else _ALTERNATIVE if pool == "alternative" else _ALL
    return table.get(str(key or "").strip())


def _compact(value):
    return "".join(character for character in (value or "").upper() if character.isalnum())


def _marker_hit(text, marker):
    return _compact(marker) in _compact(text)


def check_sss_id_text(id_key, text, pool="primary"):
    """Return an error when the visible words do not match the selected ID."""
    selected = sss_id_by_key(id_key, pool=pool)
    if selected is None:
        return "Select one identification document from the list."
    readable = " ".join((text or "").split())
    if len(_compact(readable)) < 4:
        return (
            "The words on this file could not be read. Upload a clearer, straight PDF or photo "
            "of the full ID, with its title visible."
        )
    if any(_marker_hit(readable, marker) for marker in selected["markers"]):
        return None
    return (
        f"This file does not look like {selected['label']}. "
        "Upload a clearer copy of that ID, with its title visible."
    )
