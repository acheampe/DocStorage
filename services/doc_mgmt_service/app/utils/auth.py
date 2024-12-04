from functools import wraps
from flask import request, jsonify
import jwt
import os

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        print(f"Auth header received: {auth_header}")
        
        if not auth_header or not auth_header.startswith('Bearer '):
            print("No valid auth header found")
            return jsonify({'error': 'No token provided'}), 401

        token = auth_header.split(' ')[1]
        try:
            current_user = jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=['HS256'])
            print(f"Decoded user: {current_user}")
            return f(current_user=current_user, *args, **kwargs)
        except jwt.InvalidTokenError as e:
            print(f"Token validation failed: {str(e)}")
            return jsonify({'error': 'Invalid token'}), 401

    return decorated 