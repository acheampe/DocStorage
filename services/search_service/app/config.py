import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-please-change')
    SQLALCHEMY_DATABASE_URI = os.getenv('DB_URL')  # Search service database
    SQLALCHEMY_BINDS = {
        'share_db': os.getenv('SHARE_DB_URL'),  # Share service database
        'doc_db': os.getenv('DOC_DB_URL')       # Document management database
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False 