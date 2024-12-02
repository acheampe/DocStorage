from flask import Blueprint, request, jsonify
from app.models.share import db, SharedDocument
from app.utils.auth import require_auth
from datetime import datetime
import requests

shares = Blueprint('shares', __name__)

@shares.route('/share', methods=['POST'])
@require_auth
def share_document(current_user):
    try:
        data = request.get_json()
        doc_id = data.get('doc_id')
        recipient_email = data.get('recipient_email')
        permissions = data.get('permissions', {
            "can_view": True,
            "can_download": False,
            "can_reshare": False
        })
        expiry_date = data.get('expiry_date')

        # Verify recipient exists via API gateway
        auth_response = requests.get(
            f'http://127.0.0.1:5000/auth/user/email/{recipient_email}',
            headers=request.headers
        )
        
        if not auth_response.ok:
            return jsonify({'error': 'Recipient not found'}), 404
            
        recipient_data = auth_response.json()
        recipient_id = recipient_data['user_id']

        # Verify document exists via API gateway
        doc_response = requests.get(
            f'http://127.0.0.1:5000/docs/documents/{doc_id}',
            headers=request.headers
        )
        
        if not doc_response.ok:
            return jsonify({'error': 'Document not found'}), 404

        # Check if share already exists
        existing_share = SharedDocument.query.filter_by(
            doc_id=doc_id,
            owner_id=current_user['user_id'],
            recipient_id=recipient_id,
            status='active'
        ).first()

        if existing_share:
            return jsonify({'error': 'Document already shared with this user'}), 409

        # Create new share
        new_share = SharedDocument(
            doc_id=doc_id,
            owner_id=current_user['user_id'],
            recipient_id=recipient_id,
            permissions=permissions,
            expiry_date=datetime.fromisoformat(expiry_date) if expiry_date else None
        )

        db.session.add(new_share)
        db.session.commit()

        return jsonify(new_share.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@shares.route('/share/<int:share_id>', methods=['DELETE'])
@require_auth
def revoke_share(current_user, share_id):
    try:
        share = SharedDocument.query.get_or_404(share_id)
        
        # Verify ownership
        if share.owner_id != current_user['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403

        share.status = 'revoked'
        db.session.commit()

        return jsonify({'message': 'Share revoked successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@shares.route('/shared-with-me', methods=['GET'])
@require_auth
def get_shared_with_me(current_user):
    try:
        shares = SharedDocument.query.filter_by(
            recipient_id=current_user['user_id'],
            status='active'
        ).all()
        
        return jsonify([share.to_dict() for share in shares]), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shares.route('/shared-by-me', methods=['GET'])
@require_auth
def get_shared_by_me(current_user):
    try:
        shares = SharedDocument.query.filter_by(
            owner_id=current_user['user_id']
        ).all()
        
        return jsonify([share.to_dict() for share in shares]), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shares.route('/share/<int:share_id>/permissions', methods=['PATCH'])
@require_auth
def update_permissions(current_user, share_id):
    try:
        share = SharedDocument.query.get_or_404(share_id)
        
        # Verify ownership
        if share.owner_id != current_user['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        new_permissions = data.get('permissions')
        
        if not new_permissions:
            return jsonify({'error': 'No permissions provided'}), 400

        share.permissions = new_permissions
        share.last_accessed = datetime.utcnow()
        db.session.commit()

        return jsonify(share.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 