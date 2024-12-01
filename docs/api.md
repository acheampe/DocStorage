# API Documentation

## Authentication Service (Port: 3001)

### Register User
```http
POST /auth/register
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "password123",
    "first_name": "John",
    "last_name": "Doe"
}
```

**Response**
```json
{
    "message": "User registered successfully",
    "user": {
        "user_id": 1,
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe"
    }
}
```

### Login
```http
POST /auth/login
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "password123"
}
```

**Response**
```json
{
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": {
        "user_id": 1,
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe"
    }
}
```

## Document Service (Port: 3002)

### Upload Document
```http
POST /docs/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: <file>
```

**Response**
```json
{
    "message": "File uploaded successfully",
    "doc_id": 1,
    "filename": "document.pdf"
}
```

### Get Recent Documents
```http
GET /docs/recent
Authorization: Bearer <token>
```

**Response**
```json
{
    "files": [
        {
            "doc_id": 1,
            "original_filename": "document.pdf",
            "upload_date": "2024-01-01T12:00:00Z",
            "file_type": "application/pdf"
        }
    ]
}
```

### Get Document
```http
GET /docs/file/{doc_id}
Authorization: Bearer <token>
```

**Response**
- File content with appropriate Content-Type header
- Or error message if file not found/unauthorized

### Delete Document
```http
DELETE /docs/file/{doc_id}
Authorization: Bearer <token>
```

**Response**
```json
{
    "message": "File deleted successfully"
}
```

## Search Service (Port: 3003) [Planned]

### Search Documents
```http
GET /search?q={query}
Authorization: Bearer <token>
```

**Response**
```json
{
    "results": [
        {
            "doc_id": 1,
            "filename": "document.pdf",
            "match_score": 0.95
        }
    ]
}
```

## Share Service (Port: 3004) [Planned]

### Share Document
```http
POST /share
Content-Type: application/json
Authorization: Bearer <token>

{
    "doc_id": 1,
    "recipient_email": "recipient@example.com",
    "permissions": ["read", "download"]
}
```

**Response**
```json
{
    "message": "Document shared successfully",
    "share_id": "abc123"
}
```

## Error Responses

### 400 Bad Request
```json
{
    "error": "Invalid request parameters"
}
```

### 401 Unauthorized
```json
{
    "error": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
    "error": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
    "error": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
    "error": "Internal server error"
}
``` 