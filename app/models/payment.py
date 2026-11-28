from sqlalchemy.dialects.mysql import INTEGER

from app import db


class Payment(db.Model):
    """Maps the existing payments table. This model does not create a table."""

    __tablename__ = "payments"

    payment_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    application_id = db.Column(
        INTEGER(unsigned=True),
        db.ForeignKey("applications.application_id"),
        nullable=False,
    )
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_reference = db.Column(db.String(64), nullable=False, unique=True)
    payment_method = db.Column(
        db.Enum(
            "gcash",
            "maya",
            "bank_transfer",
            "over_the_counter",
            "online_banking",
            name="payment_method",
        ),
        nullable=False,
    )
    payment_status = db.Column(
        db.Enum("pending", "paid", "failed", "refunded", "cancelled", name="payment_status"),
        nullable=False,
    )
    transaction_date = db.Column(db.DateTime)
    provider_checkout_id = db.Column(db.String(64), unique=True)
    provider_status = db.Column(db.String(40))

    application = db.relationship("Application", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.payment_id} {self.payment_reference}>"
