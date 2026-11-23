from datetime import datetime
from sqlalchemy.dialects.mysql import INTEGER
from app import db


class AccountRequest(db.Model):
    __tablename__ = "account_requests"

    request_id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    user_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("users.user_id"), nullable=False, index=True)
    request_type = db.Column(db.Enum("deactivation", "deletion", name="account_request_type"), nullable=False)
    reason = db.Column(db.String(500))
    status = db.Column(db.Enum("pending", "reviewed", "approved", "rejected", "cancelled", name="account_request_status"), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        db.Index("idx_account_requests_status", "status"),
    )
