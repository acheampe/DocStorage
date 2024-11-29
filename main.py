from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "http://localhost:3000",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

SERVICES = {
    'auth': 'http://127.0.0.1:3001',
    'docs': 'http://127.0.0.1:3002',
    'search': 'http://127.0.0.1:3003',
    'share': 'http://127.0.0.1:3004'
}

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

@app.route('/docs/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def docs_service(path):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    try:
        service_url = SERVICES['docs']
        
        # Handle file uploads differently
        if request.files:
            files = {
                key: (value.filename, value.stream, value.content_type)
                for key, value in request.files.items()
            }
            headers = {
                k: v for k, v in request.headers.items()
                if k.lower() not in ['host', 'content-length', 'content-type']
            }
            response = requests.request(
                method=request.method,
                url=f"{service_url}/docs/{path}",
                headers=headers,
                files=files,
                data=request.form,
                cookies=request.cookies,
                allow_redirects=False
            )
        else:
            response = requests.request(
                method=request.method,
                url=f"{service_url}/docs/{path}",
                headers={k: v for k, v in request.headers if k != 'Host'},
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False
            )
        
        return response.content, response.status_code, response.headers.items()
    except requests.exceptions.RequestException as e:
        print(f"Document service error: {str(e)}")
        return jsonify({'error': 'Document service unavailable'}), 503

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)