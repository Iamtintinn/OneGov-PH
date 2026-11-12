import re

_NAME = re.compile(r"^[A-Za-zÀ-ÿÑñ]+(?:[ .'-][A-Za-zÀ-ÿÑñ]+)*$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean_text(value):
    return " ".join((value or "").split())


def normalize_email(value):
    return clean_text(value).lower()


def normalize_contact_number(value):
    raw = (value or "").strip()
    has_plus = raw.startswith("+")
    digits = re.sub(r"[\s().-]", "", raw)
    if digits.startswith("+"):
        has_plus = True
        digits = digits[1:]
    if not digits.isdigit():
        return ""
    if has_plus:
        return f"+{digits}"
    return digits


def validate_name(value, label, required=True, max_length=80):
    name = clean_text(value)
    if not name:
        if required:
            return None, f"{label} is required."
        return None, None
    if len(name) > max_length or not _NAME.fullmatch(name):
        return None, f"Enter a valid {label.lower()}."
    return name, None


def validate_registration(data, password, confirm_password):
    errors = {}

    first_name, first_error = validate_name(data.get("first_name"), "First name")
    middle_name, middle_error = validate_name(
        data.get("middle_name"), "Middle name", required=False
    )
    last_name, last_error = validate_name(data.get("last_name"), "Last name")
    if first_error:
        errors["first_name"] = first_error
    if middle_error:
        errors["middle_name"] = middle_error
    if last_error:
        errors["last_name"] = last_error

    email = normalize_email(data.get("email"))
    if not email:
        errors["email"] = "Email address is required."
    elif len(email) > 255 or not _EMAIL.fullmatch(email):
        errors["email"] = "Enter a valid email address."

    contact_number = normalize_contact_number(data.get("contact_number"))
    contact_digits = contact_number[1:] if contact_number.startswith("+") else contact_number
    if not contact_number:
        errors["contact_number"] = "Contact number is required."
    elif not contact_digits.isdigit() or not 10 <= len(contact_digits) <= 15:
        errors["contact_number"] = "Enter a valid contact number."

    if not password:
        errors["password"] = "Password is required."
    elif not 8 <= len(password) <= 128:
        errors["password"] = "Use a password between 8 and 128 characters."
    elif not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        errors["password"] = "Use at least one letter and one number."

    if not confirm_password:
        errors["confirm_password"] = "Confirm your password."
    elif password != confirm_password:
        errors["confirm_password"] = "Passwords do not match."

    cleaned = {
        "first_name": first_name or "",
        "middle_name": middle_name or "",
        "last_name": last_name or "",
        "email": email,
        "contact_number": contact_number,
    }
    return cleaned, errors
