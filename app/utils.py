import re
from flask import current_app

# Conectores válidos dentro de nombres/apellidos compuestos en español (ej. "José de la Cruz").
_CONECTORES_NOMBRE = {'de', 'del', 'la', 'los', 'las', 'y'}

# Palabras comunes del español que NUNCA forman parte de un nombre propio, pero que a veces
# aparecen capitalizadas por estar al inicio de una oración (ej. "Una variable es..."),
# lo que puede engañar a un extractor de nombres ingenuo.
_PALABRAS_NO_NOMBRE = {
    'una', 'uno', 'unos', 'unas', 'el', 'un',
    'que', 'para', 'por', 'con', 'sin', 'sobre', 'entre', 'segun', 'según',
    'como', 'mas', 'más', 'muy', 'tambien', 'también', 'porque', 'cuando',
    'donde', 'dónde', 'cómo', 'esta', 'está', 'esto', 'eso', 'esa',
    'ese', 'estas', 'estos', 'hay', 'fue', 'fueron', 'era', 'eran', 'ser',
    'estar', 'tiene', 'tienen', 'puede', 'pueden', 'debe', 'deben', 'este',
    'aqui', 'aquí', 'ahi', 'ahí', 'todo', 'toda', 'todos', 'todas', 'nada',
    'algo', 'cada', 'otro', 'otra', 'mismo', 'misma', 'mientras', 'durante',
    'despues', 'después', 'antes', 'luego', 'ademas', 'además', 'es', 'son',
    'o', 'the', 'is', 'are', 'was', 'were',
}

# Acepta tanto "Maria" (Título) como "MARIA" (MAYÚSCULAS) — muchos documentos académicos
# ecuatorianos escriben el nombre del autor completamente en mayúsculas en la portada.
_PALABRA_NOMBRE_RE = re.compile(r'^[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ]+$')
_CONECTOR_RE = re.compile(r'^[A-Za-zÁÉÍÓÚÑáéíóúñ]+$')


def parece_nombre_valido(nombre):
    """Heurística para descartar textos que la IA (o una expresión regular) confundió con un
    nombre de estudiante, ej. tomar el inicio de una oración del documento ("Una variable es")
    en vez de devolver vacío cuando el documento no menciona ningún nombre."""
    if not nombre:
        return False
    palabras = nombre.strip().split()
    if not (2 <= len(palabras) <= 6):
        return False
    if palabras[0].lower() in _CONECTORES_NOMBRE:
        return False  # un nombre no puede empezar con un conector ("de", "la", etc.)
    for p in palabras:
        pl = p.lower()
        if pl in _CONECTORES_NOMBRE:
            if not _CONECTOR_RE.match(p):
                return False
            continue
        if pl in _PALABRAS_NO_NOMBRE:
            return False
        if not _PALABRA_NOMBRE_RE.match(p):
            return False
    return True


def normalizar_nombre(nombre):
    """Convierte un nombre (venga en MAYÚSCULAS, minúsculas o mixto) a formato legible:
    cada palabra capitalizada, salvo los conectores ("de", "la", ...) que van en minúscula."""
    if not nombre:
        return nombre
    palabras = []
    for p in nombre.strip().split():
        pl = p.lower()
        palabras.append(pl if pl in _CONECTORES_NOMBRE else pl[:1].upper() + pl[1:])
    return ' '.join(palabras)


def extension_ok(fn):
    return '.' in fn and fn.rsplit('.', 1)[1].lower() in current_app.config['EXTENSIONES_PERMITIDAS']


def extraer_texto(path):
    """Extrae el texto de un PDF o Word para usarlo como contexto o como respuesta del estudiante."""
    ext = path.rsplit('.', 1)[-1].lower()
    try:
        if ext == 'pdf':
            import PyPDF2
            with open(path, 'rb') as f:
                r = PyPDF2.PdfReader(f)
                return '\n'.join(p.extract_text() or '' for p in r.pages)
        elif ext in ('doc', 'docx'):
            import docx
            doc = docx.Document(path)
            return '\n'.join(p.text for p in doc.paragraphs)
    except Exception as e:
        return f"[Error leyendo archivo: {e}]"
    return ""


def get_gemini_api_key():
    """Obtiene la API key de Gemini configurada por el administrador en la base de datos.
    Si no se ha configurado ninguna, recurre a la variable de entorno como respaldo."""
    from app.models import Configuracion
    cfg = Configuracion.obtener()
    if cfg.gemini_api_key and cfg.gemini_api_key.strip():
        return cfg.gemini_api_key.strip()
    return current_app.config.get('GEMINI_API_KEY', '')
