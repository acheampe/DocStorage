
# DocStorage

## Overview

**DocStorage** is a simplified version of the on-going InfoVault project. It reflects a microservice architecture and allows users to register, store documents, search for them, and share documents with other registered users. This project does not utilize AWS services like infovault and instead relies on local storage for backend services.

## Tech Stack

- **Backend:**
  - Python (Flask) / or any stack that programmer is comfortable with. 
  - PostgreSQL
  - JWT (for authentication)
  
- **Frontend:**
  - React
  - Tailwind CSS

## Microservices

1. **Authentication Service**  
   Handles user registration, login, and authentication using JWT tokens.

2. **Document Management Service**  
   Manages document storage, retrieval, and metadata. Documents are stored locally.

3. **Search Service**  
   Allows users to search for documents by metadata such as name or category.

4. **Share Service**  
   Enables users to share documents with other registered users, verifying the recipient before granting access.

## Project Structure

```bash
docstorage/
├── services/
│   ├── auth_service/          # Authentication service
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── models/
│   │   │   └── routes/
│   │   ├── requirements.txt
│   │   └── run.py
│   ├── doc_mgmt_service/      # Future document service
│   ├── search_service/        # Future search service
│   └── share_service/         # Future share service
├── frontend/                  # Next.js frontend
│   ├── src/
│   │   ├── app/
│   │   └── components/
│   ├── public/
│   └── package.json
├── database/                  # Database schemas
│   └── AuthServiceDDL.sql
├── DocStorageDocuments/       # Local storage
├── main.py
├── requirement.txt
└── .gitignore

```

## Setup Instructions

### Backend

1. **Clone the repository:**

   ```bash
   git clone https://github.com/acheampe/DocStorage.git
   cd docstorage
   ```

2. **Set up virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # For Mac/Linux
   venv\Scripts\activate   # For Windows
   ```

3. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run each Flask microservice**:

   - Start the **auth_service**:
   
     ```bash
     cd auth_service
     flask run
     ```

   - Repeat for `doc_mgmt_service`, `search_service`, and `share_service`.

### Frontend

1. **Navigate to the frontend directory:**

   ```bash
   cd frontend
   ```

2. **Install frontend dependencies:**

   ```bash
   npm install
   ```

3. **Run the frontend server:**

   ```bash
   npm start
   ```

## Future Enhancements

- Add file type restrictions for document uploads.
- Implement rate limiting for API endpoints.
- Integrate more advanced search capabilities.
- Improve document sharing access control and permissions.

## License

This project is licensed under the MIT License.
