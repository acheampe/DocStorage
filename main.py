from flask import Flask, request, jsonify, make_response, Response
from flask_cors import CORS, cross_origin
import requests
import os
from dotenv import load_dotenv
import traceback
import jwt
import base64
import json
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "expose_headers": ["Content-Type", "Authorization"]
    }
})

SERVICES = {
    'auth': 'http://localhost:3001',
    'docs': 'http://localhost:3002',
    'search': 'http://localhost:3003',
    'share': 'http://localhost:3004'
}

def get_forwarded_headers(request):
    headers = {
        key: value for (key, value) in request.headers if key != 'Host'
    }
    
    # Get the authorization header
    auth_header = headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        
        try:
            # Decode the token
            decoded = jwt.decode(token, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])
            
            # Add sub claim if missing
            if 'user_id' in decoded and 'sub' not in decoded:
                decoded['sub'] = str(decoded['user_id'])  # Convert to string for sub claim
                
                # Create new token with sub claim
                new_token = jwt.encode(
                    decoded,
                    os.getenv('JWT_SECRET_KEY'),
                    algorithm='HS256'
                )
                
                # Update the Authorization header with the new token
                headers['Authorization'] = f'Bearer {new_token}'
                print(f"Gateway: Modified token payload: {decoded}")
        except Exception as e:
            print(f"Gateway: Error processing token: {str(e)}")
    
    return headers

