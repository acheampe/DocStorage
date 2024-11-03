from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config import Config
from flask_cors import CORS

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    CORS(app, resources={
        r"/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:5000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from app.routes import main_bp, auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Create database tables
    with app.app_context():
        db.create_all()

    return app