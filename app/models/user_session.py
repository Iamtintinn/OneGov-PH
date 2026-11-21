from datetime import datetime
from sqlalchemy.dialects.mysql import INTEGER
from app import db


class UserSession(db.Model):
    __tablename__ = "user_sessions"

    id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    user_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("users.user_id"), nullable=False, index=True)
    session_token = db.Column(db.String(128), nullable=False, unique=True, index=True)
    ip_address = db.Column(db.String(64))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    revoked_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])

    @property
    def is_active(self):
        return self.revoked_at is None
