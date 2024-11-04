from flask import Flask
from .extensions import db
from .config import Config

def create_app():
    app = Flask(__name__)
    
    # Configure your app
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints - move these imports here to avoid circular imports
    from .routes import main_bp, auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Create database tables
    with app.app_context():
        db.create_all()

    return app