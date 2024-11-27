import requests
import os
import json

BASE_URL = 'http://localhost:3002'
AUTH_URL = 'http://localhost:3001'

def login_user():
    response = requests.post(f'{AUTH_URL}/auth/login', json={
        'email': 'jane.smith@example.com',
        'password': 'Pass456$%^'
    })
    return response.json()['token']

def test_document_service():
    # Get auth token
    token = login_user()
    headers = {'Authorization': f'Bearer {token}'}
    
    # 1. Test file upload
    file_path = 'test_document.txt'
    with open(file_path, 'w') as f:
        f.write('Test content for document upload')
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {'description': 'Test document description'}
        response = requests.post(f'{BASE_URL}/docs/upload', 
                               headers=headers,
                               files=files,
                               data=data)
        print('Upload response:', response.json())
        doc_id = response.json()['doc_id']
    
    # 2. Test get all documents
    response = requests.get(f'{BASE_URL}/docs/documents', headers=headers)
    print('Get all documents:', response.json())
    
    # 3. Test download document
    response = requests.get(f'{BASE_URL}/docs/documents/{doc_id}', headers=headers)
    if response.status_code == 200:
        with open('downloaded_doc.txt', 'wb') as f:
            f.write(response.content)
        print('Document downloaded successfully')
    
    # 4. Test delete document
    response = requests.delete(f'{BASE_URL}/docs/documents/{doc_id}', headers=headers)
    print('Delete response:', response.json())
    
    # Cleanup
    os.remove(file_path)
    if os.path.exists('downloaded_doc.txt'):
        os.remove('downloaded_doc.txt')

if __name__ == '__main__':
    test_document_service() 