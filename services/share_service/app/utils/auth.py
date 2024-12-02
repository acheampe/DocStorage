from functools import wraps
from flask import request, jsonify
import requests

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'No authorization header'}), 401

        try:
            # Verify token through API gateway instead of direct service call
            auth_response = requests.get(
                'http://127.0.0.1:5000/auth/verify',
                headers={'Authorization': auth_header}
            )
            
            if not auth_response.ok:
                return jsonify({'error': 'Invalid token'}), 401

            current_user = auth_response.json()
            return f(current_user=current_user, *args, **kwargs)

        except requests.exceptions.RequestException:
            return jsonify({'error': 'Gateway unavailable'}), 503

    return decorated 