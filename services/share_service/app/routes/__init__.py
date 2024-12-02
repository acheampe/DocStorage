from flask import Blueprint

share_bp = Blueprint('share', __name__)

from . import shares  # This imports the routes 