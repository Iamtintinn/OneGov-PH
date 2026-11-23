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
        default="system",
        server_default="system",
    )
    read_status = db.Column(
        db.Enum("unread", "read", name="read_status"),
        nullable=False,
        default="unread",
        server_default="unread",
    )
    created_date = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )

    __table_args__ = (
        db.Index("idx_notifications_read_status", "read_status"),
        db.Index("idx_notifications_created_date", "created_date"),
    )

    def __repr__(self):
        return f"<Notification {self.notification_id} user={self.user_id}>"
