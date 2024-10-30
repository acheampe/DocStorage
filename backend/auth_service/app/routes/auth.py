from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User
import bcrypt
import jwt
import os
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

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
        'exp': datetime.utcnow() + timedelta(days=1)
    }, os.getenv('SECRET_KEY'))
    
    return jsonify({
        'token': token,
        'user': user.to_dict()
    }), 200

# Update Profile
@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    # Get token from header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid token'}), 401
    
    token = auth_header.split(' ')[1]
    try:
        # Verify token and get user_id
        payload = jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=['HS256'])
        user_id = payload['user_id']
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token has expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

    # Get user from database
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    
    # Update basic info
    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    
    # Update email (with validation)
    if 'email' in data:
        if User.query.filter(User.email == data['email'], User.user_id != user_id).first():
            return jsonify({'error': 'Email already in use'}), 400
        user.email = data['email']
    
    # Update password with confirmation
    if 'password' in data:
        if not all(key in data for key in ['current_password', 'password', 'password_confirmation']):
            return jsonify({'error': 'Current password and password confirmation required'}), 400
            
        if data['password'] != data['password_confirmation']:
            return jsonify({'error': 'New passwords do not match'}), 400
            
        if len(data['password']) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        # Verify current password
        if not bcrypt.checkpw(
            data['current_password'].encode('utf-8'),
            user.hashed_password.encode('utf-8')
        ):
            return jsonify({'error': 'Invalid current password'}), 401
        
        # Hash and set new password
        hashed_password = bcrypt.hashpw(
            data['password'].encode('utf-8'),
            bcrypt.gensalt()
        )
        user.hashed_password = hashed_password.decode('utf-8')

    db.session.commit()
    return jsonify({'message': 'Profile updated successfully', 'user': user.to_dict()}), 200