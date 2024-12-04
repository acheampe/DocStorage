import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_IDENTITY_CLAIM = 'sub'
    JWT_ACCESS_TOKEN_EXPIRES = False
