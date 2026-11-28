from sqlalchemy.dialects.mysql import INTEGER

from app import db


class Notification(db.Model):
    """Maps the existing notifications table. This model does not create a table."""

    __tablename__ = "notifications"

    notification_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    user_id = db.Column(
        INTEGER(unsigned=True),
        db.ForeignKey("users.user_id"),
        nullable=False,
        index=True,
    )
    notification_title = db.Column(db.String(200), nullable=False)
    notification_message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(
        db.Enum(
            "application",
            "payment",
            "appointment",
            "account",
            "system",
            name="notification_type",
        ),
        nullable=False,
    )
    read_status = db.Column(
        db.Enum("unread", "read", name="read_status"),
        nullable=False,
    )
    created_date = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<Notification {self.notification_id} user={self.user_id}>"
