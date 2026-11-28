from sqlalchemy.dialects.mysql import INTEGER

from app import db


class Service(db.Model):
    """Maps the existing services table. This model does not create a table."""

    __tablename__ = "services"

    service_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    department_id = db.Column(
        INTEGER(unsigned=True),
        db.ForeignKey("departments.department_id"),
        nullable=False,
    )
    service_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    processing_fee = db.Column(db.Numeric(10, 2), nullable=False)
    estimated_processing_time = db.Column(db.String(100))
    service_requirements = db.Column(db.Text)
    service_status = db.Column(
        db.Enum("active", "inactive", name="service_status"),
        nullable=False,
    )

    department = db.relationship("Department", foreign_keys=[department_id])

    def __repr__(self):
        return f"<Service {self.service_id} {self.service_name}>"
