from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    
    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql://{os.getenv('DB_USER')}:"
        f"{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:"
        f"{os.getenv('DB_PORT')}/"
        f"{os.getenv('DB_NAME')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    from .routes import search_bp
    app.register_blueprint(search_bp)
    
    # Debug print registered routes
    print("\nRegistered routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")
    
    return app 