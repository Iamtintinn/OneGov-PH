from sqlalchemy.dialects.mysql import INTEGER

from app import db


class Department(db.Model):
    """Maps the existing departments table. This model does not create a table."""

    __tablename__ = "departments"

    department_id = db.Column(INTEGER(unsigned=True), primary_key=True)
    department_name = db.Column(db.String(150), nullable=False, unique=True)
    department_description = db.Column(db.Text)
    department_status = db.Column(
        db.Enum("active", "inactive", name="department_status"),
        nullable=False,
    )

    def __repr__(self):
        return f"<Department {self.department_id} {self.department_name}>"
