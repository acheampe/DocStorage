from flask import Blueprint, jsonify
from ..extensions import db
from sqlalchemy import text
from .auth import auth_bp

main_bp = Blueprint('main', __name__)

@main_bp.route('/health')
def health_check():
    try:
        # Test database connection
        db.session.execute(text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 500