from flask import Flask
from flask_cors import CORS
from .config import Config
from .extensions import db  # Import db from extensions
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize CORS with proper configuration
    cors = CORS()
    app.config['CORS_HEADERS'] = 'Content-Type'
    app.config['CORS_METHODS'] = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']
    app.config['CORS_ALLOW_HEADERS'] = ['Content-Type', 'Authorization']
    app.config['CORS_SUPPORTS_CREDENTIALS'] = True
    app.config['CORS_ORIGINS'] = ["http://localhost:3000"]
    cors.init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    
    # Ensure upload folder exists
    upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '..', 'DocStorageDocuments')
    os.makedirs(upload_folder, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_folder
    
    # Register blueprints
    from .routes import docs_bp
    app.register_blueprint(docs_bp, url_prefix='/docs')

    # Create database tables
    with app.app_context():
        db.create_all()

    return app
