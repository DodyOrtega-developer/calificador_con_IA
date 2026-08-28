import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-utm-2025'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///calificador_utm.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB máximo por archivo
    # Respaldo si el administrador no ha configurado una API key desde el panel de administración.
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    EXTENSIONES_PERMITIDAS = {'pdf', 'doc', 'docx'}
