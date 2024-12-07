from functools import wraps
from flask import request, jsonify
import jwt
import os

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            print("DEBUG - Starting token verification")
            auth_header = request.headers.get('Authorization')
            print("DEBUG - Authorization header:", auth_header)
            
            if not auth_header or not auth_header.startswith('Bearer '):
                raise Exception("No valid authorization header")
                
            token = auth_header.split(' ')[1]
            secret_key = os.getenv('SECRET_KEY')
            
            # Manually decode the token
            decoded = jwt.decode(token, secret_key, algorithms=['HS256'])
            print("DEBUG - Decoded token:", decoded)
            
            # Get user_id from either sub or user_id claim
            user_id = decoded.get('sub') or decoded.get('user_id')
            print("DEBUG - Extracted user_id:", user_id)
            
            if not user_id:
                raise Exception("No user identifier found in token")
                
            current_user = {
                'user_id': user_id,
                'email': decoded.get('email')
            }
            print("DEBUG - Current user:", current_user)
            
            return f(current_user=current_user, *args, **kwargs)
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            print(f"Error type: {type(e)}")
            return jsonify({'error': f'Authentication failed: {str(e)}'}), 401
    return decorated 