"""Save, validate, and submit citizen applications without calling an agency API."""

import json
import re
import secrets
from datetime import date, datetime
from pathlib import Path

from flask import current_app
from sqlalchemy import update
from werkzeug.utils import secure_filename

from app import db
from app.models.application import Application, ApplicationRequirement
from app.models.notification import Notification
from app.services.application_forms import specification_for
from app.utils.validators import clean_text, normalize_contact_number, normalize_email, validate_name

ALLOWED_EXTENSIONS = {
    ".pdf": b"%PDF",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG",
}
TERMS_TEXT = (
    "I understand that OneGov PH stores this application for assistance and tracking. "
    "Submitting it here does not file the request with the government agency. "
    "The agency may still require a visit, an appointment, or more documents."
)


def _now():
    return datetime.now().replace(microsecond=0)


def _upload_root():
    root = Path(current_app.root_path) / "instance" / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _max_bytes():
    return int(current_app.config.get("MAX_CONTENT_LENGTH") or (16 * 1024 * 1024))


def read_details(application):
    raw = {}
    if application is not None and application.application_details:
        raw = application.application_details
        if isinstance(raw, str):
            raw = json.loads(raw)
    details = {
        "fields": list(raw.get("fields") or []),
        "checklist": list(raw.get("checklist") or []),
        "id_autofill_keys": list(raw.get("id_autofill_keys") or []),
        "passport_reviewed": bool(raw.get("passport_reviewed")),
        "barangay_reviewed": bool(raw.get("barangay_reviewed")),
        "residency_reviewed": bool(raw.get("residency_reviewed")),
        "senior_reviewed": bool(raw.get("senior_reviewed")),
        "nbi_reviewed": bool(raw.get("nbi_reviewed")),
        "birth_reviewed": bool(raw.get("birth_reviewed")),
        "cenomar_reviewed": bool(raw.get("cenomar_reviewed")),
        "philsys_reviewed": bool(raw.get("philsys_reviewed")),
    }
    if raw.get("appointment"):
        details["appointment"] = raw["appointment"]
    if raw.get("confirmation"):
        details["confirmation"] = raw["confirmation"]
    if raw.get("payment"):
        details["payment"] = raw["payment"]
    return details


def write_details(application, details, commit=True):
    """Store application_details while keeping appointment and confirmation blocks."""
    payload = {
        "fields": list(details.get("fields") or []),
        "checklist": list(details.get("checklist") or []),
    }
    autofill_keys = list(details.get("id_autofill_keys") or [])
    if autofill_keys:
        payload["id_autofill_keys"] = autofill_keys
    if details.get("passport_reviewed"):
        payload["passport_reviewed"] = True
    if details.get("barangay_reviewed"):
        payload["barangay_reviewed"] = True
    if details.get("residency_reviewed"):
        payload["residency_reviewed"] = True
    if details.get("senior_reviewed"):
        payload["senior_reviewed"] = True
    if details.get("nbi_reviewed"):
        payload["nbi_reviewed"] = True
    if details.get("birth_reviewed"):
        payload["birth_reviewed"] = True
    if details.get("cenomar_reviewed"):
        payload["cenomar_reviewed"] = True
    if details.get("philsys_reviewed"):
        payload["philsys_reviewed"] = True
    if details.get("appointment"):
        payload["appointment"] = details["appointment"]
    if details.get("confirmation"):
        payload["confirmation"] = details["confirmation"]
    if details.get("payment"):
        payload["payment"] = details["payment"]
    application.application_details = payload
    application.last_updated = _now()
    if commit:
        db.session.commit()


def read_fields(application):
    return read_details(application)["fields"]


def read_checklist(application):
    return read_details(application)["checklist"]


def field_map(application):
    return {item["key"]: item.get("value") or "" for item in read_fields(application)}


def document_rules(spec, values):
    """Return document rules, including items that become required from an answer."""
    rules = []
    for document in spec["documents"]:
        required = document["required"]
        when = document.get("required_when")
        if when is not None:
            field_key, expected = when
            required = values.get(field_key) == expected
        unless = document.get("required_unless")
        if unless is not None:
            field_key, exempt_value = unless
            required = values.get(field_key) != exempt_value
        rules.append({**document, "required": required})
    return rules


def _age(born, today):
    years = today.year - born.year
    if (today.month, today.day) < (born.month, born.day):
        years -= 1
    return years


def _residency_length(started, today):
    """Describe how long someone has lived at an address, from a start date."""
    years = today.year - started.year
    months = today.month - started.month
    if today.day < started.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    parts = []
    if years > 0:
        parts.append(f"{years} year" if years == 1 else f"{years} years")
    if months > 0:
        parts.append(f"{months} month" if months == 1 else f"{months} months")
    if not parts:
        return "Less than 1 month"
    return " and ".join(parts)


def _parse_date(value, allow_future=False):
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    if parsed.year < 1900:
        return None
    if parsed > date.today():
        if not allow_future or parsed.year > date.today().year + 5:
            return None
    return parsed


def _ss_number_digits(value):
    return re.sub(r"[\s-]", "", clean_text(value))


def _measurement(value, low, high, label):
    if not re.fullmatch(r"\d{1,3}(\.\d)?", value or ""):
        return f"Enter {label} as a number."
    number = float(value)
    if not low <= number <= high:
        return f"Enter {label} from {low:g} to {high:g}."
    return None


def _beneficiaries_from_form(form, civil_status):
    from app.services.application_forms import SSS_BENEFICIARY_RELATIONSHIPS

    names = form.getlist("beneficiary_name") if hasattr(form, "getlist") else []
    relationships = form.getlist("beneficiary_relationship") if hasattr(form, "getlist") else []
    births = form.getlist("beneficiary_birth_date") if hasattr(form, "getlist") else []
    notes = form.getlist("beneficiary_note") if hasattr(form, "getlist") else []
    count = max(len(names), len(relationships), len(births), len(notes), 0)
    people = []
    messages = []
    for index in range(count):
        name = names[index] if index < len(names) else ""
        relationship = clean_text(relationships[index] if index < len(relationships) else "")
        birth = clean_text(births[index] if index < len(births) else "")
        note = clean_text(notes[index] if index < len(notes) else "")
        if not any((clean_text(name), relationship, birth, note)):
            continue
        item_errors = []
        cleaned, name_error = validate_name(name, "Beneficiary complete name", required=True, max_length=160)
        if name_error:
            item_errors.append(name_error)
        if relationship not in SSS_BENEFICIARY_RELATIONSHIPS:
            item_errors.append("Select the beneficiary relationship.")
        elif relationship == "Spouse" and civil_status != "Married":
            item_errors.append("A spouse beneficiary applies only when the civil status is Married.")
        parsed = _parse_date(birth) if birth else None
        if parsed is None:
            item_errors.append("Enter the beneficiary date of birth. A future date is not accepted.")
        if relationship == "Other eligible beneficiary" and not note:
            item_errors.append("Describe the other eligible beneficiary.")
        elif len(note) > 200:
            item_errors.append("Use no more than 200 characters for the other beneficiary information.")
        if item_errors:
            messages.append(f"Beneficiary {len(people) + 1}: " + " ".join(item_errors))
        people.append(
            {
                "name": cleaned or clean_text(name),
                "relationship": relationship,
                "birth_date": parsed.isoformat() if parsed else birth,
                "note": note,
            }
        )
    if len(people) > 10:
        messages.append("Add no more than 10 beneficiaries. SSS can collect more on the official website.")
    return json.dumps(people), " ".join(messages)


