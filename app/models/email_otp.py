from datetime import datetime

from sqlalchemy.dialects.mysql import INTEGER

from app import db


class EmailOtp(db.Model):
    PURPOSE_LOGIN = "login"
    PURPOSE_REGISTER = "register"
    PURPOSES = (PURPOSE_LOGIN, PURPOSE_REGISTER)

    __tablename__ = "email_otps"

    otp_id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    purpose = db.Column(
        db.Enum(*PURPOSES, name="email_otp_purpose"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        INTEGER(unsigned=True),
        db.ForeignKey("users.user_id"),
        nullable=True,
        index=True,
    )
    email = db.Column(db.String(255), nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)
    payload = db.Column(db.JSON, nullable=True)
    attempts = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    max_attempts = db.Column(db.Integer, nullable=False, default=5, server_default="5")
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    last_sent_at = db.Column(db.DateTime, nullable=False)
    resend_available_at = db.Column(db.DateTime, nullable=False)
    consumed_at = db.Column(db.DateTime, nullable=True)
    invalidated_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )

    user = db.relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        db.Index(
            "idx_email_otps_active_lookup",
            "purpose",
            "email",
            "consumed_at",
            "invalidated_at",
        ),
    )

    def is_active(self, now=None):
        now = now or datetime.utcnow()
        return (
            self.consumed_at is None
            and self.invalidated_at is None
            and self.expires_at > now
        )

    def is_expired(self, now=None):
        now = now or datetime.utcnow()
        return self.expires_at <= now

    def attempts_exhausted(self):
        return (self.attempts or 0) >= (self.max_attempts or 5)

    def can_resend(self, now=None):
        now = now or datetime.utcnow()
        return now >= (self.resend_available_at or now)

    def resend_wait_seconds(self, now=None):
        now = now or datetime.utcnow()
        target = self.resend_available_at or now
        if now >= target:
            return 0
        return int((target - now).total_seconds() + 0.999)

    def expires_in_seconds(self, now=None):
        now = now or datetime.utcnow()
        if now >= self.expires_at:
            return 0
        return int((self.expires_at - now).total_seconds() + 0.999)
