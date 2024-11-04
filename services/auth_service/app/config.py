import os
from dotenv import load_dotenv

load_dotenv()

print(f"DB_URL: {os.getenv('DB_URL')}")
print(f"SECRET_KEY: {os.getenv('SECRET_KEY')}")

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-please-change')
    SQLALCHEMY_DATABASE_URI = os.getenv('DB_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False