from functools import wraps
from flask import request, jsonify
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'No authorization header'}), 401

        try:
            # Extract token from "Bearer <token>"
            token = auth_header.split(' ')[1]
            # Decode the token
            payload = jwt.decode(
                token, 
                os.getenv('JWT_SECRET_KEY'), 
                algorithms=['HS256']
            )
            return f(payload, *args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
            
    return decorated

def get_forwarded_headers(request):
    """Forward relevant headers from the original request"""
    headers = {}
    if 'Authorization' in request.headers:
        headers['Authorization'] = request.headers['Authorization']
    return headers 