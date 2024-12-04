from flask import Flask
from .extensions import db
from .routes.documents import docs_bp
from .config import Config
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Initialize configuration (this will also init SQLAlchemy)
    Config.init_app(app)
    
    # Register blueprints and other app setup
    from .routes.documents import docs_bp
    app.register_blueprint(docs_bp)
    
    return app