def validate_answers(service, spec, form, extra=None):
    """Validate one service form. Returns stored field rows and a map of errors."""
    from app.services.application_forms import SSS_PATH_NEW, field_is_visible

    errors = {}
    stored = []
    extra = extra or {}
    for field in spec["fields"]:
        key = field["key"]
        label = field["label"]
        if not field_is_visible(field, form):
            row = {"key": key, "label": label, "value": ""}
            if field.get("section"):
                row["section"] = field["section"]
            if field.get("step"):
                row["step"] = field["step"]
            stored.append(row)
            continue
        raw = form.get(key, "")
        if field["type"] == "hidden":
            value = clean_text(raw) or clean_text(field.get("default") or "")
            if key == "sss_path" and not value:
                value = SSS_PATH_NEW
            if key == "application_type" and not value:
                value = clean_text((extra or {}).get("application_type") or "")
        elif field["type"] == "email":
            value = normalize_email(raw)
            if field["required"] and not value:
                errors[key] = f"{label} is required."
            elif value and ("@" not in value or "." not in value.split("@")[-1] or len(value) > 255):
                errors[key] = "Enter a valid email address."
        elif field["type"] == "tel":
            value = normalize_contact_number(raw)
            digits = value[1:] if value.startswith("+") else value
            if field["required"] and not value:
                errors[key] = f"{label} is required."
            elif value and (not digits.isdigit() or not 10 <= len(digits) <= 15):
                errors[key] = "Enter a valid contact number."
            elif (
                key == "mobile_number"
                and value
                and not (
                    (len(digits) == 11 and digits.startswith("09"))
                    or (len(digits) == 12 and digits.startswith("639"))
                )
            ):
                errors[key] = "Enter a Philippine mobile number, such as 09171234567."
        elif key in {
            "first_name",
            "middle_name",
            "last_name",
            "owner_first_name",
            "owner_middle_name",
            "owner_last_name",
            "emergency_contact_name",
            "father_first_name",
            "father_middle_name",
            "father_last_name",
            "mother_first_name",
            "mother_middle_name",
            "mother_maiden_middle_name",
            "mother_maiden_last_name",
        }:
            required = field["required"]
            value, name_error = validate_name(raw, label, required=required)
            value = value or ""
            if name_error:
                errors[key] = name_error
        elif key in {"father_name", "mother_maiden_name", "requester_name", "spouse_member_name"}:
            value, name_error = validate_name(raw, label, required=field["required"], max_length=field["max_length"])
            value = value or ""
            if name_error:
                errors[key] = name_error
        elif field["type"] == "output" and key == "membership_category":
            from app.services.application_forms import SSS_CATEGORIES

            value = SSS_CATEGORIES.get(clean_text(form.get("registration_purpose", "")), "")
            if not value:
                errors[key] = "Select a purpose of registration first."
        elif field["type"] == "beneficiaries":
            civil_status = extra.get("civil_status") or clean_text(form.get("civil_status", ""))
            value, beneficiary_error = _beneficiaries_from_form(form, civil_status)
            if beneficiary_error:
                errors[key] = beneficiary_error
        elif field["type"] == "checkbox":
            value = "Yes" if form.get(key) == "yes" else ""
            if field["required"] and not value:
                errors[key] = "Confirm this statement before you continue."
        elif field["type"] == "hidden":
            value = clean_text(raw)
            if value not in field.get("options", ()):
                errors[key] = "Choose a first-time registration or an existing SS Number concern."
        elif field["type"] == "computed" and key == "length_of_residency":
            started = _parse_date(clean_text(form.get("residency_started", "")))
            value = _residency_length(started, date.today()) if started else ""
        elif field["type"] == "computed" and key == "age":
            born = _parse_date(clean_text(form.get("date_of_birth", "")))
            value = "" if born is None else f"{_age(born, date.today())} years"
        elif field["type"] == "time":
            value = clean_text(raw)
            if field["required"] and not value:
                errors[key] = f"{label} is required."
            elif value:
                parts = value.split(":")
                numbers = [part for part in parts if part.isdigit()]
                if len(parts) not in (2, 3) or len(numbers) != len(parts):
                    errors[key] = "Enter a time using hours and minutes."
                else:
                    hour, minute = int(parts[0]), int(parts[1])
                    second = int(parts[2]) if len(parts) == 3 else 0
                    if not 0 <= hour <= 23 or not 0 <= minute <= 59 or not 0 <= second <= 59:
                        errors[key] = "Enter a time using hours and minutes."
                    else:
                        value = f"{hour:02d}:{minute:02d}"
        elif field["type"] == "date":
            value = clean_text(raw)
            parsed = _parse_date(value, allow_future=bool(field.get("allow_future"))) if value else None
            if field["required"] and not value:
                errors[key] = f"{label} is required."
            elif value and parsed is None:
                errors[key] = (
                    "Enter a real appointment date."
                    if key == "appointment_date"
                    else "Enter the date you started living at this address. Use a real date that is not in the future."
                    if key == "residency_started"
                    else "Enter a real date that is not in the future."
                )
            elif (
                key == "residency_started"
                and parsed is not None
                and _parse_date(clean_text(form.get("date_of_birth", ""))) is not None
                and parsed < _parse_date(clean_text(form.get("date_of_birth", "")))
            ):
                errors[key] = "The date you started living here cannot be earlier than your date of birth."
            elif (
                key == "date_of_birth"
                and parsed is not None
                and field.get("min_age")
                and _age(parsed, date.today()) < field["min_age"]
            ):
                errors[key] = (
                    "You are not eligible to continue. A Senior Citizen ID is for a person who is 60 years old or older."
                )
        elif field["type"] == "select":
            value = clean_text(raw)
            if field["required"] and not value:
                errors[key] = f"Select a {label.lower()}."
            elif value and value not in field["options"]:
                errors[key] = f"Select a valid {label.lower()}."
        elif field["type"] == "number":
            value = clean_text(raw)
            if field["required"] and not value:
                errors[key] = f"{label} is required."
            elif key == "years_residing" and value and (not value.isdigit() or int(value) > 120):
                errors[key] = "Enter the number of years from 0 to 120. Use 0 if it is less than one year."
            elif value and (not value.isdigit() or int(value) < 0 or int(value) > 99):
                errors[key] = f"Enter a whole number for {label.lower()}."
            elif key == "copies" and value.isdigit() and not 1 <= int(value) <= 5:
                errors[key] = "Enter a number of copies from 1 to 5."
        else:
            value = clean_text(raw)
            limit = field["max_length"]
            if key in {"existing_ss_number", "spouse_member_ss_number"}:
                digits = _ss_number_digits(value)
                if field["required"] and not digits:
                    errors[key] = f"{label} is required."
                elif digits and not (digits.isdigit() and len(digits) == 10):
                    errors[key] = "Enter the 10-digit SS Number. OneGov PH does not create this number."
                else:
                    value = digits
            elif key == "mysss_user_id":
                if field["required"] and not value:
                    errors[key] = f"{label} is required."
                elif value and not re.fullmatch(r"[A-Za-z0-9]{6,20}", value):
                    errors[key] = "Enter 6 to 20 letters or numbers. Do not enter a My.SSS password."
            elif key in {"height_cm", "weight_kg"}:
                if field["required"] and not value:
                    errors[key] = f"{label} is required."
                else:
                    measure_error = (
                        _measurement(value, 50, 250, "height in centimeters")
                        if key == "height_cm"
                        else _measurement(value, 15, 300, "weight in kilograms")
                    )
                    if value and measure_error:
                        errors[key] = measure_error
            elif key == "home_zip":
                country = clean_text(form.get("country", "")).casefold()
                if not value:
                    errors[key] = "ZIP code is required."
                elif country in {"philippines", "ph"} and (not value.isdigit() or len(value) != 4):
                    errors[key] = "Enter a 4-digit ZIP code for a Philippine address."
                elif country not in {"philippines", "ph"} and not re.fullmatch(r"[A-Za-z0-9 -]{3,12}", value):
                    errors[key] = "Enter the ZIP or postal code for this country."
            elif key in {"zip_code", "postal_code"}:
                if not value:
                    errors[key] = "Postal code is required." if key == "postal_code" else "ZIP code is required."
                elif not value.isdigit() or len(value) != 4:
                    errors[key] = "Enter a 4-digit postal code." if key == "postal_code" else "Enter a 4-digit ZIP code."
            elif field["required"] and not value:
                errors[key] = f"{label} is required."
            elif len(value) > limit:
                errors[key] = f"Use no more than {limit} characters."
        row = {"key": key, "label": label, "value": value}
        if field.get("section"):
            row["section"] = field["section"]
        if field.get("step"):
            row["step"] = field["step"]
        stored.append(row)
    for field in spec["fields"]:
        if not field.get("required_when_shown") or not field_is_visible(field, form):
            continue
        if field["type"] == "checkbox":
            present = form.get(field["key"]) == "yes"
        else:
            present = bool(clean_text(form.get(field["key"], "")))
        if not present:
            errors[field["key"]] = f"{field['label']} is required."
    field_keys = {field["key"] for field in spec["fields"]}
    purpose = clean_text(form.get("registration_purpose", ""))
    if "registration_purpose" in field_keys and purpose == "Non-Working Spouse":
        civil = clean_text(form.get("civil_status", ""))
        if civil and civil != "Married":
            errors["registration_purpose"] = (
                "A non-working spouse registration is for a person who is married to an SSS member. "
                "SSS confirms eligibility on the official website."
            )
    if (
        "registration_purpose" in field_keys
        and purpose == "Overseas Filipino Worker (OFW)"
        and clean_text(form.get("citizenship", "")) == "Foreign National"
    ):
        errors["registration_purpose"] = (
            "OFW registration is for a Filipino citizen. SSS confirms eligibility on the official website."
        )
    citizenship = clean_text(form.get("citizenship", ""))
    for row in stored:
        if row["key"] in {"spouse_member_name", "spouse_member_ss_number"} and purpose != "Non-Working Spouse":
            row["value"] = ""
            errors.pop(row["key"], None)
        # SSS only asks nationality for foreign nationals. Passport and other
        # services keep the nationality the applicant typed.
        if (
            row["key"] == "nationality"
            and "citizenship" in field_keys
            and citizenship != "Foreign National"
            and spec.get("kind") == "sss"
        ):
            row["value"] = ""
            errors.pop(row["key"], None)
        if row["key"] == "sss_path" and not row.get("value"):
            row["value"] = SSS_PATH_NEW
    return stored, errors


