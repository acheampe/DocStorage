# Setup Guide

## Prerequisites

- Python 3.8+
- Node.js 18+
- PostgreSQL 13+
- Git

## Environment Setup

1. **Clone the Repository**
```bash
git clone https://github.com/yourusername/docstorage.git
cd docstorage
```

2. **Environment Variables**
Copy `.env.example` to `.env` and update the values:
```bash
cp .env.example .env
```

Required environment variables:
```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=docstorage
DB_USER=your_username
DB_PASSWORD=your_password

# JWT
JWT_SECRET_KEY=your_secret_key
JWT_EXPIRATION_HOURS=48

# Services
GATEWAY_PORT=5000
AUTH_SERVICE_PORT=3001
DOC_SERVICE_PORT=3002
SEARCH_SERVICE_PORT=3003
SHARE_SERVICE_PORT=3004

# File Storage
UPLOAD_FOLDER=./uploads
MAX_CONTENT_LENGTH=16777216  # 16MB
```

## Backend Setup

1. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
cd services/gateway && pip install -r requirements.txt
cd ../auth_service && pip install -r requirements.txt
cd ../doc_service && pip install -r requirements.txt
```

3. **Database Setup**
```bash
# Create database
psql -U postgres
CREATE DATABASE docstorage;
\q

# Initialize schemas
psql -U postgres -d docstorage -f database/init.sql
psql -U postgres -d docstorage -f database/auth_schema.sql
psql -U postgres -d docstorage -f database/doc_schema.sql
```

4. **Start Services**
```bash
# Start API Gateway (Terminal 1)
cd services/gateway
python main.py

# Start Auth Service (Terminal 2)
cd services/auth_service
python run.py

# Start Document Service (Terminal 3)
cd services/doc_service
python run.py
```

## Frontend Setup

1. **Install Dependencies**
```bash
cd frontend
npm install
```

2. **Start Development Server**
```bash
npm run dev
```

The application will be available at `http://localhost:3000`

## Docker Setup (Alternative)

1. **Build Images**
```bash
docker-compose build
```

2. **Start Services**
```bash
docker-compose up -d
```

3. **Stop Services**
```bash
docker-compose down
```

## Verification

1. **Check Services**
- Gateway: http://localhost:5000/health
- Auth Service: http://localhost:3001/health
- Document Service: http://localhost:3002/health
- Frontend: http://localhost:3000

2. **Test Authentication**
```bash
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
- Verify PostgreSQL is running
- Check database credentials in .env
- Ensure database exists and is accessible

2. **Service Start Failed**
- Check if ports are available
- Verify all dependencies are installed
- Ensure environment variables are set

3. **File Upload Issues**
- Check UPLOAD_FOLDER permissions
- Verify MAX_CONTENT_LENGTH setting
- Ensure disk space is available

### Logs

- Gateway logs: `services/gateway/logs/gateway.log`
- Auth service logs: `services/auth_service/logs/auth.log`
- Document service logs: `services/doc_service/logs/doc.log`

## Development Setup

### VSCode Configuration
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "editor.formatOnSave": true,
  "python.formatting.provider": "black"
}
```

### Git Hooks
```bash
cp hooks/pre-commit .git/hooks/
chmod +x .git/hooks/pre-commit
```

## Next Steps

1. Review the API documentation in `docs/api.md`
2. Explore the architecture in `docs/architecture.md`
3. Start developing new features! 