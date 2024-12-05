from flask import request, jsonify, current_app, send_file, make_response
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
from pathlib import Path
import shutil
import mimetypes
from flask_cors import cross_origin

# Get storage path from environment variable, with a default fallback
STORAGE_PATH = Path(os.getenv('STORAGE_PATH', 'DocStorageDocuments')).resolve()

@share_bp.route('/share', methods=['POST'])
@require_auth
def create_share(current_user):
    try:
        print("Share Service: Starting share creation...")
        
        data = request.get_json()
        print(f"Share Service: Parsed JSON data: {data}")
        
        # Validate required fields
        required_fields = ['doc_id', 'recipient_id', 'document_metadata']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Use document metadata from the request
        doc_metadata = data['document_metadata']
        original_filename = doc_metadata.get('original_filename', f"Document {data['doc_id']}")
        source_path = f"../../DocStorageDocuments/{doc_metadata['file_path']}"
        
        # Create shared file path using Path
        shared_file_path = (STORAGE_PATH / 'shared' / 
                          str(current_user['user_id']) / 
                          str(data['recipient_id']) / 
                          f"{data['doc_id']}_{original_filename}")
        
        # Ensure the directory structure exists
        shared_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy the file
        try:
            shutil.copy2(source_path, shared_file_path)
            print(f"Share Service: File copied from {source_path} to {shared_file_path}")
        except Exception as copy_error:
            print(f"Share Service: Error copying file: {str(copy_error)}")
            return jsonify({'error': f'File copy failed: {str(copy_error)}'}), 500
        
        try:
            # Create share with application context
            with current_app.app_context():
                share = SharedDocument(
                    doc_id=data['doc_id'],
                    owner_id=current_user['user_id'],
                    recipient_id=data['recipient_id'],
                    display_name=data.get('display_name', original_filename),
                    original_filename=original_filename,
                    file_path=str(shared_file_path),  # Convert PosixPath to string
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
        recipient_id = current_user['user_id']
        print(f"Fetching shares for recipient ID: {recipient_id}")
            
        shares = SharedDocument.query.filter_by(
            recipient_id=recipient_id,
            status='active'
        ).all()
        
        print(f"Found {len(shares)} shares for recipient")
        share_list = []
        
        for share in shares:
            share_dict = share.to_dict()
            # Use the original_filename from SharedDocument table
            share_dict.update({
                'filename': share.original_filename,  # Use this instead of generic "Document X"
                'doc_id': share.doc_id,
                'owner_id': share.owner_id,
                'shared_date': share.shared_date.isoformat() if share.shared_date else None,
                'file_path': share.file_path  # Include file_path for preview/thumbnail
            })
            share_list.append(share_dict)
            
        return jsonify({'shares': share_list}), 200
        
    except Exception as e:
        print(f"Error in get_shared_with_me: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@share_bp.route('/share/shared-by-me', methods=['GET'])
@require_auth  # Change to require_auth to be consistent
def get_shared_by_me(current_user):
    try:
        owner_id = current_user['user_id']  # Use the authenticated user's ID directly
        print(f"Fetching shares by owner ID: {owner_id}")
            
        shares = SharedDocument.query.filter_by(
            owner_id=owner_id,
            status='active'
        ).all()
        
        print(f"Found {len(shares)} shares by owner")
        share_list = []
        
        # Get document details through gateway
        gateway_url = os.getenv('GATEWAY_URL', 'http://localhost:5000')
        
        for share in shares:
            share_dict = share.to_dict()
            print(f"Processing share: {share_dict}")
            
            # Fetch document metadata through gateway
            doc_response = requests.get(
                f"{gateway_url}/docs/file/{share.doc_id}",
                headers={'Authorization': request.headers.get('Authorization')}
            )
            
            if doc_response.status_code == 200:
                doc_data = doc_response.json()
                share_dict.update({
                    'filename': doc_data.get('original_filename', f"Document {share.doc_id}"),
                    'file_type': doc_data.get('file_type'),
                    'doc_id': share.doc_id
                })
            else:
                print(f"Failed to fetch document metadata: Status {doc_response.status_code}")
                share_dict.update({
                    'filename': f"Document {share.doc_id}",
                    'doc_id': share.doc_id
                })
                
            share_list.append(share_dict)
            
        return jsonify({'shares': share_list}), 200
        
    except Exception as e:
        print(f"Error in get_shared_by_me: {str(e)}")
        traceback.print_exc()
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

@share_bp.route('/share/preview/<int:doc_id>', methods=['GET'])
@require_auth
def preview_shared_file(current_user, doc_id):
    """
    This endpoint is used to preview a shared file and to download a shared file.
    """
    try:
        # First check if user is the owner of this shared file
        owner_share = SharedDocument.query.filter_by(
            doc_id=doc_id,
            owner_id=current_user['user_id'],
            status='active'
        ).first()
        
        if owner_share:
            # If user is owner, use the original file path
            gateway_url = os.getenv('GATEWAY_URL', 'http://localhost:5000')
            response = requests.get(
                f"{gateway_url}/docs/preview/{doc_id}",
                headers={'Authorization': request.headers.get('Authorization')}
            )
            
            if response.status_code != 200:
                return jsonify({'error': 'Failed to fetch file from docs service'}), response.status_code
                
            return response.content, response.status_code, response.headers.items()
            
        # If not owner, check if user is recipient
        recipient_share = SharedDocument.query.filter_by(
            doc_id=doc_id,
            recipient_id=current_user['user_id'],
            status='active'
        ).first()
        
        if not recipient_share:
            print(f"No active share found for doc_id {doc_id} and user {current_user['user_id']}")
            return jsonify({'error': 'File not found or no access'}), 404

        # Get the file path and resolve it properly
        file_path = Path(recipient_share.file_path)
        if not file_path.is_absolute():
            file_path = STORAGE_PATH / 'shared' / str(recipient_share.owner_id) / str(recipient_share.recipient_id) / f"{doc_id}_{recipient_share.original_filename}"
        
        print(f"Attempting to serve file from: {file_path}")
        
        if not file_path.exists():
            print(f"File not found at path: {file_path}")
            return jsonify({'error': 'File not found'}), 404

        # Get the file's mime type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = 'application/octet-stream'

        return send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=False,
            download_name=recipient_share.original_filename
        )

    except Exception as e:
        print(f"Error in preview_shared_file: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500 

@share_bp.route('/share/check-access/<int:doc_id>', methods=['GET'])
@require_auth
def check_file_access(current_user, doc_id):
    try:
        user_id = current_user['user_id']
        print(f"Checking access for doc_id {doc_id} and user {user_id}")

        # Check if user is either owner or recipient of the shared document
        share = SharedDocument.query.filter(
            SharedDocument.doc_id == doc_id,
            SharedDocument.status == 'active',
            db.or_(
                SharedDocument.owner_id == user_id,
                SharedDocument.recipient_id == user_id
            )
        ).first()

        if not share:
            print(f"No active share found for doc_id {doc_id} and user {user_id}")
            return jsonify({
                'error': 'Access denied',
                'has_access': False
            }), 403

        # Return success with share details
        return jsonify({
            'has_access': True,
            'access_type': 'owner' if share.owner_id == user_id else 'recipient',
            'share_id': share.share_id,
            'original_filename': share.original_filename
        }), 200

    except Exception as e:
        print(f"Error checking file access: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500 