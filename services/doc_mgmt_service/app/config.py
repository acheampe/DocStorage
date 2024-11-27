import os
from dotenv import load_dotenv

load_dotenv()

print(f"DB_URL: {os.getenv('DB_URL')}")
print(f"SECRET_KEY: {os.getenv('SECRET_KEY')}")

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-please-change')
    SQLALCHEMY_DATABASE_URI = os.getenv('DB_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Document storage configuration
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'DocStorageDocuments'))
    
    # Ensure upload folder exists during app initialization
    @classmethod
    def init_upload_folder(cls):
        if not os.path.exists(cls.UPLOAD_FOLDER):
            os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
            print(f"Created upload folder at: {cls.UPLOAD_FOLDER}")
        else:
            print(f"Upload folder exists at: {cls.UPLOAD_FOLDER}")