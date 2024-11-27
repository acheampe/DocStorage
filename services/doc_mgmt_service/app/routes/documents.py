from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import magic
import jwt
from datetime import datetime
from ..models.document import Document
from ..extensions import db

docs_bp = Blueprint('documents', __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), 'DocStorageDocuments')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def get_user_id_from_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=['HS256'])
        return payload['user_id']
    except jwt.InvalidTokenError:
        return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@docs_bp.route('/upload', methods=['POST'])
def upload_document():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    if file.content_length and file.content_length > MAX_FILE_SIZE:
        return jsonify({'error': 'File size exceeds maximum limit'}), 400

    try:
        filename = secure_filename(file.filename)
        user_folder = os.path.join(UPLOAD_FOLDER, str(user_id))
        os.makedirs(user_folder, exist_ok=True)
        
        # Create unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(user_folder, unique_filename)
        
        file.save(file_path)
        
        # Get file type using python-magic
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file_path)
        
        # Create document record
        document = Document(
            filename=unique_filename,
            original_filename=filename,
            file_type=file_type,
            file_size=os.path.getsize(file_path),
            user_id=user_id,
            description=request.form.get('description', '')
        )
        
        db.session.add(document)
        db.session.commit()
        
        return jsonify(document.to_dict()), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@docs_bp.route('/documents', methods=['GET'])
def get_user_documents():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    documents = Document.query.filter_by(user_id=user_id).all()
    return jsonify([doc.to_dict() for doc in documents]), 200

@docs_bp.route('/documents/<int:doc_id>', methods=['GET'])
def download_document(doc_id):
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    document = Document.query.filter_by(doc_id=doc_id, user_id=user_id).first()
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    file_path = os.path.join(UPLOAD_FOLDER, str(user_id), document.filename)
    return send_file(file_path, as_attachment=True, download_name=document.original_filename)

@docs_bp.route('/documents/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    document = Document.query.filter_by(doc_id=doc_id, user_id=user_id).first()
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    try:
        file_path = os.path.join(UPLOAD_FOLDER, str(user_id), document.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({'message': 'Document deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
