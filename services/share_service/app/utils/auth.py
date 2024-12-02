from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
import jwt
import os

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            claims = get_jwt()
            current_user = {
                'user_id': claims.get('sub'),  # Get user_id from sub claim
                'email': claims.get('email')   # Get email if present
            }
            return f(current_user=current_user, *args, **kwargs)
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return jsonify({'error': f'Authentication failed: {str(e)}'}), 401
    return decorated 