def prefill_values(application=None):
    """Return answers already saved on a draft. A new form starts empty."""
    if application is None:
        return {}
    return field_map(application)


def _tracking_number():
    for _ in range(5):
        number = f"OGP-{_now():%Y%m%d}-{secrets.token_hex(4).upper()}"
        taken = db.session.scalar(
            db.select(Application.application_id).where(Application.tracking_number == number)
        )
        if taken is None:
            return number
    raise RuntimeError("A reference number could not be created. Try again.")


def find_draft(user_id, service_id):
    return db.session.scalar(
        db.select(Application)
        .where(
            Application.applicant_id == user_id,
            Application.service_id == service_id,
            Application.application_status == "draft",
        )
        .order_by(Application.application_id.desc())
    )


def ensure_draft(user, service):
    """Return the open draft for this service, creating an empty one when needed."""
    draft = find_draft(user.user_id, service.service_id)
    if draft is not None:
        return draft
    return save_draft(user, service, [], None)


def merge_id_autofill(application, extracted, spec):
    """Fill blankable passport fields from OCR. Keep missing OCR values empty."""
    details = read_details(application)
    previous_keys = set(details.get("id_autofill_keys") or [])
    by_key = {row.get("key"): dict(row) for row in details["fields"] if row.get("key")}
    for key in previous_keys:
        if key not in extracted and key in by_key:
            by_key[key]["value"] = ""
    field_meta = {field["key"]: field for field in spec.get("fields") or []}
    autofill_keys = []
    for key, value in (extracted or {}).items():
        cleaned = str(value or "").strip()
        if not cleaned or key not in field_meta:
            continue
        field = field_meta[key]
        row = by_key.get(key) or {
            "key": key,
            "label": field["label"],
            "value": "",
        }
        if field.get("section"):
            row["section"] = field["section"]
        row["label"] = field["label"]
        row["value"] = cleaned[: field.get("max_length") or 500]
        by_key[key] = row
        autofill_keys.append(key)
    ordered = []
    seen = set()
    for field in spec.get("fields") or []:
        key = field["key"]
        if key in by_key:
            ordered.append(by_key[key])
            seen.add(key)
    for key, row in by_key.items():
        if key not in seen:
            ordered.append(row)
    details["fields"] = ordered
    details["id_autofill_keys"] = autofill_keys
    write_details(application, details, commit=False)


def clear_id_autofill(application):
    """Clear values that were filled from a removed passport ID upload."""
    details = read_details(application)
    autofill_keys = set(details.get("id_autofill_keys") or [])
    if not autofill_keys:
        return
    for row in details["fields"]:
        if row.get("key") in autofill_keys:
            row["value"] = ""
    details["id_autofill_keys"] = []
    write_details(application, details, commit=False)


def owned_application(user_id, application_id):
    return db.session.scalar(
        db.select(Application).where(
            Application.application_id == application_id,
            Application.applicant_id == user_id,
        )
    )


