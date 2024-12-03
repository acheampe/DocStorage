from flask import request, jsonify, current_app
from app import db
from app.models.share import SharedDocument
from app.utils.auth import require_auth
from app.routes import share_bp
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import logging
import os
import requests
import traceback
from sqlalchemy import text

@share_bp.route('/share', methods=['POST'])
@require_auth
def create_share(current_user):
    try:
        print("Share Service: Starting share creation...")
        
        data = request.get_json()
        print(f"Share Service: Parsed JSON data: {data}")
        
        # Validate required fields
        required_fields = ['doc_id', 'recipient_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Fetch original filename from doc management service
        gateway_url = os.getenv('GATEWAY_URL', 'http://localhost:5000')
        doc_response = requests.get(
            f"{gateway_url}/docs/file/{data['doc_id']}",
            headers={'Authorization': request.headers.get('Authorization')}
        )
        
        if doc_response.status_code != 200:
            return jsonify({'error': 'Failed to fetch document details'}), 400
            
        doc_data = doc_response.json()
        original_filename = doc_data.get('filename', f"Document {data['doc_id']}")
        
        # Create a unique path under DocStorageDocuments directory
        file_path = f"DocStorageDocuments/shared/{current_user['user_id']}/{data['recipient_id']}/{data['doc_id']}"
        
        try:
            # Create share with application context
            with current_app.app_context():
                share = SharedDocument(
                    doc_id=data['doc_id'],
                    owner_id=current_user['user_id'],
                    recipient_id=data['recipient_id'],
                    display_name=data.get('display_name', original_filename),
                    original_filename=original_filename,
                    file_path=file_path,  # Use the path under DocStorageDocuments
                    expiry_date=data.get('expiry_date'),
                    status='active'
                )
                
                db.session.add(share)
                db.session.commit()
                
                result = share.to_dict()
                print(f"Share Service: Successfully created share: {result}")
                return jsonify(result), 201
                
        except Exception as db_error:
            print(f"Share Service: Database error: {str(db_error)}")
            db.session.rollback()
            traceback.print_exc()
            return jsonify({'error': f'Database error: {str(db_error)}'}), 500
            
    except Exception as e:
        print(f"Share Service Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@share_bp.route('/share/shared-with-me', methods=['GET'])
@require_auth
def get_shared_with_me(current_user):
    try:
        recipient_id = request.args.get('recipient_id')
        if not recipient_id:
            return jsonify({'error': 'Recipient ID is required'}), 400
            
        print(f"Fetching shares for recipient ID: {recipient_id}")
            
        shares = SharedDocument.query.filter_by(
            recipient_id=recipient_id,
            status='active'
        ).all()
        share_list = []
        
        # Get document details through gateway
        gateway_url = os.getenv('GATEWAY_URL', 'http://localhost:5000')
        
        for share in shares:
            share_dict = share.to_dict()
            
            # Fetch document metadata through gateway
            doc_response = requests.get(
                f"{gateway_url}/docs/file/{share.doc_id}",
                headers={'Authorization': request.headers.get('Authorization')}
            )
            
            if doc_response.status_code == 200:
                doc_data = doc_response.json()
                share_dict.update({
                    'filename': doc_data.get('filename', f"Document {share.doc_id}"),
                    'mime_type': doc_data.get('mime_type'),
                    'file_size': doc_data.get('file_size')
                })
            else:
                share_dict['filename'] = f"Document {share.doc_id}"
                
            share_list.append(share_dict)
            
        return jsonify({'shares': share_list}), 200
    except Exception as e:
        print(f"Error in get_shared_with_me: {str(e)}")
        return jsonify({'error': str(e)}), 500

@share_bp.route('/share/shared-by-me', methods=['GET'])
@jwt_required()
def get_shared_by_me():
    try:
        owner_id = request.args.get('owner_id')
        if not owner_id:
            return jsonify({'error': 'Owner ID is required'}), 400
            
        print(f"Fetching shares by owner ID: {owner_id}")
            
        shares = SharedDocument.query.filter_by(
            owner_id=owner_id,
            status='active'
        ).all()
        share_list = []
        
        for share in shares:
            share_dict = share.to_dict()
            share_list.append(share_dict)
            
        return jsonify({'shares': share_list}), 200
    except Exception as e:
        print(f"Error in get_shared_by_me: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@share_bp.route('/share/<int:share_id>', methods=['PATCH'])
def update_share(share_id):
    share = SharedDocument.query.get_or_404(share_id)
    data = request.get_json()
    
    # Only allow updating display_name and expiry_date
    if 'display_name' in data:
        share.display_name = data['display_name']
    if 'expiry_date' in data:
        share.expiry_date = data['expiry_date']
        
    db.session.commit()
    return jsonify(share.to_dict()) 

@share_bp.route('/health', methods=['GET'])
def health_check():
    try:
        # Test database connection with proper SQL text handling
        with current_app.app_context():
            db.session.execute(text('SELECT 1'))
            db.session.commit()
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        print(f"Health check failed: {str(e)}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@share_bp.route('/test', methods=['GET'])
def test_endpoint():
    return jsonify({'status': 'Share service is running'}), 200 