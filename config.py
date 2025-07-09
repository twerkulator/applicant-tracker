import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-this-secret-key'
    UPLOAD_FOLDER = 'uploads'