def save_draft(user, service, stored_fields, application=None):
    now = _now()
    previous = read_details(application)
    old_citizenship = next(
        (item.get("value") for item in previous["fields"] if item.get("key") == "citizenship"),
        "",
    )
    new_citizenship = next(
        (item.get("value") for item in stored_fields if item.get("key") == "citizenship"),
        "",
    )
    checklist = [] if old_citizenship != new_citizenship else previous["checklist"]
    if old_citizenship != new_citizenship and application is not None:
        row = requirement_for(application, "supporting_id")
        if row is not None:
            _delete_stored_file(row.uploaded_file)
            db.session.delete(row)
        previous["id_autofill_keys"] = []
    if application is None:
        application = Application(
            tracking_number=_tracking_number(),
            applicant_id=user.user_id,
            service_id=service.service_id,
            application_status="draft",
            submission_date=now,
            last_updated=now,
            assigned_department_id=service.department_id,
        )
        db.session.add(application)
    payload = {"fields": stored_fields, "checklist": checklist}
    if previous.get("id_autofill_keys"):
        payload["id_autofill_keys"] = list(previous["id_autofill_keys"])
    if previous.get("appointment"):
        payload["appointment"] = previous["appointment"]
    if previous.get("confirmation"):
        payload["confirmation"] = previous["confirmation"]
    application.application_details = payload
    application.last_updated = now
    db.session.commit()
    return application


def requirement_for(application, document_key):
    return next(
        (item for item in application.requirements if item.requirement_name == document_key),
        None,
    )


def missing_documents(application, spec):
    if spec.get("checklist"):
        return missing_checklist(application, spec)
    # Temporary: allow Senior Citizen ID continue without uploaded documents.
    if spec.get("kind") == "senior":
        return []
    values = field_map(application)
    missing = []
    for rule in document_rules(spec, values):
        if not rule["required"]:
            continue
        if rule.get("id_choices") == "dfa":
            if not _passport_id_ready(application, values):
                missing.append(rule["label"])
            continue
        if rule.get("id_choices") == "barangay":
            if not _barangay_id_ready(application, rule["key"]):
                missing.append(rule["label"])
            continue
        if rule.get("id_choices") in {"sss", "sss_alt"}:
            if not _sss_id_ready(
                application,
                rule["key"],
                pool="alternative" if rule.get("id_choices") == "sss_alt" else "primary",
            ):
                missing.append(rule["label"])
            continue
        row = requirement_for(application, rule["key"])
        if row is None or not row.uploaded_file:
            missing.append(rule["label"])
    return missing


def _passport_id_ready(application, values):
    """A passport ID counts only when the file matches an ID this applicant may use."""
    from app.services.passport_ids import passport_id_by_key

    matched = next(
        (
            item
            for item in read_checklist(application)
            if item.get("key") == "valid_id" and item.get("value") == "matched"
        ),
        None,
    )
    row = requirement_for(application, "valid_id")
    selected = passport_id_by_key(
        values.get("application_type"),
        values.get("date_of_birth"),
        matched.get("document_key") if matched else "",
    )
    return matched is not None and selected is not None and row is not None and bool(row.uploaded_file)


def _barangay_id_ready(application, document_key="valid_id"):
    """A listed ID counts when an ID type is matched and the file is uploaded."""
    from app.services.barangay_ids import barangay_id_by_key

    matched = next(
        (
            item
            for item in read_checklist(application)
            if item.get("key") == document_key and item.get("value") in {"selected", "matched"}
        ),
        None,
    )
    row = requirement_for(application, document_key)
    selected = barangay_id_by_key(matched.get("document_key") if matched else "")
    return matched is not None and selected is not None and row is not None and bool(row.uploaded_file)


def _sss_id_ready(application, document_key="valid_id", pool="primary"):
    """An SSS listed ID counts when an ID type is matched and the file is uploaded."""
    from app.services.sss_ids import sss_id_by_key

    matched = next(
        (
            item
            for item in read_checklist(application)
            if item.get("key") == document_key and item.get("value") in {"selected", "matched"}
        ),
        None,
    )
    row = requirement_for(application, document_key)
    selected = sss_id_by_key(matched.get("document_key") if matched else "", pool=pool)
    return matched is not None and selected is not None and row is not None and bool(row.uploaded_file)


def missing_checklist(application, spec):
    matched = next(
        (item for item in read_checklist(application) if item.get("value") == "matched"),
        None,
    )
    if matched is None:
        return ["Selected document"]
    row = requirement_for(application, matched["key"])
    if row is None or not row.uploaded_file:
        return ["Selected document"]
    return []


def _stored_path(application_id, document_key, extension):
    folder = _upload_root() / str(application_id)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{secure_filename(document_key)}-{secrets.token_hex(8)}{extension}"
    return folder / name


def _payload_from_upload(upload, file_rules=None):
    rules = file_rules or {}
    allowed = rules.get("extensions") or ALLOWED_EXTENSIONS
    limit = rules.get("max_bytes") or _max_bytes()
    extension = Path(upload.filename or "").suffix.lower()
    signature = allowed.get(extension)
    if signature is None:
        return None, None, rules.get("type_error") or "Upload a PDF, JPG, JPEG, or PNG file."
    payload = upload.read()
    if not payload:
        return None, None, "The selected file is empty."
    if len(payload) > limit:
        return None, None, rules.get("size_error") or "The file is larger than the 16 MB limit."
    if not payload.startswith(signature):
        return None, None, rules.get("content_error") or "The file contents do not match a PDF or image."
    return payload, extension, None


def _store_payload(application, document_key, payload, extension, original_name, commit=True):
    path = _stored_path(application.application_id, document_key, extension)
    path.write_bytes(payload)
    relative = path.relative_to(_upload_root()).as_posix()
    row = requirement_for(application, document_key)
    if row is None:
        row = ApplicationRequirement(
            application_id=application.application_id,
            requirement_name=document_key,
            verification_status="pending",
        )
        db.session.add(row)
    else:
        _delete_stored_file(row.uploaded_file)
    row.uploaded_file = relative
    row.remarks = clean_text(original_name)[:200] or path.name
    row.verification_status = "pending"
    application.last_updated = _now()
    if commit:
        db.session.commit()
    return None


def remove_upload(application, document_key):
    """Delete one uploaded file from a draft. The requirement can be uploaded again."""
    row = requirement_for(application, document_key)
    if row is None:
        return None
    _delete_stored_file(row.uploaded_file)
    db.session.delete(row)
    application.last_updated = _now()
    db.session.commit()
    return None


def save_upload(application, document_key, upload, original_name, file_rules=None):
    payload, extension, error = _payload_from_upload(upload, file_rules)
    if error:
        return error
    return _store_payload(application, document_key, payload, extension, original_name)


