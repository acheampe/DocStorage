from flask import Blueprint, request, jsonify, send_file, current_app, make_response
from werkzeug.utils import secure_filename
import os
import magic
import jwt
from datetime import datetime
from ..models.document import Document
from ..extensions import db
from flask_cors import cross_origin
from pdf2image import convert_from_path
from docx import Document as DocxDocument
from wand.image import Image as WandImage
import io
from PIL import Image
import traceback
from io import BytesIO
import logging
import requests

logger = logging.getLogger(__name__)

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

def generate_pdf_thumbnail(pdf_path):
    try:
        # Convert first page of PDF to image using pdf2image (works on Mac)
        images = convert_from_path(pdf_path, first_page=1, last_page=1)
        if images:
            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            images[0].save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)
            return img_byte_arr.getvalue()
    except Exception as e:
        print(f"PDF Thumbnail Error - File: {pdf_path}")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print(f"Stack Trace:", traceback.format_exc())
    return None

def generate_docx_thumbnail(docx_path):
    try:
        # First, try to convert DOCX to PDF using LibreOffice
        pdf_path = docx_path.replace('.docx', '.pdf')
        
        # Create a temporary directory without spaces
        temp_dir = os.path.join('/tmp', 'docx_conversion')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Copy the DOCX to the temp directory with a simple name
        temp_docx = os.path.join(temp_dir, 'temp.docx')
        import shutil
        shutil.copy2(docx_path, temp_docx)
        
        # Convert in the temp directory
        conversion_command = f'soffice --headless --convert-to pdf "{temp_docx}" --outdir "{temp_dir}"'
        print(f"Running conversion command: {conversion_command}")
        
        result = os.system(conversion_command)
        print(f"LibreOffice conversion result: {result}")
        
        temp_pdf = os.path.join(temp_dir, 'temp.pdf')
        if os.path.exists(temp_pdf):
            print(f"PDF created successfully at: {temp_pdf}")
            # Use the PDF thumbnail generation method
            thumbnail = generate_pdf_thumbnail(temp_pdf)
            # Clean up temporary files
            os.remove(temp_pdf)
            os.remove(temp_docx)
            if thumbnail:
                return thumbnail
            
        print("LibreOffice conversion failed or PDF not created")

        # Fallback: Try direct DOCX conversion with ImageMagick
        print("Attempting ImageMagick conversion...")
        with WandImage() as img:
            # Copy to temp location for ImageMagick as well
            img.read(filename=temp_docx, format='docx')
            img.format = 'jpeg'
            img.compression_quality = 80
            print("Successfully converted DOCX to image")
            
            # Clean up
            os.remove(temp_docx)
            try:
                os.rmdir(temp_dir)
            except:
                pass
                
            return img.make_blob()

    except Exception as e:
        print(f"DOCX Thumbnail Error - File: {docx_path}")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print(f"Stack Trace:", traceback.format_exc())
        
        # Additional debugging information
        try:
            print("Checking file existence:", os.path.exists(docx_path))
            print("File size:", os.path.getsize(docx_path))
            print("File permissions:", oct(os.stat(docx_path).st_mode)[-3:])
            print("LibreOffice version:", os.popen('soffice --version').read())
            print("ImageMagick version:", os.popen('convert -version').read())
            print("Temp directory exists:", os.path.exists(temp_dir))
            if os.path.exists(temp_dir):
                print("Temp directory contents:", os.listdir(temp_dir))
        except Exception as debug_e:
            print("Debug info error:", str(debug_e))
        
        # Clean up temp files in case of error
        try:
            if os.path.exists(temp_docx):
                os.remove(temp_docx)
            if os.path.exists(temp_pdf):
                os.remove(temp_pdf)
            os.rmdir(temp_dir)
        except:
            pass
            
        return None

