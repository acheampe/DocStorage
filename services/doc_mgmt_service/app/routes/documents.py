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
    # Check Authorization header first
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
    else:
        # Check query parameters
        token = request.args.get('token')
        if not token:
            return None
    
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

        try:
            filename = secure_filename(file.filename)
            user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(user_id))
            os.makedirs(user_folder, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(user_folder, unique_filename)
            
            # Save the file
            file.save(file_path)
            
            # Get file type and size
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(file_path)
            file_size = os.path.getsize(file_path)
            
            # Store relative path
            relative_path = os.path.join(str(user_id), unique_filename)
            
            # Create document record
            document = Document(
                filename=unique_filename,
                original_filename=filename,
                file_type=file_type,
                file_size=file_size,
                file_path=relative_path,
                user_id=user_id,
                description=request.form.get('description', ''),
                upload_date=datetime.utcnow(),
                last_modified=datetime.utcnow()
            )
            
            db.session.add(document)
            db.session.commit()
            
            uploaded_documents.append({
                'doc_id': document.doc_id,
                'filename': document.original_filename,
                'file_type': document.file_type
            })
            
        except Exception as e:
            print(f"Error uploading {file.filename}: {str(e)}")
            errors.append(f"{file.filename}: Upload failed")
            # Rollback the session for this file
            db.session.rollback()
            # Try to clean up the file if it was saved
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass

    # Determine response based on results
    if not uploaded_documents and errors:
        # All files failed
        return jsonify({
            'error': 'All uploads failed',
            'errors': errors
        }), 400
    elif errors:
        # Some files succeeded, some failed
        return jsonify({
            'message': 'Some files uploaded successfully',
            'uploaded': uploaded_documents,
            'errors': errors
        }), 201
    else:
        # All files succeeded
        return jsonify({
            'message': 'All files uploaded successfully',
            'uploaded': uploaded_documents
        }), 201

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

@docs_bp.route('/recent', methods=['GET'])
def get_recent_documents():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        documents = Document.query.filter_by(user_id=user_id)\
            .order_by(Document.upload_date.desc())\
            .limit(6)\
            .all()
        
        return jsonify({
            'files': [doc.to_dict() for doc in documents]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@docs_bp.route('/file/<int:doc_id>', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_file(doc_id):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=['HS256'])
        user_id = payload['user_id']
        
        document = Document.query.filter_by(doc_id=doc_id, user_id=user_id).first()
        if not document:
            return jsonify({'error': 'File not found'}), 404

        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], str(user_id), document.filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404

        response = send_file(
            file_path,
            mimetype=document.file_type,
            as_attachment=False,
            download_name=document.original_filename
        )
        
        # Add CORS headers
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response

    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        print(f"Error serving file: {str(e)}")
        return jsonify({'error': 'Failed to serve file'}), 500

@docs_bp.route('/documents/<int:doc_id>', methods=['PATCH', 'OPTIONS'])
@cross_origin(
    origins=["http://localhost:3000"],
    methods=['PATCH', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization'],
    supports_credentials=True
)
def update_document(doc_id):
    if request.method == 'OPTIONS':
        response = current_app.make_default_options_response()
        response.headers['Access-Control-Allow-Methods'] = 'PATCH'
        return response
        
    print(f"Received PATCH request for document {doc_id}")  # Debug log
    user_id = get_user_id_from_token()
    print(f"User ID from token: {user_id}")  # Debug log
    
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    document = Document.query.filter_by(doc_id=doc_id, user_id=user_id).first()
    print(f"Found document: {document}")  # Debug log
    
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    try:
        data = request.get_json()
        print(f"Received data: {data}")  # Debug log
        new_filename = data.get('filename')
        
        if not new_filename:
            return jsonify({'error': 'New filename is required'}), 400

        # Update the file in local storage
        old_file_path = os.path.join(UPLOAD_FOLDER, str(user_id), document.filename)
        new_filename_with_timestamp = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(new_filename)}"
        new_file_path = os.path.join(UPLOAD_FOLDER, str(user_id), new_filename_with_timestamp)

        print(f"Old path: {old_file_path}")  # Debug log
        print(f"New path: {new_file_path}")  # Debug log

        if os.path.exists(old_file_path):
            os.rename(old_file_path, new_file_path)
            
            # Update database record
            document.original_filename = new_filename
            document.filename = new_filename_with_timestamp
            document.last_modified = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'message': 'Document updated successfully',
                'document': document.to_dict()
            }), 200
        else:
            return jsonify({'error': 'File not found in storage'}), 404

    except Exception as e:
        print(f"Error during rename: {str(e)}")  # Debug log
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