def save_passport_id(application, selected, upload):
    """Store the passport ID only when its visible title matches the selected ID."""
    from app.services.document_text import read_document_text
    from app.services.passport_ids import check_passport_id_text, extract_id_fields

    payload, extension, error = _payload_from_upload(upload)
    if error:
        return error
    text, read_error = read_document_text(payload, extension)
    if read_error:
        return read_error
    mismatch = check_passport_id_text(selected["key"], text)
    if mismatch:
        return mismatch
    details = read_details(application)
    checklist = [item for item in details["checklist"] if item.get("key") != "valid_id"]
    checklist.append({
        "key": "valid_id",
        "document_key": selected["key"],
        "label": selected["label"],
        "value": "matched",
        "filename": clean_text(upload.filename)[:200],
    })
    details["checklist"] = checklist
    write_details(application, details, commit=False)
    spec = specification_for(application.service, field_map(application))
    merge_id_autofill(application, extract_id_fields(text), spec or {})
    return _store_payload(application, "valid_id", payload, extension, upload.filename)


def save_barangay_id(application, selected, upload, document_key="valid_id"):
    """Store a searchable-list government ID only when the file matches the selected ID."""
    from app.services.barangay_ids import check_barangay_id_text
    from app.services.document_text import read_document_text

    payload, extension, error = _payload_from_upload(upload)
    if error:
        return error
    text, read_error = read_document_text(payload, extension)
    if read_error:
        return read_error
    mismatch = check_barangay_id_text(selected["key"], text)
    if mismatch:
        return mismatch
    details = read_details(application)
    checklist = [item for item in details["checklist"] if item.get("key") != document_key]
    checklist.append({
        "key": document_key,
        "document_key": selected["key"],
        "label": selected["label"],
        "value": "matched",
        "filename": clean_text(upload.filename)[:200],
    })
    details["checklist"] = checklist
    write_details(application, details, commit=False)
    return _store_payload(application, document_key, payload, extension, upload.filename)


def save_sss_id(application, selected, upload, document_key="valid_id", pool="primary"):
    """Store an SSS primary or alternative ID when the visible title matches the selection."""
    from app.services.document_text import read_document_text
    from app.services.sss_ids import check_sss_id_text

    payload, extension, error = _payload_from_upload(upload)
    if error:
        return error
    text, read_error = read_document_text(payload, extension)
    if read_error:
        return read_error
    mismatch = check_sss_id_text(selected["key"], text, pool=pool)
    if mismatch:
        return mismatch
    if document_key.startswith("alt_id_"):
        other_key = "alt_id_2" if document_key == "alt_id_1" else "alt_id_1"
        other = next(
            (
                item
                for item in read_checklist(application)
                if item.get("key") == other_key and item.get("value") in {"selected", "matched"}
            ),
            None,
        )
        if other and other.get("document_key") == selected["key"]:
            return (
                "Choose two different alternative documents. "
                f"{selected['label']} is already used for the other upload."
            )
    details = read_details(application)
    checklist = [item for item in details["checklist"] if item.get("key") != document_key]
    checklist.append({
        "key": document_key,
        "document_key": selected["key"],
        "label": selected["label"],
        "value": "matched",
        "filename": clean_text(upload.filename)[:200],
    })
    details["checklist"] = checklist
    write_details(application, details, commit=False)
    return _store_payload(application, document_key, payload, extension, upload.filename)


def _philsys_autofill_from_text(text):
    """Map OCR fields from a supporting ID onto PhilSys application field keys."""
    from app.services.passport_ids import extract_id_fields

    extracted = extract_id_fields(text) or {}
    mapped = {}
    for key, value in extracted.items():
        cleaned = str(value or "").strip()
        if not cleaned:
            continue
        if key == "civil_status":
            mapped["marital_status"] = cleaned
        elif key == "address":
            mapped["permanent_address"] = cleaned
        elif key == "nationality":
            lowered = cleaned.casefold()
            if "filipino" in lowered or lowered in {"ph", "philippines", "philippine"}:
                mapped["citizenship"] = "Filipino Citizen"
        else:
            mapped[key] = cleaned
    return mapped


def save_philsys_document(application, document, upload):
    """Store the supporting ID only when its visible title matches the selected document."""
    from app.services.document_text import read_document_text
    from app.services.philsys_national_id import check_document_text

    payload, extension, error = _payload_from_upload(upload)
    if error:
        return error
    text, read_error = read_document_text(payload, extension)
    if read_error:
        return read_error
    mismatch = check_document_text(
        field_map(application).get("citizenship"),
        document["key"],
        text,
    )
    if mismatch:
        return mismatch
    details = read_details(application)
    checklist = [item for item in details["checklist"] if item.get("key") != "supporting_id"]
    checklist.append({
        "key": "supporting_id",
        "document_key": document["key"],
        "label": document["label"],
        "value": "matched",
        "filename": clean_text(upload.filename)[:200],
    })
    details["checklist"] = checklist
    write_details(application, details, commit=False)
    spec = specification_for(application.service, field_map(application))
    merge_id_autofill(application, _philsys_autofill_from_text(text), spec or {})
    return _store_payload(
        application,
        "supporting_id",
        payload,
        extension,
        upload.filename,
    )


def save_philsys_reference(application, raw):
    """Save a PSA transaction reference. This does not change the application status."""
    value = clean_text(raw)
    if len(value) > 40:
        return "Use no more than 40 characters."
    if value and not value.replace(" ", "").replace("-", "").replace("/", "").isalnum():
        return "Enter the reference number PSA gave you, using letters and numbers."
    fields = []
    found = False
    for item in read_fields(application):
        stored = dict(item)
        if stored.get("key") == "philsys_reference":
            stored["value"] = value
            found = True
        fields.append(stored)
    if not found:
        fields.append({
            "key": "philsys_reference",
            "label": "PhilSys transaction reference number",
            "value": value,
            "section": "PhilSys transaction reference",
        })
    details = read_details(application)
    application.application_details = {"fields": fields, "checklist": details["checklist"]}
    application.last_updated = _now()
    db.session.commit()
    return None


def _upsert_field(fields, key, label, value, section):
    updated = []
    found = False
    for item in fields:
        stored = dict(item)
        if stored.get("key") == key:
            stored["value"] = value
            stored["label"] = label
            stored["section"] = section
            found = True
        updated.append(stored)
    if not found:
        updated.append({"key": key, "label": label, "value": value, "section": section})
    return updated


