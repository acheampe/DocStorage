from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # Load config from .env file
    load_dotenv()
    
    # Ensure SECRET_KEY is set
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    if not app.config['SECRET_KEY']:
        raise ValueError("No SECRET_KEY set in environment")
        
    # Get database URLs, with fallbacks
    search_db = os.getenv('SEARCH_DB_URL')
    doc_db = os.getenv('DOC_DB_URL')
    share_db = os.getenv('SHARE_DB_URL')

    if not all([search_db, doc_db, share_db]):
        raise ValueError("Missing required database URLs in environment variables")

    # Database configurations
    app.config['SQLALCHEMY_DATABASE_URI'] = search_db
    app.config['SQLALCHEMY_BINDS'] = {
        'doc_db': doc_db,
        'share_db': share_db
    }
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from .routes.search import search_bp
    app.register_blueprint(search_bp)

    return app 