@docs_bp.route('/docs/upload', methods=['POST', 'OPTIONS'])
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
            
            # After successful upload, index the document through the API gateway
            try:
                index_payload = {
                    'doc_id': document.doc_id,
                    'content_text': '',
                    'doc_metadata': {
                        'filename': document.original_filename,
                        'upload_date': document.upload_date.isoformat(),
                        'file_type': document.file_type,
                        'description': document.description
                    }
                }
                print(f"Sending index request with payload: {index_payload}")  # Debug log
                
                index_response = requests.post(
                    'http://127.0.0.1:5000/search/index',
                    json=index_payload,
                    headers={
                        'Authorization': request.headers.get('Authorization'),
                        'Content-Type': 'application/json'
                    }
                )
                
                print(f"Index response status: {index_response.status_code}")  # Debug log
                print(f"Index response text: {index_response.text}")  # Debug log
                
                if not index_response.ok:
                    print(f"Warning: Failed to index document {document.doc_id}: {index_response.text}")
            except Exception as index_error:
                print(f"Error indexing document {document.doc_id}: {str(index_error)}")
                # Don't fail the upload if indexing fails
            
            uploaded_documents.append({
                'id': document.doc_id,
                'filename': document.original_filename,
                'file_type': document.file_type,
                'upload_date': document.upload_date.isoformat(),
                'success': True
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
            'errors': errors,
            'success': False
        }), 400
    elif errors:
        # Some files succeeded, some failed
        return jsonify({
            'message': 'Some files uploaded successfully',
            'files': uploaded_documents,
            'errors': errors,
            'success': True
        }), 201
    else:
        # All files succeeded
        return jsonify({
            'message': 'All files uploaded successfully',
            'files': uploaded_documents,
            'success': True
        }), 201

@docs_bp.route('/docs/documents', methods=['GET'])
def get_user_documents():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    documents = Document.query.filter_by(user_id=user_id).all()
    return jsonify([doc.to_dict() for doc in documents]), 200

@docs_bp.route('/docs/documents/<int:doc_id>', methods=['GET'])
def download_document(doc_id):
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    document = Document.query.filter_by(doc_id=doc_id, user_id=user_id).first()
    if not document:
        return jsonify({'error': 'Document not found'}), 404

    file_path = os.path.join(UPLOAD_FOLDER, str(user_id), document.filename)
    return send_file(file_path, as_attachment=True, download_name=document.original_filename)

@docs_bp.route('/docs/documents/<int:doc_id>', methods=['DELETE'])
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
        print(f"Error deleting document: {str(e)}")  # Add logging
        db.session.rollback()  # Add rollback on error
        return jsonify({'error': str(e)}), 500

@docs_bp.route('/docs/recent', methods=['GET'])
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

@docs_bp.route('/docs/file/<int:file_id>', methods=['GET'])
def get_file_direct(file_id):
    try:
        # Get user_id from token
        user_id = get_user_id_from_token()
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401
            
        document = Document.query.filter_by(doc_id=file_id, user_id=user_id).first()
        if not document:
            return jsonify({'error': 'File not found'}), 404

        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 
                                str(user_id), 
                                document.filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found on disk'}), 404

        response = send_file(
            file_path,
            mimetype=document.file_type,
            as_attachment=True,
            download_name=document.original_filename
        )
        
        return response

    except Exception as e:
        print(f"Error serving file: {str(e)}")
        return jsonify({'error': 'Failed to serve file'}), 500

