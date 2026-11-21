"""Administrative audit trail records. Immutable through the application."""

from datetime import datetime, timezone
import uuid

from sqlalchemy.dialects.mysql import INTEGER, JSON

from app import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    activity_id = db.Column(db.String(40), nullable=False, unique=True, index=True)
    user_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("users.user_id"), nullable=True, index=True)
    department_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("departments.department_id"), nullable=True, index=True)
    user_name_snapshot = db.Column(db.String(200), nullable=False, default="")
    user_role = db.Column(db.String(60), nullable=False, default="", index=True)
    activity_type = db.Column(db.String(120), nullable=False, index=True)
    module = db.Column(db.String(80), nullable=False, index=True)
    description = db.Column(db.String(600), nullable=False)
    record_id = db.Column(db.String(120), nullable=True, index=True)
    previous_value = db.Column(JSON, nullable=True)
    new_value = db.Column(JSON, nullable=True)
    ip_address = db.Column(db.String(64), nullable=True, index=True)
    user_agent = db.Column(db.String(500), nullable=True)
    activity_status = db.Column(db.String(20), nullable=False, default="Success", index=True)  # Success/Failed/Denied
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    user = db.relationship("User", foreign_keys=[user_id])
    department = db.relationship("Department", foreign_keys=[department_id])

    @staticmethod
    def make_activity_id():
        return f"AUD-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:10].upper()}"

    def __repr__(self):
        return f"<AuditLog {self.activity_id} {self.activity_type}>"
