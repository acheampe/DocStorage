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
        
        # Check if share already exists
        existing_share = SharedDocument.query.filter_by(
            doc_id=data['doc_id'],
            owner_id=current_user['user_id'],
            recipient_id=data['recipient_id'],
            status='active'
        ).first()
        
        if existing_share:
            print("Share Service: Share already exists, returning existing share")
            return jsonify({
                'message': 'Document is already shared with this user',
                'share': existing_share.to_dict()
            }), 200
        
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
        print(f"Share Service: Fetching shares for recipient ID: {recipient_id}")
        
        shares = SharedDocument.query.filter_by(
            recipient_id=recipient_id,
            status='active'
        ).all()
        
        share_list = []
        for share in shares:
            share_dict = {
                'doc_id': share.doc_id,
                'original_filename': share.original_filename,
                'file_type': mimetypes.guess_type(share.original_filename)[0],
                'shared_date': share.shared_date.isoformat() if share.shared_date else None,
                'owner_id': share.owner_id,
                'recipient_id': share.recipient_id,
                'share_id': share.share_id,
                'file_path': str(share.file_path),
                'access_type': 'recipient'
            }
            share_list.append(share_dict)
            
        print(f"Share Service: Found {len(share_list)} shares")
        return jsonify({'shares': share_list}), 200
        
    except Exception as e:
        print(f"Share Service Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@share_bp.route('/share/shared-by-me', methods=['GET'])
@require_auth
def get_shared_by_me(current_user):
    try:
        owner_id = current_user['user_id']
        print(f"Share Service: Fetching shares by owner ID: {owner_id}")
        
        shares = SharedDocument.query.filter_by(
            owner_id=owner_id,
            status='active'
        ).all()
        
        share_list = []
        for share in shares:
            share_dict = {
                'doc_id': share.doc_id,
                'original_filename': share.original_filename,
                'file_type': mimetypes.guess_type(share.original_filename)[0],
                'shared_date': share.shared_date.isoformat() if share.shared_date else None,
                'owner_id': share.owner_id,
                'recipient_id': share.recipient_id,
                'share_id': share.share_id,
                'file_path': str(share.file_path),
                'access_type': 'owner'
            }
            share_list.append(share_dict)
            
        print(f"Share Service: Found {len(share_list)} shares")
        return jsonify({'shares': share_list}), 200
        
    except Exception as e:
        print(f"Share Service Error: {str(e)}")
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

@share_bp.route('/share/preview/<int:share_id>/content', methods=['GET'])
@require_auth
def get_shared_content(current_user, share_id):
    try:
        print(f"Share Service: Accessing content for share_id {share_id} by user {current_user['user_id']}")
        
        # Get the share record
        share = SharedDocument.query.filter_by(
            share_id=share_id,
            status='active'  # Only allow access to active shares
        ).first_or_404()
        
        print(f"Share Service: Found share record: owner_id={share.owner_id}, recipient_id={share.recipient_id}")
        
        # Check access rights
        user_id = int(current_user['user_id'])  # Ensure integer comparison
        has_access = (int(share.owner_id) == user_id or int(share.recipient_id) == user_id)
        print(f"Share Service: User {user_id} access check: {has_access}")
        print(f"Share Service: Types - user_id: {type(user_id)}, owner_id: {type(share.owner_id)}, recipient_id: {type(share.recipient_id)}")
        
        if not has_access:
            print(f"Share Service: Access denied for user {user_id}")
            return jsonify({
                'error': 'Access denied',
                'details': {
                    'user_id': user_id,
                    'owner_id': share.owner_id,
                    'recipient_id': share.recipient_id,
                    'share_id': share_id
                }
            }), 403

        # Get the file path
        file_path = Path(share.file_path)
        if not file_path.is_absolute():
            file_path = STORAGE_PATH / 'shared' / str(share.owner_id) / str(share.recipient_id) / f"{share.doc_id}_{share.original_filename}"
        
        print(f"Share Service: Attempting to serve file from: {file_path}")
        
        if not file_path.exists():
            print(f"Share Service: File not found at path: {file_path}")
            return jsonify({'error': 'File not found'}), 404

        # Get the file's mime type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = 'application/octet-stream'

        print(f"Share Service: Serving file with mime type: {mime_type}")
        return send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=False,
            download_name=share.original_filename
        )

    except Exception as e:
        print(f"Share Service Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@share_bp.route('/share/check-access/<int:doc_id>', methods=['GET'])
@require_auth
def check_file_access(current_user, doc_id):
    try:
        user_id = current_user['user_id']
        
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
            return jsonify({
                'has_access': False,
                'is_shared': False
            }), 200

        # Return success with share details
        return jsonify({
            'has_access': True,
            'is_shared': True,
            'access_type': 'owner' if share.owner_id == user_id else 'recipient',
            'share_id': share.share_id,
            'original_filename': share.original_filename
        }), 200

    except Exception as e:
        print(f"Error checking file access: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500 

# Add a new endpoint for thumbnails
@share_bp.route('/share/preview/<int:share_id>/thumbnail', methods=['GET'])
@require_auth
def get_shared_thumbnail(current_user, share_id):
    try:
        share = SharedDocument.query.filter_by(
            share_id=share_id,
            status='active'
        ).first_or_404()
        
        # Check access rights
        user_id = current_user['user_id']
        if user_id != share.owner_id and user_id != share.recipient_id:
            return jsonify({'error': 'Access denied'}), 403

        # Get the file path
        file_path = Path(share.file_path)
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404

        # Get the file's mime type
        mime_type = mimetypes.guess_type(str(file_path))[0]
        if not mime_type:
            mime_type = 'application/octet-stream'

        return send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=False
        )

    except Exception as e:
        print(f"Error serving shared thumbnail: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@share_bp.route('/share/file/<int:doc_id>/metadata', methods=['GET'])
@require_auth
def get_shared_file_metadata(current_user, doc_id):
    """
    Get metadata for a shared file (whether shared by or with the user).
    """
    try:
        user_id = current_user['user_id']
        
        # Find the share record where the user is either owner or recipient
        share = SharedDocument.query.filter(
            SharedDocument.doc_id == doc_id,
            SharedDocument.status == 'active',
            db.or_(
                SharedDocument.owner_id == user_id,
                SharedDocument.recipient_id == user_id
            )
        ).first()

        if not share:
            return jsonify({'error': 'Shared document not found'}), 404
            
        # Return metadata as JSON
        return jsonify({
            'doc_id': share.doc_id,
            'original_filename': share.original_filename,
            'file_path': share.file_path,
            'file_type': mimetypes.guess_type(share.original_filename)[0],
            'shared_date': share.shared_date.isoformat() if share.shared_date else None,
            'owner_id': share.owner_id,
            'recipient_id': share.recipient_id,
            'share_id': share.share_id,
            'access_type': 'owner' if share.owner_id == user_id else 'recipient'
        })
        
    except Exception as e:
        print(f"Error retrieving shared document metadata: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500 

@share_bp.route('/share/file/metadata', methods=['GET'])
@require_auth
def get_all_shared_file_metadata(current_user):
    """
    Get metadata for all files shared with or by the user
    """
    try:
        user_id = current_user['user_id']
        
        # Find all shares where user is either owner or recipient
        shares = SharedDocument.query.filter(
            SharedDocument.status == 'active',
            db.or_(
                SharedDocument.owner_id == user_id,
                SharedDocument.recipient_id == user_id
            )
        ).all()

        files_metadata = []
        for share in shares:
            metadata = {
                'doc_id': share.doc_id,
                'original_filename': share.original_filename,
                'file_path': share.file_path,
                'file_type': mimetypes.guess_type(share.original_filename)[0],
                'shared_date': share.shared_date.isoformat() if share.shared_date else None,
                'owner_id': share.owner_id,
                'recipient_id': share.recipient_id,
                'share_id': share.share_id,
                'access_type': 'owner' if share.owner_id == user_id else 'recipient'
            }
            files_metadata.append(metadata)
            
        return jsonify({
            'files': files_metadata,
            'total': len(files_metadata)
        }), 200
        
    except Exception as e:
        print(f"Error retrieving shared files metadata: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500 

@share_bp.route('/share/debug/list-all', methods=['GET'])
@require_auth
def debug_list_all_shares(current_user):
    try:
        all_shares = SharedDocument.query.all()
        shares_data = [{
            'share_id': s.share_id,
            'doc_id': s.doc_id,
            'owner_id': s.owner_id,
            'recipient_id': s.recipient_id,
            'status': s.status,
            'file_path': s.file_path,
            'original_filename': s.original_filename
        } for s in all_shares]
        
        return jsonify({
            'total_shares': len(shares_data),
            'shares': shares_data
        }), 200
    except Exception as e:
        print(f"Error in debug list: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500 