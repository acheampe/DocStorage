from flask import Flask, request, jsonify, make_response, Response
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "http://localhost:3000",
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "allow_credentials": True
    }
})

SERVICES = {
    'auth': 'http://127.0.0.1:3001',
    'docs': 'http://127.0.0.1:3002',
    'search': 'http://127.0.0.1:3003',
    'share': 'http://127.0.0.1:3004'
}

def get_forwarded_headers(request):
    return {key: value for key, value in request.headers.items() 
            if key != 'Host' and key != 'Content-Length'}

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

@app.route('/docs/file/<path:path>', methods=['GET'])
def docs_file_service(path):
    try:
        response = requests.get(
            f'http://127.0.0.1:3002/docs/file/{path}',
            headers=get_forwarded_headers(request),
        )
        print(f"Gateway: Response status: {response.status_code}")
        
        # Create response with proper headers
        gateway_response = Response(
            response.content,
            status=response.status_code,
            headers={
                'Content-Type': response.headers.get('Content-Type', 'application/octet-stream'),
                'Content-Disposition': response.headers.get('Content-Disposition', ''),
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )
        
        return gateway_response
        
    except Exception as e:
        print(f"Gateway error: {str(e)}")
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

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)