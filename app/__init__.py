from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
import os  # ← AÑADE ESTA LÍNEA

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Debes iniciar sesión para acceder.'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    login_manager.init_app(app)
    
    # ← AÑADE ESTAS 2 LÍNEAS AQUÍ
    # Crear la carpeta de uploads si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    print(f"Carpeta de uploads creada/verificada en: {app.config['UPLOAD_FOLDER']}")  # Opcional: para verificar

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.calificacion import calificacion_bp
    from app.routes.reportes import reportes_bp
    from app.routes.materias import materias_bp
    from app.routes.perfil import perfil_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(calificacion_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(materias_bp)
    app.register_blueprint(perfil_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()
        _migrar_columnas()
        _crear_usuario_demo()
        _crear_admin_demo()
        _sembrar_configuracion()

    return app

def _migrar_columnas():
    """Agrega columnas nuevas a tablas existentes sin borrar datos."""
    inspector = db.inspect(db.engine)
    with db.engine.connect() as conn:
        cols_rubrica = {col['name'] for col in inspector.get_columns('rubrica')}
        if 'nota_maxima' not in cols_rubrica:
            conn.execute(db.text('ALTER TABLE rubrica ADD COLUMN nota_maxima REAL NOT NULL DEFAULT 10.0'))
            conn.commit()
        if 'contexto_adicional' not in cols_rubrica:
            conn.execute(db.text('ALTER TABLE rubrica ADD COLUMN contexto_adicional TEXT'))
            conn.commit()
        if 'documento_fuente_nombre' not in cols_rubrica:
            conn.execute(db.text('ALTER TABLE rubrica ADD COLUMN documento_fuente_nombre VARCHAR(256)'))
            conn.commit()
        if 'documento_fuente_path' not in cols_rubrica:
            conn.execute(db.text('ALTER TABLE rubrica ADD COLUMN documento_fuente_path VARCHAR(256)'))
            conn.commit()
        if 'documento_fuente_texto' not in cols_rubrica:
            conn.execute(db.text('ALTER TABLE rubrica ADD COLUMN documento_fuente_texto TEXT'))
            conn.commit()

        cols_calif = {col['name'] for col in inspector.get_columns('calificacion')}
        if 'retroalimentacion_corta' not in cols_calif:
            conn.execute(db.text('ALTER TABLE calificacion ADD COLUMN retroalimentacion_corta TEXT'))
            conn.commit()
        if 'desglose_json' not in cols_calif:
            conn.execute(db.text('ALTER TABLE calificacion ADD COLUMN desglose_json TEXT'))
            conn.commit()

def _sembrar_configuracion():
    """Crea la fila única de configuración (API key, etc.) si no existe todavía."""
    from app.models import Configuracion
    if not Configuracion.query.first():
        db.session.add(Configuracion())
        db.session.commit()

def _crear_usuario_demo():
    from app.models import Usuario
    if not Usuario.query.filter_by(correo='profesor@utm.edu.ec').first():
        u = Usuario(nombre='Prof. Demo UTM', correo='profesor@utm.edu.ec', rol='profesor')
        u.set_password('utm2025')
        db.session.add(u)
        db.session.commit()

def _crear_admin_demo():
    from app.models import Usuario
    if not Usuario.query.filter_by(correo='admin@utm.edu.ec').first():
        a = Usuario(nombre='Administrador UTM', correo='admin@utm.edu.ec', rol='admin')
        a.set_password('admin2025')
        db.session.add(a)
        db.session.commit()