from flask import abort
from flask_login import current_user
from sqlalchemy import false, or_
from sqlalchemy.orm import joinedload

from app import db
from app.models.application import Application
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.service import Service
from app.models.user import User
from app.utils.portal import in_admin_portal

DEPARTMENT_ADMIN_DEPARTMENTS = User.DEPARTMENT_ADMIN_DEPARTMENTS
DEPARTMENT_ADMIN_DEPARTMENT_NAMES = frozenset(DEPARTMENT_ADMIN_DEPARTMENTS)
DEPARTMENT_ROLES = frozenset({User.ROLE_DEPARTMENT_STAFF, User.ROLE_DEPARTMENT_SUPERVISOR})


def is_system_admin():
    return (
        current_user.is_authenticated
        and current_user.is_active
        and current_user.role == User.ROLE_SYSTEM_ADMIN
    )


def is_department_admin():
    if not (
        current_user.is_authenticated
        and current_user.is_active
        and current_user.role == User.ROLE_DEPARTMENT_SUPERVISOR
        and bool(current_user.department_id)
    ):
        return False
    department = current_user.department
    return bool(department and department.department_name in DEPARTMENT_ADMIN_DEPARTMENT_NAMES)


def is_department_user():
    return (
        current_user.is_authenticated
        and current_user.is_active
        and current_user.role in DEPARTMENT_ROLES
        and bool(current_user.department_id)
    )


def is_admin_console_user():
    return is_system_admin() or is_department_admin()


def access_context():
    return {
        "is_system_admin": is_system_admin(),
        "is_department_admin": is_department_admin(),
        "is_admin_console_user": is_admin_console_user(),
        "department_admin_labels": DEPARTMENT_ADMIN_DEPARTMENT_NAMES,
    }


def department_role_label(user=None):
    account = user or current_user
    if account.role != User.ROLE_DEPARTMENT_SUPERVISOR:
        return User.ROLE_LABELS.get(account.role, "Account")
    name = account.department.department_name if account.department else ""
    if name in DEPARTMENT_ADMIN_DEPARTMENT_NAMES:
        return f"{name} Administrator"
    return User.ROLE_LABELS[User.ROLE_DEPARTMENT_SUPERVISOR]


def visible_application_query(query=None):
    query = query if query is not None else db.select(Application)
    if is_system_admin():
        return query
    if current_user.is_authenticated and current_user.role == User.ROLE_CITIZEN:
        return query.where(Application.applicant_id == current_user.user_id)
    if is_department_user():
        return query.where(Application.assigned_department_id == current_user.department_id)
    return query.where(false())


def visible_service_query(query=None):
    query = query if query is not None else db.select(Service)
    if not is_department_user():
        return query
    return query.where(Service.department_id == current_user.department_id)


def visible_payment_query(query=None):
    query = query if query is not None else db.select(Payment)
    query = query.join(Application, Payment.application_id == Application.application_id)
    return visible_application_query(query)


def managed_account_query(query=None):
    query = query if query is not None else db.select(User)
    if is_system_admin():
        return query
    if not is_department_user():
        return query.where(false())
    return query.where(
        User.role == User.ROLE_CITIZEN,
        User.user_id.in_(
            db.select(Application.applicant_id).where(
                Application.assigned_department_id == current_user.department_id
            )
        ),
    )


def application_or_404(application_id, *, include_documents=False, include_payments=False):
    options = [
        joinedload(Application.service).joinedload(Service.department),
        joinedload(Application.department),
    ]
    if include_documents:
        options.append(joinedload(Application.requirements))
    if include_payments:
        options.append(joinedload(Application.payments))
    query = visible_application_query(
        db.select(Application).options(*options).where(Application.application_id == application_id)
    )
    application = db.session.scalars(query).unique().first()
    if application is None:
        abort(404)
    return application


def _like_term(value):
    escaped = str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def visible_notification_query(query=None):
    query = query if query is not None else db.select(Notification)
    if in_admin_portal() and is_system_admin():
        return query
    if in_admin_portal() and is_department_user():
        tracking_numbers = db.session.scalars(
            db.select(Application.tracking_number).where(
                Application.assigned_department_id == current_user.department_id,
                Application.tracking_number.is_not(None),
            )
        ).all()
        payment_references = db.session.scalars(
            db.select(Payment.payment_reference)
            .join(Application, Payment.application_id == Application.application_id)
            .where(
                Application.assigned_department_id == current_user.department_id,
                Payment.payment_reference.is_not(None),
            )
        ).all()
        terms = [term for term in (*tracking_numbers, *payment_references) if term]
        if not terms:
            return query.where(false())
        return query.where(
            or_(*(Notification.notification_message.like(_like_term(term), escape="\\") for term in terms))
        )
    if current_user.is_authenticated:
        return query.where(Notification.user_id == current_user.user_id)
    return query.where(false())