@app.route('/auth/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def auth_service(path):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    try:
        service_url = SERVICES['auth']
        response = requests.request(
            method=request.method,
            url=f"{service_url}/auth/{path}",
            headers={key: value for key, value in request.headers if key != 'Host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False
        )
        return response.content, response.status_code, response.headers.items()
    except requests.exceptions.RequestException:
        return jsonify({'error': 'Auth service unavailable'}), 503

@app.route('/docs', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
@app.route('/docs/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def docs_service(path):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,PATCH,OPTIONS')
        return response

    try:
        service_url = SERVICES['docs']
        target_url = f"{service_url}/docs"
        if path:
            target_url = f"{target_url}/{path}"
            
        print(f"Gateway: Forwarding {request.method} request to: {target_url}")
        print(f"Gateway: Headers: {dict(request.headers)}")
        
        response = requests.request(
            method=request.method,
            url=target_url,
            headers={k: v for k, v in request.headers.items() if k != 'Host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False
        )
        
        print(f"Gateway: Response status: {response.status_code}")
        print(f"Gateway: Response content: {response.content.decode()[:200]}")
        
        gateway_response = make_response(response.content)
        gateway_response.status_code = response.status_code
                
        return gateway_response
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error: {str(e)}")
        return jsonify({'error': 'Document service unavailable'}), 503

@app.route('/docs/file/<path:path>', methods=['GET', 'PUT', 'OPTIONS'])
def get_document(path):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        user_id = get_user_id_from_token(request.headers.get('Authorization'))
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401
            
        # Forward to document service
        service_url = SERVICES['docs']
        target_url = f"{service_url}/docs/file/{path}"
        
        # Handle both GET and PUT requests
        if request.method == 'GET':
            response = requests.get(
                target_url,
                headers=get_forwarded_headers(request),
                cookies=request.cookies,
                stream=True
            )
        elif request.method == 'PUT':
            response = requests.put(
                target_url,
                headers=get_forwarded_headers(request),
                data=request.get_data(),
                cookies=request.cookies
            )
        
        return Response(
            response.iter_content(chunk_size=8192) if request.method == 'GET' else response.content,
            status=response.status_code,
            headers={
                'Content-Type': response.headers.get('Content-Type', 'application/octet-stream'),
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            },
            direct_passthrough=request.method == 'GET'
        )
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error in get_document: {str(e)}")
        return jsonify({'error': 'Document service unavailable'}), 503
    except Exception as e:
        print(f"Unexpected error in get_document: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/docs/documents', methods=['GET'])
def get_documents():
    try:
        service_url = SERVICES['docs']
        target_url = f"{service_url}/docs/documents"
        
        print(f"Gateway: Forwarding GET request to: {target_url}")
        print(f"Gateway: Headers being forwarded: {get_forwarded_headers(request)}")
        
        response = requests.get(
            target_url,
            headers=get_forwarded_headers(request)
        )
        
        print(f"Gateway: Response status: {response.status_code}")
        if response.status_code != 200:
            print(f"Gateway: Error response: {response.text}")
        
        return Response(
            response.content,
            status=response.status_code,
            headers={'Content-Type': response.headers.get('Content-Type', 'application/json')}
        )
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error: {str(e)}")
        return jsonify({'error': 'Document service unavailable'}), 503

@app.route('/docs/recent', methods=['GET', 'OPTIONS'])
def get_recent_files():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        service_url = SERVICES['docs']
        target_url = f"{service_url}/docs/recent"
        
        print(f"Gateway: Forwarding GET request to: {target_url}")
        print(f"Gateway: Headers being forwarded: {get_forwarded_headers(request)}")
        
        response = requests.get(
            target_url,
            headers=get_forwarded_headers(request)
        )
        
        print(f"Gateway: Response status: {response.status_code}")
        if response.status_code != 200:
            print(f"Gateway: Error response: {response.text}")
        
        gateway_response = make_response(response.content)
        gateway_response.headers['Access-Control-Allow-Credentials'] = 'true'
        gateway_response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        gateway_response.status_code = response.status_code
        
        return gateway_response
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error: {str(e)}")
        return jsonify({'error': 'Document service unavailable'}), 503

@app.route('/search', methods=['GET', 'OPTIONS'])
def search_service():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        service_url = SERVICES['search']
        query_string = request.query_string.decode()
        target_url = f"{service_url}/search?{query_string}"
        
        print(f"Gateway: Search request received with query: {query_string}")
        print(f"Gateway: Forwarding GET request to: {target_url}")
        print(f"Gateway: Headers being forwarded: {get_forwarded_headers(request)}")
        
        response = requests.get(
            target_url,
            headers=get_forwarded_headers(request),
            timeout=10  # Increased timeout
        )
        
        print(f"Gateway: Search response status: {response.status_code}")
        print(f"Gateway: Search response content: {response.content.decode()[:200]}")
        
        if response.status_code != 200:
            error_message = f"Search failed with status {response.status_code}: {response.text}"
            print(f"Gateway: {error_message}")
            return jsonify({'error': error_message}), response.status_code
        
        # Parse response to ensure it's valid JSON
        try:
            response_data = response.json()
            return Response(
                response.content,
                status=200,
                headers={
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Credentials': 'true',
                    'Access-Control-Allow-Origin': 'http://localhost:3000'
                }
            )
        except ValueError as e:
            print(f"Gateway: Invalid JSON in search response: {str(e)}")
            return jsonify({'error': 'Invalid search response format'}), 500
        
    except requests.exceptions.RequestException as e:
        error_message = f"Search service error: {str(e)}"
        print(f"Gateway: {error_message}")
        return jsonify({'error': error_message}), 503

@app.route('/search/index', methods=['POST', 'OPTIONS'])
def index_document():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        service_url = SERVICES['search']
        target_url = f"{service_url}/search/index"
        
        print(f"Gateway: Forwarding POST request to: {target_url}")
        
        response = requests.post(
            target_url,
            headers=get_forwarded_headers(request),
            json=request.get_json()
        )
        
        gateway_response = make_response(response.content)
        gateway_response.headers['Access-Control-Allow-Credentials'] = 'true'
        gateway_response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        gateway_response.status_code = response.status_code
        
        return gateway_response
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error: {str(e)}")
        return jsonify({'error': 'Search service unavailable'}), 503

@app.route('/docs/documents/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def docs_service_with_path(path):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,PATCH,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        service_url = SERVICES['docs']
        target_url = f"{service_url}/docs/documents/{path}"
        
        headers = get_forwarded_headers(request)
        headers['Accept'] = request.headers.get('Accept', 'application/json')
        
        response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False
        )
        
        # Create response with proper headers
        gateway_response = Response(
            response.content,
            status=response.status_code,
            headers={
                'Content-Type': response.headers.get('Content-Type', 'application/json'),
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Allow-Methods': 'GET,PUT,POST,DELETE,PATCH,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization,Accept'
            }
        )
        
        return gateway_response
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error: {str(e)}")
        return jsonify({'error': 'Service unavailable'}), 503

@app.route('/search/delete/<path:path>', methods=['DELETE', 'OPTIONS'])
def delete_search_index(path):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        service_url = SERVICES['search']
        target_url = f"{service_url}/search/delete/{path}"
        
        print(f"Gateway: Forwarding DELETE request to search service: {target_url}")
        
        response = requests.delete(
            target_url,
            headers=get_forwarded_headers(request)
        )
        
        return Response(
            response.content,
            status=response.status_code,
            headers={
                'Content-Type': response.headers.get('Content-Type', 'application/json'),
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error: {str(e)}")
        return jsonify({'error': 'Search service unavailable'}), 503

def get_user_id_from_email(email):
    try:
        # Forward request to auth service to get user ID from email
        auth_url = f"{SERVICES['auth']}/auth/user/by-email"
        response = requests.post(
            auth_url,
            headers={'Content-Type': 'application/json'},
            json={'email': email}
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('user_id')
        else:
            print(f"Error getting user ID from email: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error in get_user_id_from_email: {str(e)}")
        return None

@app.route('/share', methods=['POST', 'OPTIONS'])
def create_share():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        data = request.get_json()
        print(f"Gateway: Received share request data: {data}")
        
        # Get document metadata from docs service
        docs_url = f"{SERVICES['docs']}/docs/file/{data['doc_id']}/metadata"
        headers = get_forwarded_headers(request)
        
        print(f"Gateway: Fetching document details from: {docs_url}")
        print(f"Gateway: Using headers: {headers}")
        
        docs_response = requests.get(
            docs_url,
            headers=headers,
            timeout=5
        )
        
        print(f"Gateway: Docs service response status: {docs_response.status_code}")
        print(f"Gateway: Docs service response content: {docs_response.content.decode('utf-8', errors='replace')}")
        
        if docs_response.status_code != 200:
            error_msg = f"Document not found: {docs_response.text}"
            print(f"Gateway: {error_msg}")
            response = jsonify({'error': error_msg})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response, docs_response.status_code
            
        # Add document metadata to share request
        doc_metadata = docs_response.json()
        share_data = {
            **data,
            'document_metadata': doc_metadata  # Include metadata in share request
        }
            
        # Forward to share service
        share_url = f"{SERVICES['share']}/share"
        print(f"Gateway: Forwarding to share service: {share_url}")
        print(f"Gateway: Share request data: {share_data}")
        
        share_response = requests.post(
            share_url,
            headers=headers,
            json=share_data,
            timeout=5
        )
        
        print(f"Gateway: Share service response status: {share_response.status_code}")
        print(f"Gateway: Share service response content: {share_response.content.decode('utf-8', errors='replace')}")
        
        # Create response with proper CORS headers
        response = Response(
            share_response.content,
            status=share_response.status_code,
            headers={
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            }
        )
        return response
            
    except requests.exceptions.RequestException as e:
        print(f"Gateway error (Request failed): {str(e)}")
        error_response = jsonify({'error': f'Service unavailable: {str(e)}'})
        error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        error_response.headers.add('Access-Control-Allow-Credentials', 'true')
        return error_response, 503
    except Exception as e:
        print(f"Gateway error (Unexpected): {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        error_response = jsonify({'error': 'Internal server error'})
        error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        error_response.headers.add('Access-Control-Allow-Credentials', 'true')
        return error_response, 500

@app.route('/share/<int:share_id>', methods=['DELETE', 'OPTIONS'])
def revoke_share(share_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        service_url = SERVICES['share']
        target_url = f"{service_url}/share/{share_id}"
        
        response = requests.delete(
            target_url,
            headers=get_forwarded_headers(request)
        )
        
        return Response(
            response.content,
            status=response.status_code,
            headers={
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error: {str(e)}")
        return jsonify({'error': 'Share service unavailable'}), 503

@app.route('/share/shared-with-me', methods=['GET'])
def get_shared_with_me():
    try:
        user_id = get_user_id_from_token(request.headers.get('Authorization'))
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        # Forward to share service
        share_service_url = SERVICES['share']
        auth_service_url = SERVICES['auth']
        docs_service_url = SERVICES['docs']
        
        share_response = requests.get(
            f"{share_service_url}/share/shared-with-me",
            params={'recipient_id': user_id},
            headers=get_forwarded_headers(request)
        )
        
        if share_response.status_code == 200:
            share_data = share_response.json()
            
            # Enrich with owner info and document metadata
            for share in share_data.get('shares', []):
                try:
                    # Get owner info
                    owner_response = requests.get(
                        f"{auth_service_url}/auth/users/{share['owner_id']}",
                        headers=get_forwarded_headers(request)
                    )
                    
                    if owner_response.status_code == 200:
                        owner_data = owner_response.json()
                        share['shared_by'] = owner_data.get('email')
                    
                    # Format the date
                    if share.get('shared_date'):
                        shared_date = datetime.fromisoformat(share['shared_date'].replace('Z', '+00:00'))
                        share['shared_date'] = shared_date.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Get document metadata
                    doc_response = requests.get(
                        f"{docs_service_url}/docs/file/{share['doc_id']}",
                        headers=get_forwarded_headers(request)
                    )
                    
                    if doc_response.status_code == 200:
                        doc_data = doc_response.json()
                        share.update({
                            'filename': doc_data.get('filename'),
                            'mime_type': doc_data.get('mime_type'),
                            'file_size': doc_data.get('file_size'),
                            'thumbnail_url': f"/docs/file/{share['doc_id']}/thumbnail"
                        })
                        
                except Exception as e:
                    print(f"Error enriching share data: {str(e)}")
                    
            return jsonify(share_data)
            
        return Response(
            share_response.content,
            status=share_response.status_code,
            headers={
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error in get_shared_with_me: {str(e)}")
        return jsonify({'error': 'Share service unavailable'}), 503
    except Exception as e:
        print(f"Unexpected error in get_shared_with_me: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def get_jwt_data(auth_header):
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
        
    token = auth_header.split(' ')[1]
    try:
        # Get JWT secret from environment
        jwt_secret = os.getenv('JWT_SECRET_KEY')
        if not jwt_secret:
            print("Warning: JWT_SECRET_KEY not found in environment")
            return None
            
        return jwt.decode(token, jwt_secret, algorithms=['HS256'])
    except jwt.InvalidTokenError as e:
        print(f"Token validation error: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error decoding token: {str(e)}")
        return None

@app.route('/share/shared-by-me', methods=['GET', 'OPTIONS'])
def get_shared_by_me():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        # Get user ID from token using the new function
        user_id = get_user_id_from_token(request.headers.get('Authorization'))
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        # Forward request to share service
        share_service_url = SERVICES['share']
        share_response = requests.get(
            f"{share_service_url}/share/shared-by-me",
            headers=get_forwarded_headers(request),
            params={'owner_id': user_id}
        )

        if share_response.status_code == 200:
            share_data = share_response.json()
            
            # Get auth service for user lookups
            auth_service_url = SERVICES['auth']
            
            # Enrich with document metadata and recipient info
            docs_service_url = SERVICES['docs']
            for share in share_data.get('shares', []):
                try:
                    # Get recipient info using auth service's user lookup endpoint
                    recipient_response = requests.post(
                        f"{auth_service_url}/auth/user/by-id",
                        headers=get_forwarded_headers(request),
                        json={'user_id': share['recipient_id']}
                    )
                    
                    if recipient_response.status_code == 200:
                        recipient_data = recipient_response.json()
                        share['shared_with'] = recipient_data.get('email')
                    else:
                        print(f"Error fetching recipient data: {recipient_response.status_code}")
                        share['shared_with'] = 'Unknown'
                    
                    # Format the date
                    if share.get('shared_date'):
                        shared_date = datetime.fromisoformat(share['shared_date'].replace('Z', '+00:00'))
                        share['shared_date'] = shared_date.strftime('%Y-%m-%d')
                    
                    # Get document metadata
                    doc_response = requests.get(
                        f"{docs_service_url}/docs/file/{share['doc_id']}",
                        headers=get_forwarded_headers(request)
                    )
                    
                    if doc_response.status_code == 200:
                        doc_data = doc_response.json()
                        share.update({
                            'filename': doc_data.get('filename'),
                            'mime_type': doc_data.get('mime_type'),
                            'file_size': doc_data.get('file_size'),
                            'thumbnail_url': f"/docs/file/{share['doc_id']}/thumbnail"
                        })
                        
                except Exception as e:
                    print(f"Error enriching share data: {str(e)}")
                    continue
                    
            return jsonify(share_data)
            
        return Response(
            share_response.content,
            status=share_response.status_code,
            headers={
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error: {str(e)}")
        return jsonify({'error': 'Service unavailable'}), 503

@app.route('/share/<int:share_id>/permissions', methods=['PATCH', 'OPTIONS'])
def update_share_permissions(share_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'PATCH,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        service_url = SERVICES['share']
        target_url = f"{service_url}/share/{share_id}/permissions"
        
        response = requests.patch(
            target_url,
            headers=get_forwarded_headers(request),
            json=request.get_json()
        )
        
        return Response(
            response.content,
            status=response.status_code,
            headers={
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error: {str(e)}")
        return jsonify({'error': 'Share service unavailable'}), 503

# Add new route for document previews
@app.route('/docs/preview/<doc_id>', methods=['GET', 'OPTIONS'])
def preview_document(doc_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        # Get user ID from token
        user_id = get_user_id_from_token(request.headers.get('Authorization'))
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        # Forward request to docs service
        service_url = SERVICES['docs']
        target_url = f"{service_url}/docs/file/{doc_id}"  # Using the file endpoint since that's what has the content
        
        print(f"Gateway: Forwarding preview request to: {target_url}")
        headers = get_forwarded_headers(request)
        
        response = requests.get(
            target_url,
            headers=headers,
            stream=True  # Important for handling file downloads
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'File not found'}), response.status_code
            
        # Get content type from response
        content_type = response.headers.get('Content-Type', 'application/octet-stream')
        
        # For now, we'll only support direct preview for images and PDFs
        if not (content_type.startswith('image/') or content_type == 'application/pdf'):
            return jsonify({'error': 'Unsupported file type for preview'}), 415
            
        return Response(
            response.content,
            status=response.status_code,
            headers={
                'Content-Type': content_type,
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error in preview: {str(e)}")
        return jsonify({'error': 'Document service unavailable'}), 503

def get_user_id_from_token(auth_header):
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
        
    token = auth_header.split(' ')[1]
    try:
        # Get JWT secret from environment
        jwt_secret = os.getenv('JWT_SECRET_KEY')
        if not jwt_secret:
            print("Warning: JWT_SECRET_KEY not found in environment")
            return None
            
        decoded = jwt.decode(token, jwt_secret, algorithms=['HS256'])
        return decoded.get('user_id')
    except jwt.InvalidTokenError as e:
        print(f"Token validation error: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error decoding token: {str(e)}")
        return None

@app.route('/auth/users/lookup', methods=['GET', 'OPTIONS'])
def lookup_user():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        # Forward request to auth service
        service_url = SERVICES['auth']
        target_url = f"{service_url}/auth/users/lookup"
        
        # Forward the email parameter and headers
        response = requests.get(
            target_url,
            headers=get_forwarded_headers(request),
            params={'email': request.args.get('email')}
        )
        
        return Response(
            response.content,
            status=response.status_code,
            headers={
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error in lookup_user: {str(e)}")
        return jsonify({'error': 'Auth service unavailable'}), 503

@app.route('/share/preview/<doc_id>', methods=['GET', 'OPTIONS'])
def preview_shared_document(doc_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        # Forward to share service
        service_url = SERVICES['share']
        target_url = f"{service_url}/share/preview/{doc_id}"
        
        response = requests.get(
            target_url,
            headers=get_forwarded_headers(request)
        )
        
        return Response(
            response.content,
            status=response.status_code,
            headers={
                'Content-Type': response.headers.get('Content-Type', 'application/octet-stream'),
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error in preview_shared_document: {str(e)}")
        return jsonify({'error': 'Share service unavailable'}), 503

@app.route('/share/file/<doc_id>', methods=['GET', 'OPTIONS'])
def get_shared_file(doc_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        # Get user ID from token
        user_id = get_user_id_from_token(request.headers.get('Authorization'))
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        # Check access through share service
        share_service_url = SERVICES['share']
        access_check = requests.get(
            f"{share_service_url}/share/check-access/{doc_id}",
            headers=get_forwarded_headers(request)
        )

        if access_check.status_code != 200:
            print(f"Access denied: {access_check.text}")
            return jsonify({'error': 'Access denied'}), 403

        # Access granted, get file from docs service
        docs_service_url = SERVICES['docs']
        file_response = requests.get(
            f"{docs_service_url}/docs/file/{doc_id}",
            headers=get_forwarded_headers(request),
            stream=True
        )

        if file_response.status_code != 200:
            return jsonify({'error': 'File not found'}), file_response.status_code

        return Response(
            file_response.content,
            status=file_response.status_code,
            headers={
                'Content-Type': file_response.headers.get('Content-Type', 'application/octet-stream'),
                'Content-Disposition': file_response.headers.get('Content-Disposition', ''),
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )

    except requests.exceptions.RequestException as e:
        print(f"Gateway error in get_shared_file: {str(e)}")
        return jsonify({'error': 'Service unavailable'}), 503

@app.route('/share/file/<doc_id>/thumbnail', methods=['GET', 'OPTIONS'])
def get_shared_file_thumbnail(doc_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        # Get user ID from token
        user_id = get_user_id_from_token(request.headers.get('Authorization'))
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        # First check if user has access to this shared file
        share_service_url = SERVICES['share']
        access_check = requests.get(
            f"{share_service_url}/share/check-access/{doc_id}",
            headers=get_forwarded_headers(request),
            params={'user_id': user_id}
        )

        if access_check.status_code != 200:
            return jsonify({'error': 'Access denied'}), 403

        # If access is granted, get the thumbnail from docs service
        docs_service_url = SERVICES['docs']
        thumbnail_response = requests.get(
            f"{docs_service_url}/docs/file/{doc_id}/thumbnail",
            headers=get_forwarded_headers(request),
            stream=True
        )

        return Response(
            thumbnail_response.content,
            status=thumbnail_response.status_code,
            headers={
                'Content-Type': thumbnail_response.headers.get('Content-Type', 'image/jpeg'),
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )

    except requests.exceptions.RequestException as e:
        print(f"Gateway error in get_shared_file_thumbnail: {str(e)}")
        return jsonify({'error': 'Service unavailable'}), 503

# Add new routes for share preview and content
@app.route('/share/preview/<int:share_id>/content', methods=['GET', 'OPTIONS'])
def get_shared_content(share_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        service_url = SERVICES['share']
        target_url = f"{service_url}/share/preview/{share_id}/content"
        
        print(f"Gateway: Forwarding GET request to: {target_url}")
        
        response = requests.get(
            target_url,
            headers=get_forwarded_headers(request),
            stream=True  # Important for file downloads
        )
        
        if response.status_code != 200:
            return make_response(response.content, response.status_code)

        gateway_response = Response(
            response.content,
            status=200,
            headers={
                'Content-Type': response.headers.get('Content-Type', 'application/octet-stream'),
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )
        
        return gateway_response

    except requests.exceptions.RequestException as e:
        print(f"Gateway error: {str(e)}")
        return jsonify({'error': 'Share service unavailable'}), 503

@app.route('/share/preview/<int:share_id>/thumbnail', methods=['GET', 'OPTIONS'])
def get_shared_thumbnail(share_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        service_url = SERVICES['share']
        target_url = f"{service_url}/share/preview/{share_id}/thumbnail"
        
        response = requests.get(
            target_url,
            headers=get_forwarded_headers(request)
        )
        
        gateway_response = make_response(response.content)
        gateway_response.headers['Content-Type'] = response.headers.get('Content-Type', 'image/jpeg')
        gateway_response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        gateway_response.headers['Access-Control-Allow-Credentials'] = 'true'
        gateway_response.status_code = response.status_code
        
        return gateway_response

    except requests.exceptions.RequestException as e:
        print(f"Gateway error: {str(e)}")
        return jsonify({'error': 'Share service unavailable'}), 503

@app.route('/docs/file/<int:doc_id>/rename', methods=['PUT', 'OPTIONS'])
def rename_document(doc_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        # Forward to document service
        service_url = SERVICES['docs']
        target_url = f"{service_url}/docs/file/{doc_id}/rename"
        
        response = requests.put(
            target_url,
            headers=get_forwarded_headers(request),
            json=request.get_json()
        )
        
        return Response(
            response.content,
            status=response.status_code,
            headers={
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )
        
    except requests.exceptions.RequestException as e:
        print(f"Gateway error in rename_document: {str(e)}")
        return jsonify({'error': 'Document service unavailable'}), 503

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)