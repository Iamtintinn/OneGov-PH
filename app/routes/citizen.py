from flask import Blueprint, render_template

from app.models.user import User
from app.utils.decorators import role_required

citizen_bp = Blueprint("citizen", __name__)


@citizen_bp.route("/citizen/dashboard")
@role_required(User.ROLE_CITIZEN)
def dashboard():
    return render_template("citizen/dashboard.html")
