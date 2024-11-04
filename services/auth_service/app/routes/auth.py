from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User
import bcrypt
import jwt
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def jwt_required():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = None
            auth_header = request.headers.get('Authorization')
            
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            
            if not token:
                return jsonify({'error': 'Token is missing'}), 401
            
            try:
                payload = jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=['HS256'])
                current_user_id = payload['user_id']
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token has expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'Invalid token'}), 401
                
            return f(*args, current_user_id=current_user_id, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    hashed_password = bcrypt.hashpw(
        data['password'].encode('utf-8'), 
        bcrypt.gensalt()
    )
    
    new_user = User(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        hashed_password=hashed_password.decode('utf-8')
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not bcrypt.checkpw(
        data['password'].encode('utf-8'), 
        user.hashed_password.encode('utf-8')
    ):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    token = jwt.encode({
        'user_id': user.user_id,
        'exp': datetime.now(timezone.utc) + timedelta(days=1)
    }, os.getenv('SECRET_KEY'))
    
    return jsonify({
        'token': token,
        'user': user.to_dict()
    }), 200

# Update Profile
@auth_bp.route('/update-profile', methods=['PUT'])
@jwt_required()
def update_profile(current_user_id):
    data = request.get_json()

    # Verify required fields
    required_fields = ['first_name', 'last_name', 'email', 'old_password']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        # Get user from database
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Verify old password using bcrypt
        if not bcrypt.checkpw(
            data['old_password'].encode('utf-8'),
            user.hashed_password.encode('utf-8')
        ):
            return jsonify({'error': 'Current password is incorrect'}), 401

        # Update user information
        user.first_name = data['first_name']
        user.last_name = data['last_name']
        user.email = data['email']

        # Update password if provided
        if data.get('new_password'):
            new_hashed_password = bcrypt.hashpw(
                data['new_password'].encode('utf-8'),
                bcrypt.gensalt()
            )
            user.hashed_password = new_hashed_password.decode('utf-8')

        db.session.commit()

        # Return updated user info
        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'user_id': user.user_id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email
            }
        }), 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Email already exists'}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500