@docs_bp.route('/docs/file/<int:file_id>/thumbnail', methods=['GET'])
def get_file_thumbnail(file_id):
    try:
        # Get user_id from token
        user_id = get_user_id_from_token()
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401
            
        document = Document.query.filter_by(doc_id=file_id, user_id=user_id).first()
        if not document:
            return jsonify({'error': 'File not found'}), 404

        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 
                                str(user_id), 
                                document.filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found on disk'}), 404
            
        # Generate thumbnail
        img = Image.open(file_path)
        img.thumbnail((200, 200))  # Resize to thumbnail size
        
        # Save to bytes
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(
            img_io, 
            mimetype='image/png',
            as_attachment=False
        )
        
    except Exception as e:
        print(f"Error generating thumbnail: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Error generating thumbnail'}), 500

@docs_bp.route('/docs/documents/<int:doc_id>', methods=['PATCH', 'OPTIONS'])
@cross_origin(
    origins=["http://localhost:3000", "http://localhost:5000"],
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

@docs_bp.route('/docs/recent', methods=['GET'])
def get_recent_files():
    try:
        # Get the user_id from the Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            print("No token provided or invalid format")
            return jsonify({'error': 'No token provided'}), 401
            
        token = auth_header.split(' ')[1]
        print(f"Received token: {token[:10]}...")  # Print first 10 chars for debugging
        
        try:
            # Make sure we're using the same secret key as the auth service
            secret_key = current_app.config.get('SECRET_KEY')
            print(f"Using secret key: {secret_key[:10]}...")  # Print first 10 chars for debugging
            
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
            if not user_id:
                print("No user_id in token payload")
                return jsonify({'error': 'Invalid token payload'}), 401
                
            print(f"Decoded user_id: {user_id}")
        except jwt.InvalidTokenError as e:
            print(f"Token decode error: {str(e)}")
            return jsonify({'error': 'Invalid token'}), 401

        # Query for recent files
        recent_files = Document.query.filter_by(user_id=user_id)\
            .order_by(Document.upload_date.desc())\
            .limit(6)\
            .all()

        files_data = [{
            'doc_id': doc.doc_id,
            'original_filename': doc.original_filename,
            'upload_date': doc.upload_date.isoformat(),
            'file_type': doc.file_type
        } for doc in recent_files]

        return jsonify({'files': files_data}), 200

    except Exception as e:
        print(f"Error in get_recent_files: {str(e)}")
        print("Traceback:", traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500

@docs_bp.route('/docs/file/<int:file_id>', methods=['GET'])
@docs_bp.route('/docs/file/<int:file_id>/thumbnail', methods=['GET'])
def get_file_content(file_id):
    try:
        document = Document.query.filter_by(doc_id=file_id).first()
        
        if not document:
            return jsonify({'error': 'File not found'}), 404

        # Construct file path using user_id and filename
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 
                                str(document.user_id), 
                                document.filename)
        
        if not os.path.exists(file_path):
            print(f"File not found at path: {file_path}")
            return jsonify({'error': 'File not found on disk'}), 404

        is_thumbnail = request.path.endswith('/thumbnail')
        
        if is_thumbnail and document.file_type.startswith('image/'):
            try:
                with Image.open(file_path) as img:
                    img.thumbnail((100, 100))
                    thumbnail_io = BytesIO()
                    img.save(thumbnail_io, format=img.format)
                    thumbnail_io.seek(0)
                    return send_file(
                        thumbnail_io,
                        mimetype=document.file_type,
                        as_attachment=False
                    )
            except Exception as e:
                print(f"Thumbnail generation error: {str(e)}")
                print(f"Traceback: {traceback.format_exc()}")
                return jsonify({'error': 'Error generating thumbnail'}), 500

        # For non-thumbnails or non-images, send the original file
        return send_file(
            file_path,
            mimetype=document.file_type,
            as_attachment=True,
            download_name=document.original_filename
        )

    except Exception as e:
        print(f"Error retrieving file: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Internal server error'}), 500

def get_file(doc_id, user_id):
    try:
        document = Document.query.filter_by(doc_id=doc_id).first()
        if not document:
            logger.error(f"Document not found: {doc_id}")
            return None, None
            
        # Combine UPLOAD_FOLDER with the stored file_path
        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], document.file_path)
        logger.info(f"Accessing file at: {full_path}")
        
        if not os.path.exists(full_path):
            logger.error(f"File not found at path: {full_path}")
            return None, None
            
        return document, full_path
    except Exception as e:
        logger.error(f"Error retrieving file: {str(e)}\nTraceback: {traceback.format_exc()}")
        return None, None

@docs_bp.route('/docs/documents', methods=['GET'])
def get_all_documents():
    try:
        user_id = get_user_id_from_token()
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        documents = Document.query.filter_by(user_id=user_id)\
            .order_by(Document.upload_date.desc())\
            .all()

        files_data = [{
            'doc_id': doc.doc_id,
            'original_filename': doc.original_filename,
            'upload_date': doc.upload_date.isoformat(),
            'file_type': doc.file_type
        } for doc in documents]

        return jsonify(files_data), 200

    except Exception as e:
        print(f"Error in get_all_documents: {str(e)}")
        print("Traceback:", traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500

@docs_bp.route('/docs/file/<int:doc_id>', methods=['GET'])
def get_file_metadata(doc_id):
    try:
        document = Document.query.filter_by(doc_id=doc_id).first()
        if not document:
            return jsonify({'error': 'Document not found'}), 404
            
        return jsonify(document.to_dict())
        
    except Exception as e:
        print(f"Error retrieving document: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
