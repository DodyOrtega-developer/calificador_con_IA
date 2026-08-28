from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    id            = db.Column(db.Integer, primary_key=True)
    nombre        = db.Column(db.String(120), nullable=False)
    correo        = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rol           = db.Column(db.String(20), default='profesor')
    creado_en     = db.Column(db.DateTime, default=datetime.utcnow)
    materias      = db.relationship('Materia', backref='profesor', lazy=True)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class Materia(db.Model):
    __tablename__ = 'materia'
    id          = db.Column(db.Integer, primary_key=True)
    profesor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    nombre      = db.Column(db.String(120), nullable=False)
    codigo      = db.Column(db.String(20))
    periodo     = db.Column(db.String(20))
    rubricas    = db.relationship('Rubrica', backref='materia', lazy=True)
    tareas      = db.relationship('Tarea', backref='materia', lazy=True)

class Rubrica(db.Model):
    __tablename__ = 'rubrica'
    id             = db.Column(db.Integer, primary_key=True)
    materia_id     = db.Column(db.Integer, db.ForeignKey('materia.id'), nullable=False)
    nombre         = db.Column(db.String(120), nullable=False)
    criterios_json = db.Column(db.Text, nullable=False, default='[]')
    nota_maxima    = db.Column(db.Float, default=10.0, nullable=False)
    enunciado      = db.Column(db.Text, nullable=True)
    contexto_adicional = db.Column(db.Text, nullable=True)
    documento_fuente_nombre = db.Column(db.String(256), nullable=True)
    documento_fuente_path   = db.Column(db.String(256), nullable=True)
    documento_fuente_texto  = db.Column(db.Text, nullable=True)
    creado_en      = db.Column(db.DateTime, default=datetime.utcnow)
    tareas         = db.relationship('Tarea', backref='rubrica', lazy=True)

    def get_criterios(self):
        """Devuelve los criterios desde el campo JSON"""
        try:
            data = json.loads(self.criterios_json) if self.criterios_json else []
            return data
        except:
            return []

    def set_criterios(self, lista):
        """Guarda los criterios como JSON"""
        self.criterios_json = json.dumps(lista, ensure_ascii=False)

class Tarea(db.Model):
    __tablename__ = 'tarea'
    id                = db.Column(db.Integer, primary_key=True)
    materia_id        = db.Column(db.Integer, db.ForeignKey('materia.id'), nullable=False)
    rubrica_id        = db.Column(db.Integer, db.ForeignKey('rubrica.id'), nullable=False)
    estudiante_nombre = db.Column(db.String(120), nullable=False)
    archivo_path      = db.Column(db.String(256))
    enunciado         = db.Column(db.Text, nullable=False)
    subida_en         = db.Column(db.DateTime, default=datetime.utcnow)
    calificacion      = db.relationship('Calificacion', backref='tarea', uselist=False, lazy=True)

class Calificacion(db.Model):
    __tablename__ = 'calificacion'
    id                      = db.Column(db.Integer, primary_key=True)
    tarea_id                = db.Column(db.Integer, db.ForeignKey('tarea.id'), unique=True, nullable=False)
    nota_ia                 = db.Column(db.Float, nullable=False)
    nota_final              = db.Column(db.Float)
    retroalimentacion       = db.Column(db.Text)   # larga (para el profesor)
    retroalimentacion_corta = db.Column(db.Text)   # breve (resumen)
    desglose_json           = db.Column(db.Text)   # JSON con cumple por criterio
    prompt_usado            = db.Column(db.Text)
    generado_en             = db.Column(db.DateTime, default=datetime.utcnow)

    def get_desglose(self):
        if self.desglose_json:
            return json.loads(self.desglose_json)
        return []


class Configuracion(db.Model):
    """Almacena parámetros globales editables desde el panel de administración,
    como la API key de Gemini, sin necesidad de tocar el código fuente."""
    __tablename__ = 'configuracion'
    id              = db.Column(db.Integer, primary_key=True)
    gemini_api_key  = db.Column(db.String(256), nullable=True)
    actualizado_en  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def obtener():
        """Devuelve la fila única de configuración, creándola si no existe."""
        cfg = Configuracion.query.first()
        if not cfg:
            cfg = Configuracion()
            db.session.add(cfg)
            db.session.commit()
        return cfg