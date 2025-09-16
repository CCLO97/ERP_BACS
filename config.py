import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'tu_clave_secreta_muy_segura_aqui_2024'
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{os.environ.get('DB_USER', 'root')}:{os.environ.get('DB_PASSWORD', '')}@{os.environ.get('DB_HOST', 'localhost')}/{os.environ.get('DB_NAME', 'erp_bacs')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de archivos
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Usuario inicial
    INITIAL_USER_EMAIL = os.environ.get('INITIAL_USER_EMAIL')
    INITIAL_USER_PASSWORD = os.environ.get('INITIAL_USER_PASSWORD')
