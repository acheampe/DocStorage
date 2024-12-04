from app import create_app, db
import os
from dotenv import load_dotenv

load_dotenv()

# Add these debug lines before creating the app
print("Debug: Current environment variables:")
print(f"STORAGE_PATH = {os.getenv('STORAGE_PATH')}")
print(f"Current working directory = {os.getcwd()}")

app = create_app()

# Create an application context
with app.app_context():
    try:
        # Create database tables
        db.create_all()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")

if __name__ == '__main__':
    # Run the application
    app.run(host='0.0.0.0', port=3004, debug=True)
