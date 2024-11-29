from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
import os
import magic
import jwt
from datetime import datetime
from ..models.document import Document
from ..extensions import db
from flask_cors import cross_origin

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

@docs_bp.route('/upload', methods=['POST', 'OPTIONS'])
def upload_document():
    if request.method == 'OPTIONS':
        return '', 200
        
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    if 'files[]' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files[]')
    if not files or all(file.filename == '' for file in files):
        return jsonify({'error': 'No files selected'}), 400

    uploaded_documents = []
    errors = []

    for file in files:
        if not allowed_file(file.filename):
            errors.append(f"{file.filename}: File type not allowed")
            continue

        if file.content_length and file.content_length > MAX_FILE_SIZE:
            errors.append(f"{file.filename}: File size exceeds maximum limit")
            continue

        try:
            filename = secure_filename(file.filename)
            user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(user_id))
            os.makedirs(user_folder, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(user_folder, unique_filename)
            
            file.save(file_path)
            
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(file_path)
            
            relative_path = os.path.join(str(user_id), unique_filename)
            
            document = Document(
                filename=unique_filename,
                original_filename=filename,
                file_type=file_type,
                file_size=os.path.getsize(file_path),
                file_path=relative_path,
                user_id=user_id,
                description=request.form.get('description', ''),
                upload_date=datetime.utcnow(),
                last_modified=datetime.utcnow()
            )
            
            db.session.add(document)
            db.session.commit()
            uploaded_documents.append(document.to_dict())
            
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
            db.session.rollback()
            continue

    response_data = {
        'uploaded_documents': uploaded_documents,
        'errors': errors if errors else None
    }

    # Return 201 if at least one file was uploaded successfully
    status_code = 201 if uploaded_documents else 500
    return jsonify(response_data), status_code

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

@docs_bp.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response
