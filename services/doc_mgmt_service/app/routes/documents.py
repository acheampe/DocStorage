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
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            print("Debug - No Bearer token found")
            return None
            
        token = auth_header.split(' ')[1]
        secret_key = current_app.config.get('SECRET_KEY')
        
        # Decode token with more detailed error handling
        try:
            payload = jwt.decode(
                token, 
                secret_key, 
                algorithms=['HS256'],
                options={"verify_sub": False}  # Don't verify the 'sub' claim
            )
            user_id = payload.get('user_id')
            print(f"Debug - Token payload: {payload}")
            print(f"Debug - Extracted user_id: {user_id}")
            return user_id
            
        except jwt.ExpiredSignatureError:
            print("Debug - Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            print(f"Debug - Invalid token: {str(e)}")
            return None
            
    except Exception as e:
        print(f"Debug - Token processing error: {str(e)}")
        return None

def allowed_file(filename):
    """
    Check if the file extension is allowed.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_pdf_thumbnail(pdf_path):
    """
    Generate a thumbnail for a PDF file.
    """
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
    """
    Generate a thumbnail for a DOCX file.
    """
    try:
        # First, try to convert DOCX to PDF using LibreOffice
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
    """
    Upload a document for the user.
    """
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

@docs_bp.route('/docs/documents/<int:doc_id>', methods=['GET'])
def download_document(doc_id):
    """
    Download a document for the user.
    """
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
    """
    Delete a document for the user.
    """
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

@docs_bp.route('/docs/file/<int:doc_id>/thumbnail', methods=['GET'])
def get_file_thumbnail(doc_id):
    """
    Get a thumbnail for a file for the user.
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No token provided'}), 401
            
        token = auth_header.split(' ')[1]
        
        try:
            # Decode token without verifying sub claim
            secret_key = current_app.config.get('SECRET_KEY')
            payload = jwt.decode(token, secret_key, algorithms=['HS256'], options={"verify_sub": False})
            user_id = payload.get('user_id')
            
            if not user_id:
                return jsonify({'error': 'Invalid token payload'}), 401

            # Get the document
            document = Document.query.filter_by(doc_id=doc_id, user_id=user_id).first()
            if not document:
                return jsonify({'error': 'Document not found'}), 404

            # Construct file path
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 
                                   str(document.user_id), 
                                   document.filename)
            
            if not os.path.exists(file_path):
                return jsonify({'error': 'File not found on disk'}), 404

            # Generate thumbnail for image files
            if document.file_type.startswith('image/'):
                try:
                    with Image.open(file_path) as img:
                        # Increased height in target size
                        target_size = (200, 300)  # Changed from (200, 200)
                        
                        # Calculate aspect ratios
                        img_ratio = img.size[0] / img.size[1]
                        target_ratio = target_size[0] / target_size[1]
                        
                        if img_ratio > target_ratio:
                            # Image is wider than target
                            resize_size = (
                                int(target_size[1] * img_ratio),
                                target_size[1]
                            )
                        else:
                            # Image is taller than target
                            resize_size = (
                                target_size[0],
                                int(target_size[0] / img_ratio)
                            )
                        
                        # Resize image
                        img = img.resize(resize_size, Image.Resampling.LANCZOS)
                        
                        # Create new image with center crop
                        left = (resize_size[0] - target_size[0]) // 2
                        top = (resize_size[1] - target_size[1]) // 2
                        right = left + target_size[0]
                        bottom = top + target_size[1]
                        
                        img = img.crop((left, top, right, bottom))
                        
                        thumbnail_io = BytesIO()
                        img.save(thumbnail_io, format=img.format or 'JPEG', quality=85)
                        thumbnail_io.seek(0)
                        return send_file(
                            thumbnail_io,
                            mimetype=document.file_type,
                            as_attachment=False
                        )
                except Exception as e:
                    print(f"Thumbnail generation error: {str(e)}")
                    return jsonify({'error': 'Error generating thumbnail'}), 500

            # For non-image files, return a default icon or error
            return jsonify({'error': 'Not an image file'}), 400

        except jwt.InvalidTokenError as e:
            print(f"Token decode error: {str(e)}")
            return jsonify({'error': 'Invalid token'}), 401

    except Exception as e:
        print(f"Error in get_file_thumbnail: {str(e)}")
        print("Traceback:", traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500

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
    """
    Get the 6 most recent files for the user.
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No token provided'}), 401
            
        token = auth_header.split(' ')[1]
        
        try:
            secret_key = current_app.config.get('SECRET_KEY')
            # Don't verify the 'sub' claim
            payload = jwt.decode(token, secret_key, algorithms=['HS256'], options={"verify_sub": False})
            user_id = payload.get('user_id')
            
            if not user_id:
                return jsonify({'error': 'Invalid token payload'}), 401

            # Query recent files
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

        except jwt.InvalidTokenError as e:
            print(f"Token decode error: {str(e)}")
            return jsonify({'error': 'Invalid token'}), 401

    except Exception as e:
        print(f"Error in get_recent_files: {str(e)}")
        print("Traceback:", traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500

@docs_bp.route('/docs/file/<int:doc_id>', methods=['GET'])
def get_file_content(doc_id):
    try:
        # Get user_id from token and add debug logging
        user_id = get_user_id_from_token()
        print(f"Debug - Token user_id: {user_id}")
        print(f"Debug - Requested doc_id: {doc_id}")
        
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        try:
            # Get document and verify ownership with debug logging
            document = Document.query.filter_by(doc_id=doc_id, user_id=user_id).first()
            print(f"Debug - Document found: {document}")
            print(f"Debug - Document details: {document.__dict__ if document else None}")
            
            if not document:
                return jsonify({'error': 'File not found'}), 404

            # Get absolute path of UPLOAD_FOLDER
            upload_folder = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
            print(f"Debug - Upload folder: {upload_folder}")

            # Construct file path
            file_path = os.path.join(
                upload_folder,
                str(user_id),
                document.filename
            )
            print(f"Debug - Constructed file path: {file_path}")
            
            if not os.path.exists(file_path):
                print(f"Debug - File does not exist at path: {file_path}")
                return jsonify({'error': 'File not found on disk'}), 404

            print(f"Debug - File exists and attempting to send")
            return send_file(
                file_path,
                as_attachment=False,
                download_name=document.original_filename
            )

        except AttributeError as e:
            print(f"Debug - Document attribute error: {str(e)}")
            return jsonify({'error': 'Invalid document data'}), 500
        except OSError as e:
            print(f"Debug - File system error: {str(e)}")
            return jsonify({'error': 'File system error'}), 500

    except Exception as e:
        print(f"Debug - Unexpected error: {str(e)}")
        print("Debug - Full traceback:", traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500

@docs_bp.route('/docs/documents', methods=['GET'])
def get_all_documents():
    """
    Get all documents for the user.
    """
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

@docs_bp.route('/docs/file/<int:doc_id>/metadata', methods=['GET'])
def get_file_metadata(doc_id):
    """
    Get the metadata for a file for the user.
    """
    try:
        document = Document.query.filter_by(doc_id=doc_id).first()
        if not document:
            return jsonify({'error': 'Document not found'}), 404
            
        # Return metadata as JSON
        return jsonify({
            'doc_id': document.doc_id,
            'original_filename': document.original_filename,
            'file_path': document.file_path,
            'file_type': document.file_type,
            'upload_date': document.upload_date.isoformat() if document.upload_date else None
        })
        
    except Exception as e:
        print(f"Error retrieving document metadata: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
