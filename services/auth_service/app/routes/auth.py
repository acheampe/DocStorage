from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User
import bcrypt
import jwt
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from functools import wraps
import traceback

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def jwt_required():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = None
            auth_header = request.headers.get('Authorization')
            
            print("Debug - Auth header:", auth_header)
            
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                print("Debug - Token found:", token[:20] + "...")
            
            if not token:
                print("Debug - No token found")
                return jsonify({'error': 'Token is missing'}), 401
            
            try:
                # Log the secret key being used (first few chars only)
                secret_key = os.getenv('SECRET_KEY')
                print("Debug - Secret key starts with:", secret_key[:10] if secret_key else None)
                
                # Try to decode the token
                payload = jwt.decode(token, secret_key, algorithms=['HS256'])
                print("Debug - Token successfully decoded")
                print("Debug - Token payload:", payload)
                
                current_user_id = payload.get('user_id')
                if not current_user_id:
                    print("Debug - No user_id in token payload")
                    return jsonify({'error': 'Invalid token structure'}), 401
                    
            except jwt.ExpiredSignatureError:
                print("Debug - Token expired")
                return jsonify({'error': 'Token has expired'}), 401
            except jwt.InvalidTokenError as e:
                print("Debug - Invalid token:", str(e))
                print("Debug - Token structure:", token.split('.') if token else None)
                return jsonify({'error': f'Invalid token: {str(e)}'}), 401
                
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

@auth_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(current_user_id, user_id):
    try:
        # Optionally verify that the requesting user has permission to view this user
        if current_user_id != user_id:
            return jsonify({'error': 'Unauthorized to view this user'}), 403
            
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        return jsonify({
            'user_id': user.user_id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }), 200
        
    except Exception as e:
        print(f"Error fetching user: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/users/by-email/<email>', methods=['GET'])
@jwt_required()
def get_user_by_email(current_user_id, email):
    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        return jsonify({
            'user_id': user.user_id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }), 200
        
    except Exception as e:
        print(f"Error fetching user by email: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/user/by-email', methods=['POST'])
def get_user_id_from_email():
    try:
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({'error': 'Email is required'}), 400
            
        user = User.query.filter_by(email=data['email']).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        return jsonify({
            'user_id': user.user_id,
            'email': user.email
        }), 200
        
    except Exception as e:
        print(f"Error in get_user_id_from_email: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/user/by-id', methods=['POST'])
def get_user_by_id():
    try:
        data = request.get_json()
        if not data or 'user_id' not in data:
            return jsonify({'error': 'User ID is required'}), 400
            
        user = User.query.get(data['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        return jsonify({
            'user_id': user.user_id,
            'email': user.email
        }), 200
        
    except Exception as e:
        print(f"Error in get_user_by_id: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/users/lookup', methods=['GET'])
@jwt_required()
def lookup_user(current_user_id):
    try:
        # Log request details
        print("Debug - Headers:", dict(request.headers))
        print(f"Debug - Current user ID: {current_user_id}")
        
        email = request.args.get('email')
        if not email:
            print("Debug - No email provided")
            return jsonify({'error': 'Email parameter is required'}), 400
            
        print(f"Debug - Looking up email: {email}")
            
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"Debug - No user found for email: {email}")
            return jsonify({'error': 'User not found'}), 404
            
        print(f"Debug - Found user: {user.user_id}")
        return jsonify({
            'user_id': user.user_id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }), 200
        
    except Exception as e:
        print(f"Debug - Lookup error: {str(e)}")
        print("Debug - Full traceback:", traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500