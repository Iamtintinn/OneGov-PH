from sqlalchemy.dialects.mysql import INTEGER

from app import db


class NbiAppointment(db.Model):
    """Demonstration appointment slot for NBI clearance monitoring. Not an official NBI booking."""

    __tablename__ = "nbi_appointments"

    appointment_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    application_id = db.Column(
        INTEGER(unsigned=True),
        db.ForeignKey("applications.application_id"),
        nullable=False,
        unique=True,
    )
    location_code = db.Column(db.String(40), nullable=False)
    location_label = db.Column(db.String(200), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.String(5), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

    application = db.relationship("Application", backref=db.backref("nbi_appointment", uselist=False))

    __table_args__ = (
        db.UniqueConstraint(
            "location_code",
            "appointment_date",
            "appointment_time",
            name="uq_nbi_appointments_slot",
        ),
    )

    def __repr__(self):
        return f"<NbiAppointment {self.appointment_id} app={self.application_id}>"
