from sqlalchemy.dialects.mysql import INTEGER

from app import db

APPLICATION_STATUSES = (
    "draft",
    "submitted",
    "under_review",
    "pending_documents",
    "for_payment",
    "paid",
    "scheduled",
    "processing",
    "ready_for_release",
    "completed",
    "rejected",
    "cancelled",
    "approved",
    "for_biometrics",
    "with_hit",
)


class Application(db.Model):
    """Maps the existing applications table. This model does not create a table."""

    __tablename__ = "applications"

    application_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    tracking_number = db.Column(db.String(30), nullable=False, unique=True)
    applicant_id = db.Column(
        INTEGER(unsigned=True),
        db.ForeignKey("users.user_id"),
        nullable=False,
        index=True,
    )
    service_id = db.Column(
        INTEGER(unsigned=True),
        db.ForeignKey("services.service_id"),
        nullable=False,
    )
    application_status = db.Column(
        db.Enum(*APPLICATION_STATUSES, name="application_status"),
        nullable=False,
        default="submitted",
        server_default="submitted",
    )
    submission_date = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    last_updated = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    assigned_department_id = db.Column(
        INTEGER(unsigned=True),
        db.ForeignKey("departments.department_id"),
        nullable=False,
    )
    application_details = db.Column(db.JSON)
    cancellation_reason = db.Column(db.String(500))

    service = db.relationship("Service", foreign_keys=[service_id])
    department = db.relationship("Department", foreign_keys=[assigned_department_id])
    payments = db.relationship("Payment", back_populates="application")
    requirements = db.relationship(
        "ApplicationRequirement",
        back_populates="application",
        order_by="ApplicationRequirement.requirement_id",
    )

    __table_args__ = (
        db.ForeignKeyConstraint(
            ["service_id", "assigned_department_id"],
            ["services.service_id", "services.department_id"],
            name="fk_applications_service_department",
            onupdate="CASCADE",
        ),
        db.Index("idx_applications_service", "service_id"),
        db.Index("idx_applications_department", "assigned_department_id"),
        db.Index("idx_applications_status", "application_status"),
        db.Index("idx_applications_submission_date", "submission_date"),
        db.Index("idx_applications_service_department", "service_id", "assigned_department_id"),
    )

    @property
    def payment_status(self):
        """Latest payment status. No payment row means nothing has been recorded."""
        if not self.payments:
            return None
        latest = max(self.payments, key=lambda payment: payment.payment_id)
        return latest.payment_status

    def __repr__(self):
        return f"<Application {self.application_id} {self.tracking_number}>"


class ApplicationEvent(db.Model):
    """Maps the existing application_tracking table. This model does not create a table."""

    __tablename__ = "application_tracking"

    tracking_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    application_id = db.Column(
        INTEGER(unsigned=True),
        db.ForeignKey("applications.application_id"),
        nullable=False,
    )
    previous_status = db.Column(db.Enum(*APPLICATION_STATUSES, name="application_status"))
    new_status = db.Column(db.Enum(*APPLICATION_STATUSES, name="application_status"), nullable=False)
    update_description = db.Column(db.String(500), nullable=False)
    updated_by = db.Column(INTEGER(unsigned=True), db.ForeignKey("users.user_id"))
    recorded_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )

    application = db.relationship("Application", foreign_keys=[application_id])

    __table_args__ = (
        db.Index("idx_application_tracking_application", "application_id"),
        db.Index("idx_application_tracking_recorded_at", "recorded_at"),
        db.Index("idx_application_tracking_updated_by", "updated_by"),
    )

    def __repr__(self):
        return f"<ApplicationEvent {self.tracking_id} application={self.application_id}>"


class ApplicationRequirement(db.Model):
    """Maps application_requirements. The column stores a file path, not the file."""

    __tablename__ = "application_requirements"

    requirement_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    application_id = db.Column(
        INTEGER(unsigned=True),
        db.ForeignKey("applications.application_id"),
        nullable=False,
    )
    requirement_name = db.Column(db.String(200), nullable=False)
    uploaded_file = db.Column(db.String(255))
    verification_status = db.Column(
        db.Enum("pending", "verified", "rejected", name="verification_status"),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    remarks = db.Column(db.String(500))

    application = db.relationship("Application", back_populates="requirements")

    __table_args__ = (
        db.Index("idx_application_requirements_application", "application_id"),
        db.Index("idx_application_requirements_status", "verification_status"),
    )

    def __repr__(self):
        return f"<ApplicationRequirement {self.requirement_id} {self.requirement_name}>"
