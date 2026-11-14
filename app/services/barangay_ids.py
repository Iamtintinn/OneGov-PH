"""Accepted government IDs for Barangay Clearance / Senior / NBI valid-ID upload."""


def _item(key, label, markers=()):
    return {"key": key, "label": label, "markers": markers}


BARANGAY_ID_CHOICES = (
    _item(
        "philsys_national_id",
        "Philippine National ID (PhilSys)",
        ("PHILIPPINE IDENTIFICATION", "PHILID", "NATIONAL ID", "PHILSYS"),
    ),
    _item(
        "passport",
        "Passport",
        ("PASSPORT", "PHILIPPINE PASSPORT", "DEPARTMENT OF FOREIGN AFFAIRS"),
    ),
    _item(
        "drivers_license",
        "Driver's License",
        ("DRIVER'S LICENSE", "DRIVERS LICENSE", "DRIVER LICENSE", "LAND TRANSPORTATION"),
    ),
    _item(
        "umid",
        "UMID Card",
        ("UNIFIED MULTI-PURPOSE", "UNIFIED MULTIPURPOSE", "UMID"),
    ),
    _item(
        "sss_id",
        "SSS ID",
        ("SOCIAL SECURITY SYSTEM", "SSS ID", "SSS"),
    ),
    _item(
        "gsis_id",
        "GSIS ID",
        ("GOVERNMENT SERVICE INSURANCE", "GSIS ID", "GSIS"),
    ),
    _item(
        "prc_id",
        "PRC ID",
        ("PROFESSIONAL REGULATION COMMISSION", "PRC ID", "PRC"),
    ),
    _item(
        "postal_id",
        "Postal ID",
        ("POSTAL ID", "POSTAL IDENTITY", "PHILPOST", "PHILIPPINE POSTAL"),
    ),
    _item(
        "voters_id",
        "Voter's ID / Voter's Certification",
        (
            "VOTER'S ID",
            "VOTERS ID",
            "VOTER'S CERTIFICATE",
            "VOTERS CERTIFICATE",
            "VOTER'S CERTIFICATION",
            "COMELEC",
        ),
    ),
    _item(
        "philhealth_id",
        "PhilHealth ID",
        ("PHILHEALTH", "PHILIPPINE HEALTH INSURANCE"),
    ),
)

_BY_KEY = {item["key"]: item for item in BARANGAY_ID_CHOICES}

# Prefer a more specific ID when multiple markers appear on one file.
_MORE_SPECIFIC = {
    "sss_id": ("umid",),
    "gsis_id": ("umid",),
}


def barangay_id_groups():
    """Single searchable group used by the barangay ID picker."""
    return [{"title": "Valid government IDs", "items": list(BARANGAY_ID_CHOICES)}]


def barangay_id_by_key(key):
    return _BY_KEY.get(str(key or "").strip())


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
    if compact_marker == "PRC":
        return "PRCID" in compact_text or "PROFESSIONALREGULATION" in compact_text
    return compact_marker in compact_text


def _matched_keys(text):
    found = []
    for item in BARANGAY_ID_CHOICES:
        if any(_marker_hit(text, marker) for marker in item["markers"]):
            found.append(item["key"])
    return found


def check_barangay_id_text(id_key, text):
    """Return an error when the visible words do not match the selected ID."""
    selected = _BY_KEY.get(id_key)
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
            other = _BY_KEY[specific]["label"]
            return (
                f"This file looks like {other}, not {selected['label']}. "
                "Select the matching ID, or upload a clear copy of the ID you selected."
            )
        return None
    if found:
        other = _BY_KEY[found[0]]["label"]
        return (
            f"This file looks like {other}, not {selected['label']}. "
            "Select the matching ID, or upload a clear copy of the ID you selected."
        )
    return (
        f"This file does not look like {selected['label']}. "
        "Upload a clearer copy of that ID, with its title visible."
    )
