from flask import request, jsonify, current_app
from app import db
from app.models.share import SharedDocument
from app.utils.auth import require_auth
from app.routes import share_bp
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import logging
import os
import requests

@share_bp.route('/share', methods=['POST'])
@require_auth
def create_share(current_user):
    try:
        data = request.get_json()
        logging.debug(f"Received share request data: {data}")
        
        # Create share with application context
        with current_app.app_context():
            share = SharedDocument(
                doc_id=data['doc_id'],
                owner_id=current_user['user_id'],
                recipient_email=data['recipient_email'],
                can_view=data['permissions'].get('can_view', True),
                can_download=data['permissions'].get('can_download', False),
                can_reshare=data['permissions'].get('can_reshare', False)
            )
            
            db.session.add(share)
            db.session.commit()
            
        return jsonify({'message': 'Share created successfully'}), 201
        
    except Exception as e:
        logging.error(f"Share error: {str(e)}")
        logging.error(f"Full traceback:", exc_info=True)
        return jsonify({'error': f'Failed to create share: {str(e)}'}), 500

@share_bp.route('/share/shared-with-me', methods=['GET'])
@require_auth
def get_shared_with_me(current_user):
    try:
        recipient_email = request.args.get('recipient_email')
        if not recipient_email:
            return jsonify({'error': 'Recipient email is required'}), 400
            
        print(f"Fetching shares for user email: {recipient_email}")
            
        shares = SharedDocument.query.filter_by(recipient_email=recipient_email).all()
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
            
        print(f"Fetching shares by user ID: {owner_id}")
            
        shares = SharedDocument.query.filter_by(owner_id=owner_id).all()
        share_list = []
        
        for share in shares:
            share_dict = share.to_dict()
            share_list.append(share_dict)
            
        return jsonify({'shares': share_list}), 200
    except Exception as e:
        print(f"Error in get_shared_by_me: {str(e)}")
        return jsonify({'error': str(e)}), 500 