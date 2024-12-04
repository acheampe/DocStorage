import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print(f"DB_URL: {os.getenv('DB_URL')}")
print(f"SECRET_KEY: {os.getenv('SECRET_KEY')}")
print(f"UPLOAD_FOLDER from env: {os.getenv('UPLOAD_FOLDER')}")

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-please-change')
    SQLALCHEMY_DATABASE_URI = os.getenv('DB_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Document storage configuration
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'DocStorageDocuments'))
    print(f"Configured UPLOAD_FOLDER: {UPLOAD_FOLDER}")
    print(f"UPLOAD_FOLDER absolute path: {os.path.abspath(UPLOAD_FOLDER)}")
    
    @classmethod
    def init_app(cls, app):
        app.config.from_object(cls)
        logger.info(f"Initializing app with UPLOAD_FOLDER: {cls.UPLOAD_FOLDER}")
        
        try:
            # Create base upload folder
            if not os.path.exists(cls.UPLOAD_FOLDER):
                os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
                logger.info(f"Created base upload folder at: {cls.UPLOAD_FOLDER}")
            
            # Initialize SQLAlchemy before querying
            from app.models import db
            db.init_app(app)
            
            # Now query for user folders
            with app.app_context():
                from app.models import Document
                user_ids = db.session.query(Document.user_id).distinct().all()
                for (user_id,) in user_ids:
                    user_folder = os.path.join(cls.UPLOAD_FOLDER, str(user_id))
                    if not os.path.exists(user_folder):
                        os.makedirs(user_folder, exist_ok=True)
                        logger.info(f"Created user folder at: {user_folder}")
            
            logger.info("Upload folder structure initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing upload folder structure: {str(e)}")
            raise