from flask import Flask, request, jsonify
import requests
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Service URLs
SERVICES = {
    'auth': 'http://127.0.0.1:3001',
    'docs': 'http://127.0.0.1:3002',
    'search': 'http://127.0.0.1:3003',
    'share': 'http://127.0.0.1:3004'
}

def proxy_request(service):
    @wraps(service)
    def wrapper(*args, **kwargs):
        service_url = SERVICES.get(service)
        if not service_url:
            return jsonify({'error': 'Service not found'}), 404

        # Forward the request to the appropriate service
        try:
            response = requests.request(
                method=request.method,
                url=f"{service_url}{request.path}",
                headers={key: value for key, value in request.headers if key != 'Host'},
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False
            )
            return response.content, response.status_code, response.headers.items()
        except requests.exceptions.RequestException:
            return jsonify({'error': f'{service} service unavailable'}), 503
    return wrapper

# Auth Service Routes
@app.route('/auth/<path:path>', methods=['GET', 'POST'])
@proxy_request('auth')
def auth_service(path):
    return path
# Document Service Routes
@app.route('/docs/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@proxy_request('docs')
def doc_service(path): pass

# Search Service Routes
@app.route('/search/<path:path>', methods=['GET'])
@proxy_request('search')
def search_service(path): pass

# Share Service Routes
@app.route('/share/<path:path>', methods=['GET', 'POST', 'DELETE'])
@proxy_request('share')
def share_service(path): pass

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=3000)