def save_cenomar_tracking(application, user, form):
    """Record a PSA reference the citizen already received. This does not confirm a PSA status."""
    from app.services.application_forms import CENOMAR_PAYMENT_OPTIONS, CENOMAR_RECORDED_STATUSES

    reference = "".join(clean_text(form.get("psa_reference", "")).split())
    if not (reference.isdigit() and len(reference) == 16):
        return "Enter the 16-digit PSA reference number from the official channel. OneGov PH does not create this number."
    application_date = _parse_date(clean_text(form.get("psa_application_date", "")))
    if application_date is None:
        return "Enter the application date shown on the official PSA channel. A future date is not accepted."
    payment_status = clean_text(form.get("psa_payment_status", ""))
    if payment_status not in CENOMAR_PAYMENT_OPTIONS:
        return "Select the payment status shown on the official PSA channel."
    payment_raw = clean_text(form.get("psa_payment_date", ""))
    if payment_raw and _parse_date(payment_raw) is None:
        return "Enter a real payment date that is not in the future."
    recorded = clean_text(form.get("psa_recorded_status", ""))
    if recorded and recorded not in CENOMAR_RECORDED_STATUSES:
        return "Select a PSA status from the list, or leave it blank."
    expected = clean_text(form.get("psa_expected_delivery", ""))
    if len(expected) > 200:
        return "Use no more than 200 characters for the expected delivery information."
    section = "Official PSA record"
    fields = read_fields(application)
    for key, label, value in (
        ("psa_reference", "PSA reference number", reference),
        ("psa_application_date", "PSA application date", application_date.isoformat()),
        ("psa_payment_status", "PSA payment status", payment_status),
        ("psa_payment_date", "PSA payment date", payment_raw),
        ("psa_expected_delivery", "Expected delivery information", expected),
        ("psa_recorded_status", "PSA status you recorded", recorded),
    ):
        fields = _upsert_field(fields, key, label, value, section)
    details = read_details(application)
    previous = application.application_status
    application.application_details = {"fields": fields, "checklist": details["checklist"]}
    now = _now()
    application.last_updated = now
    if previous == "submitted":
        application.application_status = "under_review"
        from app.services.tracking_service import add_event

        add_event(
            application,
            user.user_id,
            "under_review",
            "The applicant recorded a PSA reference number. OneGov PH did not receive this number from PSA.",
            "submitted",
            now,
        )
    db.session.commit()
    return None


def save_sss_tracking(application, user, form, files):
    """Record SSS details the citizen already received. This does not issue an SS Number."""
    from app.services.application_forms import (
        SSS_DOCUMENT_STATUSES,
        SSS_FILE_RULES,
        SSS_RECORDED_STATUSES,
    )

    ss_number = _ss_number_digits(form.get("ss_number", ""))
    if ss_number and not (ss_number.isdigit() and len(ss_number) == 10):
        return "Enter the 10-digit SS Number SSS issued. OneGov PH does not create this number."
    transaction = clean_text(form.get("sss_transaction_number", ""))
    if transaction and not re.fullmatch(r"[A-Za-z0-9-]{6,40}", transaction):
        return "Enter the SSS transaction number from the official confirmation. OneGov PH does not create this number."
    registration_raw = clean_text(form.get("sss_registration_date", ""))
    registration_date = _parse_date(registration_raw) if registration_raw else None
    if registration_raw and registration_date is None:
        return "Enter the registration date shown by SSS. A future date is not accepted."
    issue_raw = clean_text(form.get("sss_issue_date", ""))
    issue_date = _parse_date(issue_raw) if issue_raw else None
    if issue_raw and issue_date is None:
        return "Enter the SS Number issuance date shown by SSS. A future date is not accepted."
    if registration_date and issue_date and issue_date < registration_date:
        return "The issuance date cannot be earlier than the registration date."
    recorded = clean_text(form.get("sss_recorded_status", ""))
    if recorded and recorded not in SSS_RECORDED_STATUSES:
        return "Select an SSS status from the list, or leave it blank."
    document_status = clean_text(form.get("sss_document_status", ""))
    if document_status and document_status not in SSS_DOCUMENT_STATUSES:
        return "Select the supporting-document status shown on the official SSS channel."
    if recorded in {"SS Number issued", "Completed", "Supporting documents submitted"} and not ss_number:
        return "Enter the SS Number SSS issued before recording that status. OneGov PH does not create this number."
    if (ss_number or transaction) and registration_date is None:
        return "Enter the registration date shown by SSS."
    prepared = []
    for key in ("ss_number_slip", "transaction_number_slip", "e1_e6_form"):
        upload = files.get(key) if files is not None else None
        if upload is None or not upload.filename:
            continue
        payload, extension, error = _payload_from_upload(upload, SSS_FILE_RULES)
        if error:
            return error
        prepared.append((key, payload, extension, upload.filename))
    section = "Official SSS record"
    fields = read_fields(application)
    for key, label, value in (
        ("ss_number", "SS Number", ss_number),
        ("sss_transaction_number", "SSS transaction number", transaction),
        ("sss_registration_date", "SSS registration date", registration_date.isoformat() if registration_date else ""),
        ("sss_recorded_status", "SSS status you recorded", recorded),
        ("sss_issue_date", "Date of SS Number issuance", issue_date.isoformat() if issue_date else ""),
        ("sss_document_status", "Supporting document submission status", document_status),
    ):
        fields = _upsert_field(fields, key, label, value, section)
    for key, payload, extension, original_name in prepared:
        error = _store_payload(application, key, payload, extension, original_name, commit=False)
        if error:
            return error
    details = read_details(application)
    previous = application.application_status
    application.application_details = {"fields": fields, "checklist": details["checklist"]}
    now = _now()
    application.last_updated = now
    if previous == "submitted" and (ss_number or transaction):
        application.application_status = "under_review"
        from app.services.tracking_service import add_event

        add_event(
            application,
            user.user_id,
            "under_review",
            "The applicant recorded an SSS transaction number or SS Number. OneGov PH did not receive it from SSS and did not issue an SS Number.",
            "submitted",
            now,
        )
    db.session.commit()
    return None


def absolute_upload(relative_path):
    if not relative_path or ".." in relative_path.replace("\\", "/").split("/"):
        return None
    root = _upload_root().resolve()
    path = (root / relative_path).resolve()
    if root not in path.parents or not path.is_file():
        return None
    return path


def _delete_stored_file(relative_path):
    path = absolute_upload(relative_path)
    if path is not None:
        path.unlink(missing_ok=True)


def cancel_draft(application):
    from app.models.nbi_appointment import NbiAppointment
    from app.models.passport_appointment import PassportAppointment

    for row in list(application.requirements):
        _delete_stored_file(row.uploaded_file)
        db.session.delete(row)
    appointment = db.session.scalar(
        db.select(PassportAppointment).where(
            PassportAppointment.application_id == application.application_id
        )
    )
    if appointment is not None:
        db.session.delete(appointment)
    nbi_appointment = db.session.scalar(
        db.select(NbiAppointment).where(
            NbiAppointment.application_id == application.application_id
        )
    )
    if nbi_appointment is not None:
        db.session.delete(nbi_appointment)
    confirmation = read_details(application).get("confirmation") or {}
    if confirmation.get("pdf_path"):
        _delete_stored_file(confirmation["pdf_path"])
    db.session.delete(application)
    db.session.commit()


