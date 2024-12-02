from flask import Flask, request, jsonify, make_response, Response
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
import traceback
import jwt
import base64
import json

load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "http://localhost:3000",
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "allow_credentials": True,
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
                decoded['sub'] = decoded['user_id']
                
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

@app.route('/docs/file/<path:path>', methods=['GET', 'OPTIONS'])
def docs_file_service(path):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        service_url = SERVICES['docs']
        target_url = f"{service_url}/docs/file/{path}"
        
        # Forward all headers including Authorization
        headers = get_forwarded_headers(request)
        print(f"Gateway: Forwarding GET request to: {target_url}")
        print(f"Gateway: Headers being forwarded: {headers}")
        
        response = requests.get(
            target_url,
            headers=headers,
            cookies=request.cookies,
            allow_redirects=False,
            stream=True  # Add streaming for large files
        )
        
        print(f"Gateway: Response from docs service: {response.status_code}")
        
        # Create streaming response
        return Response(
            response.iter_content(chunk_size=8192),
            status=response.status_code,
            headers={
                'Content-Type': response.headers.get('Content-Type', 'application/octet-stream'),
                'Content-Disposition': response.headers.get('Content-Disposition', ''),
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            direct_passthrough=True
        )
        
    except Exception as e:
        print(f"Gateway error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

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
        # Get the original token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            print("Gateway: No Authorization header found")
            return jsonify({'error': 'No authorization token provided'}), 401

        print(f"Gateway: Received Authorization header: {auth_header[:30]}...")  # Print first 30 chars
        
        # Extract user_id from the token
        user_id = get_user_id_from_token(auth_header)
        if not user_id:
            print("Gateway: Could not extract user_id from token")
            return jsonify({'error': 'Invalid token'}), 401

        print(f"Gateway: Successfully extracted user_id: {user_id}")
        
        # Create a new token with sub claim for the share service
        share_token = jwt.encode(
            {'sub': str(user_id), 'user_id': user_id},
            os.getenv('JWT_SECRET_KEY'),
            algorithm='HS256'
        )
        
        print(f"Gateway: Created new share token: {share_token[:30]}...")

        service_url = SERVICES['share']
        target_url = f"{service_url}/share"
        
        # Log the request payload
        request_data = request.get_json()
        print(f"Gateway: Received share request data: {request_data}")
        
        # Forward the request with the modified token
        headers = get_forwarded_headers(request)
        headers['Authorization'] = f'Bearer {share_token}'
        
        response = requests.post(
            target_url,
            headers=headers,
            json=request_data
        )
        
        print(f"Gateway: Share service response: {response.status_code}")
        if response.status_code != 200 and response.status_code != 201:
            print(f"Gateway: Share service error response: {response.content.decode()}")
        
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

def get_user_email(user_id):
    try:
        # Call the auth service to get user details
        service_url = SERVICES['auth']
        target_url = f"{service_url}/auth/users/{user_id}"
        
        response = requests.get(target_url)
        if response.status_code == 200:
            user_data = response.json()
            return user_data.get('email')
        else:
            print(f"Gateway: Error fetching user email: {response.status_code}")
            return None
    except Exception as e:
        print(f"Gateway: Error in get_user_email: {str(e)}")
        return None

@app.route('/share/shared-with-me', methods=['GET', 'OPTIONS'])
def get_shared_with_me():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        # Get user email from auth service
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No valid authorization token provided'}), 401

        # Extract token and decode it
        token = auth_header.split(' ')[1]
        decoded = jwt.decode(token, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])
        user_id = decoded.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'Invalid token: no user_id claim'}), 401
            
        # Get user email from auth service
        auth_service_url = SERVICES['auth']
        auth_endpoint = f"{auth_service_url}/auth/users/{user_id}"
        print(f"Gateway: Requesting user details from: {auth_endpoint}")
        print(f"Gateway: Using headers: {auth_header}")
        
        auth_response = requests.get(
            auth_endpoint,
            headers={'Authorization': auth_header}
        )
        
        print(f"Gateway: Auth service response status: {auth_response.status_code}")
        print(f"Gateway: Auth service response: {auth_response.text}")
        
        if auth_response.status_code != 200:
            print(f"Gateway: Error fetching user details: {auth_response.status_code}")
            return jsonify({'error': f'Could not fetch user details: {auth_response.text}'}), 500
            
        user_data = auth_response.json()
        user_email = user_data.get('email')
        
        if not user_email:
            return jsonify({'error': 'Could not determine user email'}), 500
            
        print(f"Gateway: Fetched email {user_email} for user_id {user_id}")
        
        # Forward request to share service
        service_url = SERVICES['share']
        target_url = f"{service_url}/share/shared-with-me"
        
        print(f"Gateway: Forwarding to share service: {target_url}")
        print(f"Gateway: With email parameter: {user_email}")
        
        # Add email to query parameters
        headers = get_forwarded_headers(request)
        response = requests.get(
            target_url,
            headers=headers,
            params={'recipient_email': user_email}
        )
        
        print(f"Gateway: Share service response status: {response.status_code}")
        print(f"Gateway: Share service response: {response.text}")
        
        return Response(
            response.content,
            status=response.status_code,
            headers={
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )
        
    except jwt.InvalidTokenError as e:
        print(f"Gateway: Invalid token error: {str(e)}")
        return jsonify({'error': 'Invalid token'}), 401
    except requests.exceptions.RequestException as e:
        print(f"Gateway error: {str(e)}")
        return jsonify({'error': 'Service unavailable'}), 503
    except Exception as e:
        print(f"Gateway: Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

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
        # Get user ID from token
        token_data = get_jwt_data(request.headers.get('Authorization'))
        if not token_data or 'user_id' not in token_data:
            return jsonify({'error': 'Unauthorized'}), 401

        # Forward request to share service with user_id
        share_service_url = SERVICES['share']
        share_response = requests.get(
            f"{share_service_url}/share/shared-by-me",
            headers=get_forwarded_headers(request),
            params={'owner_id': token_data['user_id']}  # Add owner_id from token
        )

        if share_response.status_code != 200:
            return Response(
                share_response.content,
                status=share_response.status_code,
                headers={'Content-Type': 'application/json'}
            )

        share_data = share_response.json()
        
        # Enrich with document metadata
        docs_service_url = SERVICES['docs']
        for share in share_data.get('shares', []):
            try:
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
                        'original_filename': doc_data.get('filename'),
                        'file_type': doc_data.get('mime_type'),
                        'thumbnail_url': f"/docs/file/{share['doc_id']}/thumbnail"
                    })
                else:
                    print(f"Error fetching document {share['doc_id']}: {doc_response.status_code}")
                    share.update({
                        'filename': f"Document {share['doc_id']}",
                        'mime_type': 'application/octet-stream',
                        'file_size': 0,
                        'thumbnail_url': None
                    })
            except Exception as e:
                print(f"Error fetching document metadata: {str(e)}")
                share.update({
                    'filename': f"Document {share['doc_id']}",
                    'mime_type': 'application/octet-stream',
                    'file_size': 0,
                    'thumbnail_url': None
                })

        return jsonify(share_data)

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
@app.route('/docs/preview/<int:doc_id>', methods=['GET', 'OPTIONS'])
def preview_document(doc_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        service_url = SERVICES['docs']
        target_url = f"{service_url}/docs/preview/{doc_id}"
        
        print(f"Gateway: Forwarding preview request to docs service: {target_url}")
        
        response = requests.get(
            target_url,
            headers=get_forwarded_headers(request),
            stream=True  # Important for handling file downloads
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
        print(f"Gateway error: {str(e)}")
        return jsonify({'error': 'Document service unavailable'}), 503

def get_user_id_from_token(auth_header):
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
        
    token = auth_header.split(' ')[1]
    try:
        decoded = jwt.decode(token, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])
        return decoded.get('user_id')
    except jwt.InvalidTokenError:
        return None

@app.route('/docs/file/<doc_id>', methods=['GET', 'OPTIONS'])
def get_document(doc_id):
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
        target_url = f"{service_url}/docs/file/{doc_id}"
        
        print(f"Gateway: Forwarding GET request to: {target_url}")
        headers = get_forwarded_headers(request)
        print(f"Gateway: Headers being forwarded: {headers}")
        
        response = requests.get(target_url, headers=headers)
        print(f"Gateway: Response from docs service: {response.status_code}")
        
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
        return jsonify({'error': 'Document service unavailable'}), 503

def get_jwt_data(auth_header):
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
        
    token = auth_header.split(' ')[1]
    try:
        return jwt.decode(token, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])
    except jwt.InvalidTokenError:
        return None

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)