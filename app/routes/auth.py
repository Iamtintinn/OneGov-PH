from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, logout_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.user import User
from app.utils.helpers import establish_session, home_endpoint_for_role
from app.utils.validators import clean_text, normalize_email, validate_registration

auth_bp = Blueprint("auth", __name__)


def _safe_next_url(raw):
    """Allow only same-site relative paths (used after Maya QRPh return)."""
    candidate = (raw or "").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return None
    if "\\" in candidate or "://" in candidate:
        return None
    return candidate


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = _safe_next_url(request.values.get("next"))
    if current_user.is_authenticated:
        return redirect(next_url or url_for(home_endpoint_for_role(current_user.role)))

    email = ""
    error = None
    if request.method == "POST":
        email = normalize_email(request.form.get("email"))
        password = request.form.get("password") or ""
        if not email or not password:
            error = "Enter your email and password."
        else:
            user = db.session.scalar(db.select(User).where(User.email == email))
            if user is None or not user.check_password(password):
                error = "Invalid email or password."
            elif not user.is_active:
                error = "This account is disabled. Contact OneGov PH support."
            else:
                establish_session(user)
                return redirect(next_url or url_for(home_endpoint_for_role(user.role)))

    return render_template("auth/login.html", email=email, error=error, next_url=next_url)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(home_endpoint_for_role(current_user.role)))

    form = {
        "first_name": "",
        "middle_name": "",
        "last_name": "",
        "email": "",
        "contact_number": "",
    }
    errors = {}
    if request.method == "POST":
        submitted = {
            "first_name": request.form.get("first_name", ""),
            "middle_name": request.form.get("middle_name", ""),
            "last_name": request.form.get("last_name", ""),
            "email": request.form.get("email", ""),
            "contact_number": request.form.get("contact_number", ""),
        }
        cleaned, errors = validate_registration(
            submitted,
            request.form.get("password") or "",
            request.form.get("confirm_password") or "",
        )
        form = {
            "first_name": clean_text(submitted["first_name"]),
            "middle_name": clean_text(submitted["middle_name"]),
            "last_name": clean_text(submitted["last_name"]),
            "email": cleaned["email"] or normalize_email(submitted["email"]),
            "contact_number": clean_text(submitted["contact_number"]),
        }
        if not errors:
            user = User.register_citizen(
                first_name=cleaned["first_name"],
                middle_name=cleaned["middle_name"] or None,
                last_name=cleaned["last_name"],
                email=cleaned["email"],
                contact_number=cleaned["contact_number"],
                password=request.form.get("password") or "",
            )
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                errors["email"] = "An account with this email already exists."
            else:
                establish_session(user)
                flash("Your citizen account has been created.", "success")
                return redirect(url_for("citizen.dashboard"))

    return render_template("auth/register.html", form=form, errors=errors)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    if current_user.is_authenticated:
        logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
