from flask_login import UserMixin
from sqlalchemy.dialects.mysql import INTEGER
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(UserMixin, db.Model):
    ROLE_CITIZEN = "citizen"
    ROLE_DEPARTMENT_STAFF = "department_staff"
    ROLE_DEPARTMENT_SUPERVISOR = "department_supervisor"
    ROLE_SYSTEM_ADMIN = "system_admin"
    ROLES = (
        ROLE_CITIZEN,
        ROLE_DEPARTMENT_STAFF,
        ROLE_DEPARTMENT_SUPERVISOR,
        ROLE_SYSTEM_ADMIN,
    )
    ASSIGNED_ROLES = (
        ROLE_DEPARTMENT_STAFF,
        ROLE_DEPARTMENT_SUPERVISOR,
        ROLE_SYSTEM_ADMIN,
    )
    ROLE_LABELS = {
        ROLE_CITIZEN: "Citizen",
        ROLE_DEPARTMENT_STAFF: "Department staff",
        ROLE_DEPARTMENT_SUPERVISOR: "Department supervisor",
        ROLE_SYSTEM_ADMIN: "System administrator",
    }

    __tablename__ = "users"

    user_id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(80), nullable=False)
    middle_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    contact_number = db.Column(db.String(20))
    address = db.Column(db.String(500))
    account_status = db.Column(
        db.Enum("active", "inactive", "suspended", name="account_status"),
        nullable=False,
        default="active",
        server_default="active",
    )
    role = db.Column(
        db.Enum(*ROLES, name="user_role"),
        nullable=False,
        default=ROLE_CITIZEN,
        server_default=ROLE_CITIZEN,
        index=True,
    )
    email_verification_status = db.Column(
        db.Enum("unverified", "verified", name="email_verification_status"),
        nullable=False,
        default="unverified",
        server_default="unverified",
    )
    date_registered = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )

    @property
    def is_active(self):
        return self.account_status == "active"

    @property
    def role_label(self):
        return self.ROLE_LABELS.get(self.role, "Account")

    def get_id(self):
        return str(self.user_id)

    def set_name(self, first_name, last_name, middle_name=None):
        self.first_name = first_name
        self.middle_name = middle_name or None
        self.last_name = last_name
        parts = [first_name, middle_name, last_name]
        self.full_name = " ".join(part for part in parts if part)

    def set_password(self, password):
        """Store a Werkzeug hash. The plaintext password is not kept."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @classmethod
    def register_citizen(cls, *, first_name, middle_name, last_name, email, contact_number, password):
        """Open a citizen account. The public registration page cannot choose another role."""
        user = cls(
            email=email,
            contact_number=contact_number,
            role=cls.ROLE_CITIZEN,
            account_status="active",
            email_verification_status="unverified",
        )
        user.set_name(first_name, last_name, middle_name)
        user.set_password(password)
        return user

    @classmethod
    def create_authorized_account(
        cls,
        *,
        role,
        first_name,
        middle_name,
        last_name,
        email,
        contact_number,
        password,
    ):
        """Create a department or administrator account outside the public website form."""
        if role not in cls.ASSIGNED_ROLES:
            raise ValueError("This role must be assigned by an authorized administrator.")
        user = cls(
            email=email,
            contact_number=contact_number,
            role=role,
            account_status="active",
            email_verification_status="unverified",
        )
        user.set_name(first_name, last_name, middle_name)
        user.set_password(password)
        return user

    def __repr__(self):
        return f"<User {self.user_id} role={self.role} status={self.account_status}>"