def submit_application(application, user):
    """Move a draft to Submitted once. A second click does not create another record."""
    spec = specification_for(application.service, field_map(application))
    if spec is None:
        return "This service cannot be submitted."
    if spec.get("kind") == "cenomar":
        from app.services.application_forms import cenomar_incomplete_step

        incomplete = cenomar_incomplete_step(field_map(application))
        if incomplete:
            return "Complete every CENOMAR detail before saving this request."
    if application.application_status != "draft":
        return None
    if missing_documents(application, spec):
        if spec.get("checklist"):
            return "Mark whether you have each document before submitting."
        return "Upload every required document before submitting."
    now = _now()
    updated = db.session.execute(
        update(Application)
        .where(
            Application.application_id == application.application_id,
            Application.applicant_id == user.user_id,
            Application.application_status == "draft",
        )
        .values(
            application_status="submitted",
            submission_date=now,
            last_updated=now,
        )
    )
    if updated.rowcount != 1:
        db.session.rollback()
        return None
    from app.services.tracking_service import add_event

    add_event(
        application,
        user.user_id,
        "submitted",
        spec.get("submit_event")
        or (
            "Preliminary National ID information was saved for assistance and tracking. "
            "This does not register the person with PhilSys."
            if spec.get("kind") == "philsys"
            else "Application saved for assistance and tracking. "
            "This is not an official filing with the agency."
        ),
        "draft",
        now,
    )
    notice = spec.get("submit_notice")
    db.session.add(
        Notification(
            user_id=user.user_id,
            notification_title="Application received",
            notification_message=(
                notice.format(reference=application.tracking_number)
                if notice
                else (
                    f"Your National ID preparation {application.tracking_number} is pending in OneGov PH. "
                    "This is not PhilSys registration, and OneGov PH does not issue a National ID."
                    if spec.get("kind") == "philsys"
                    else f"Your {application.service.service_name} request {application.tracking_number} "
                    "is pending. OneGov PH is tracking it and has not filed it with the agency."
                )
            ),
            notification_type="application",
            read_status="unread",
            created_date=now,
        )
    )
    db.session.commit()
    return None


def passport_type_ready(application):
    """True when a passport application type was selected on step 1."""
    from app.services.passport_requirements import PASSPORT_APPLICATION_TYPES, normalize_passport_type

    selected = normalize_passport_type(field_map(application).get("application_type"))
    return selected in PASSPORT_APPLICATION_TYPES


def save_passport_application_type(application, application_type):
    """Store the passport application type without wiping other draft answers."""
    from app.services.passport_requirements import PASSPORT_APPLICATION_TYPES, normalize_passport_type

    selected = normalize_passport_type(application_type)
    if selected not in PASSPORT_APPLICATION_TYPES:
        return "Select a passport application type."
    details = read_details(application)
    details["fields"] = _upsert_field(
        details["fields"],
        "application_type",
        "Application type",
        selected,
        "Application",
    )
    write_details(application, details)
    return None


def barangay_type_ready(application):
    """True when a barangay clearance application type was selected on step 1."""
    from app.services.barangay_requirements import BARANGAY_APPLICATION_TYPES, normalize_barangay_type

    selected = normalize_barangay_type(field_map(application).get("application_type"))
    return selected in BARANGAY_APPLICATION_TYPES


def save_barangay_application_type(application, application_type):
    """Store the barangay application type without wiping other draft answers."""
    from app.services.barangay_requirements import BARANGAY_APPLICATION_TYPES, normalize_barangay_type

    selected = normalize_barangay_type(application_type)
    if selected not in BARANGAY_APPLICATION_TYPES:
        return "Select a barangay clearance application type."
    details = read_details(application)
    details["fields"] = _upsert_field(
        details["fields"],
        "application_type",
        "Application type",
        selected,
        "Purpose of clearance",
    )
    # Keep legacy purpose display in summaries aligned with the selected type.
    details["fields"] = _upsert_field(
        details["fields"],
        "purpose",
        "Purpose of the clearance",
        selected,
        "Purpose of clearance",
    )
    write_details(application, details)
    return None


def residency_type_ready(application):
    """True when a certificate of residency application type was selected on step 1."""
    from app.services.residency_requirements import RESIDENCY_APPLICATION_TYPES, normalize_residency_type

    selected = normalize_residency_type(field_map(application).get("application_type"))
    return selected in RESIDENCY_APPLICATION_TYPES


def senior_type_ready(application):
    """True when a Senior Citizen ID application type was selected on step 1."""
    from app.services.senior_requirements import SENIOR_APPLICATION_TYPES, normalize_senior_type

    selected = normalize_senior_type(field_map(application).get("application_type"))
    return selected in SENIOR_APPLICATION_TYPES


def save_senior_application_type(application, application_type):
    """Store the Senior Citizen ID application type without wiping other draft answers."""
    from app.services.senior_requirements import SENIOR_APPLICATION_TYPES, normalize_senior_type

    selected = normalize_senior_type(application_type)
    if selected not in SENIOR_APPLICATION_TYPES:
        return "Select a Senior Citizen ID application type."
    details = read_details(application)
    details["fields"] = _upsert_field(
        details["fields"],
        "application_type",
        "Application type",
        selected,
        "Request type",
    )
    write_details(application, details)
    return None


def nbi_type_ready(application):
    """True when an NBI clearance application type was selected on step 1."""
    from app.services.nbi_requirements import NBI_APPLICATION_TYPES, normalize_nbi_type

    selected = normalize_nbi_type(field_map(application).get("application_type"))
    return selected in NBI_APPLICATION_TYPES


def save_nbi_application_type(application, application_type):
    """Store the NBI application type without wiping other draft answers."""
    from app.services.nbi_requirements import NBI_APPLICATION_TYPES, normalize_nbi_type

    selected = normalize_nbi_type(application_type)
    if selected not in NBI_APPLICATION_TYPES:
        return "Select an NBI clearance application type."
    details = read_details(application)
    details["fields"] = _upsert_field(
        details["fields"],
        "application_type",
        "Application type",
        selected,
        "Application type",
    )
    write_details(application, details)
    return None


def birth_type_ready(application):
    """True when a birth certificate request type was selected on step 1."""
    from app.services.birth_requirements import BIRTH_APPLICATION_TYPES, normalize_birth_type

    selected = normalize_birth_type(field_map(application).get("application_type"))
    return selected in BIRTH_APPLICATION_TYPES


def save_birth_application_type(application, application_type):
    """Store the birth certificate request type without wiping other draft answers."""
    from app.services.birth_requirements import BIRTH_APPLICATION_TYPES, normalize_birth_type

    selected = normalize_birth_type(application_type)
    if selected not in BIRTH_APPLICATION_TYPES:
        return "Select a birth certificate request type."
    details = read_details(application)
    details["fields"] = _upsert_field(
        details["fields"],
        "application_type",
        "Application type",
        selected,
        "Request type",
    )
    write_details(application, details)
    return None


def save_residency_application_type(application, application_type):
    """Store the residency application type without wiping other draft answers."""
    from app.services.residency_requirements import RESIDENCY_APPLICATION_TYPES, normalize_residency_type

    selected = normalize_residency_type(application_type)
    if selected not in RESIDENCY_APPLICATION_TYPES:
        return "Select a certificate of residency application type."
    details = read_details(application)
    details["fields"] = _upsert_field(
        details["fields"],
        "application_type",
        "Application type",
        selected,
        "Purpose of certificate",
    )
    details["fields"] = _upsert_field(
        details["fields"],
        "purpose",
        "Purpose of the certificate",
        selected,
        "Purpose of certificate",
    )
    write_details(application, details)
    return None


def passport_details_ready(application, spec=None):
    """True when required passport or documents-first application fields are saved."""
    values = field_map(application)
    spec = spec or specification_for(application.service, values)
    if not spec or not (spec.get("kind") in {"passport", "philsys"} or spec.get("documents_first")):
        return False
    for field in spec.get("fields") or []:
        if not field.get("required"):
            continue
        if field.get("type") == "hidden" and field.get("key") == "application_type":
            if not passport_type_ready(application):
                return False
            continue
        if field.get("show_rules") and not field_is_visible_from_map(field, values):
            continue
        if not str(values.get(field["key"]) or "").strip():
            return False
    return True


def passport_review_ready(application):
    """True when the passport review step was accepted."""
    return bool(read_details(application).get("passport_reviewed"))


def mark_passport_reviewed(application):
    """Record that the applicant accepted the passport review step."""
    details = read_details(application)
    details["passport_reviewed"] = True
    write_details(application, details)


def barangay_review_ready(application):
    """True when the barangay review step was accepted."""
    return bool(read_details(application).get("barangay_reviewed"))


def mark_barangay_reviewed(application):
    """Record that the applicant accepted the barangay review step."""
    details = read_details(application)
    details["barangay_reviewed"] = True
    write_details(application, details)


def residency_review_ready(application):
    """True when the residency review step was accepted."""
    return bool(read_details(application).get("residency_reviewed"))


def mark_residency_reviewed(application):
    """Record that the applicant accepted the residency review step."""
    details = read_details(application)
    details["residency_reviewed"] = True
    write_details(application, details)


def senior_review_ready(application):
    """True when the senior citizen review step was accepted."""
    return bool(read_details(application).get("senior_reviewed"))


def mark_senior_reviewed(application):
    """Record that the applicant accepted the senior citizen review step."""
    details = read_details(application)
    details["senior_reviewed"] = True
    write_details(application, details)


def nbi_review_ready(application):
    """True when the NBI review step was accepted."""
    return bool(read_details(application).get("nbi_reviewed"))


def mark_nbi_reviewed(application):
    """Record that the applicant accepted the NBI review step."""
    details = read_details(application)
    details["nbi_reviewed"] = True
    write_details(application, details)


def birth_review_ready(application):
    """True when the birth certificate review step was accepted."""
    return bool(read_details(application).get("birth_reviewed"))


def mark_birth_reviewed(application):
    """Record that the applicant accepted the birth certificate review step."""
    details = read_details(application)
    details["birth_reviewed"] = True
    write_details(application, details)


def cenomar_review_ready(application):
    """True when the CENOMAR review step was accepted."""
    return bool(read_details(application).get("cenomar_reviewed"))


def mark_cenomar_reviewed(application):
    """Record that the applicant accepted the CENOMAR review step."""
    details = read_details(application)
    details["cenomar_reviewed"] = True
    write_details(application, details)


def philsys_review_ready(application):
    """True when the PhilSys review step was accepted."""
    return bool(read_details(application).get("philsys_reviewed"))


def mark_philsys_reviewed(application):
    """Record that the applicant accepted the PhilSys review step."""
    details = read_details(application)
    details["philsys_reviewed"] = True
    write_details(application, details)


def sss_review_ready(application):
    """True when the SSS review step was accepted."""
    return bool(read_details(application).get("sss_reviewed"))


def mark_sss_reviewed(application):
    """Record that the applicant accepted the SSS review step."""
    details = read_details(application)
    details["sss_reviewed"] = True
    write_details(application, details)


def field_is_visible_from_map(field, values):
    from app.services.application_forms import field_is_visible

    return field_is_visible(field, values)


def continue_target(application):
    spec = specification_for(application.service, field_map(application))
    if spec is None or application.application_status != "draft":
        return "detail"
    if spec.get("kind") == "passport":
        if not passport_type_ready(application):
            return "type"
        if missing_documents(application, spec):
            return "documents"
        if not passport_details_ready(application, spec):
            return "details"
        if not passport_review_ready(application):
            return "review"
        from app.services.passport_scheduling import appointment_for

        if appointment_for(application) is None:
            return "schedule"
        return "payment"
    if spec.get("kind") == "philsys":
        if missing_documents(application, spec):
            return "documents"
        if not passport_details_ready(application, spec):
            return "details"
        if not philsys_review_ready(application):
            return "review"
        from app.services.philsys_scheduling import appointment_for

        if appointment_for(application) is None:
            return "schedule"
        return "payment"
    if spec.get("kind") == "nbi":
        if spec.get("type_first") and not nbi_type_ready(application):
            return "type"
        if not read_fields(application):
            return "details"
        if missing_documents(application, spec):
            return "documents"
        if not nbi_review_ready(application):
            return "review"
        if spec.get("review_before_schedule"):
            from app.services.nbi_scheduling import appointment_for

            if appointment_for(application) is None:
                return "schedule"
        return "payment"
    if spec.get("kind") in {"barangay", "residency"}:
        if spec.get("type_first"):
            type_ready = barangay_type_ready(application) if spec.get("kind") == "barangay" else residency_type_ready(application)
            if not type_ready:
                return "type"
        if not read_fields(application):
            return "details"
        if missing_documents(application, spec):
            return "documents"
        reviewed = (
            barangay_review_ready(application)
            if spec.get("kind") == "barangay"
            else residency_review_ready(application)
        )
        if not reviewed:
            return "review"
        if spec.get("review_before_schedule"):
            from app.services.barangay_scheduling import appointment_for

            if appointment_for(application) is None:
                return "schedule"
        return "payment"
    if spec.get("kind") == "senior":
        if spec.get("type_first") and not senior_type_ready(application):
            return "type"
        if not read_fields(application):
            return "details"
        if missing_documents(application, spec):
            return "documents"
        if not senior_review_ready(application):
            return "review"
        if spec.get("review_before_schedule"):
            from app.services.senior_scheduling import appointment_for

            if appointment_for(application) is None:
                return "schedule"
        return "payment"
    if spec.get("kind") == "birth":
        if spec.get("type_first") and not birth_type_ready(application):
            return "type"
        if not read_fields(application):
            return "details"
        if missing_documents(application, spec):
            return "documents"
        if not birth_review_ready(application):
            return "review"
        return "payment"
    if spec.get("kind") in {"cenomar", "sss"}:
        if not read_fields(application):
            return "details"
        if missing_documents(application, spec):
            return "documents"
        if spec.get("kind") == "cenomar":
            from app.services.application_forms import cenomar_incomplete_step

            incomplete = cenomar_incomplete_step(field_map(application))
            if incomplete:
                return "details"
            reviewed = cenomar_review_ready(application)
        else:
            reviewed = sss_review_ready(application)
        if not reviewed:
            return "review"
        return "payment"
    if spec.get("documents_first"):
        if missing_documents(application, spec):
            return "documents"
        if not passport_details_ready(application, spec):
            return "details"
        from app.services.passport_scheduling import appointment_for

        if appointment_for(application) is None:
            return "schedule"
        return "payment"
    if not read_fields(application):
        return "details"
    if missing_documents(application, spec):
        return "documents"
    return "review"
