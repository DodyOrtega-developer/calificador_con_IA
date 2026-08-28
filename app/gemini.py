import google.generativeai as genai
from flask import current_app
import json
import re
import os
from app.utils import get_gemini_api_key, parece_nombre_valido, normalizar_nombre

def get_available_model():
    """Obtiene el primer modelo disponible que pueda generar contenido"""
    try:
        models_available = []
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                models_available.append(model.name)
        
        # Modelos preferidos en orden. Se usan alias "-latest" primero porque Google los
        # mantiene apuntando siempre al modelo flash vigente, evitando que la app se rompa
        # cuando descontinúan una versión concreta (ej. gemini-2.5-flash dejó de estar
        # disponible para keys nuevas mientras el alias seguía funcionando).
        preferred_models = [
            'gemini-flash-latest',
            'models/gemini-flash-latest',
            'gemini-3.5-flash',
            'models/gemini-3.5-flash',
            'gemini-3.1-flash-lite',
            'models/gemini-3.1-flash-lite',
            'gemini-2.0-flash-exp',
            'models/gemini-2.0-flash-exp',
            'gemini-1.5-pro',
            'models/gemini-1.5-pro',
            'gemini-1.5-flash',
            'models/gemini-1.5-flash',
            'gemini-pro',
            'models/gemini-pro'
        ]
        
        for preferred in preferred_models:
            if preferred in models_available or preferred.replace('models/', '') in models_available:
                print(f"Usando modelo: {preferred}")
                return preferred
        
        if models_available:
            print(f"Usando modelo por defecto: {models_available[0]}")
            return models_available[0]
        
        return 'gemini-pro'
    except Exception as e:
        print(f"Error al listar modelos: {e}")
        return 'gemini-pro'


def _normalizar_criterios(criterios):
    """Normaliza los criterios para asegurar que tengan el formato esperado"""
    if not criterios:
        return [
            {'criterio': 'Contenido', 'detalle': 'Calidad y profundidad del contenido', 'peso': 40},
            {'criterio': 'Estructura', 'detalle': 'Organización y estructura del trabajo', 'peso': 30},
            {'criterio': 'Formato', 'detalle': 'Formato y presentación', 'peso': 20},
            {'criterio': 'Originalidad', 'detalle': 'Originalidad y creatividad', 'peso': 10}
        ]
    
    criterios_normalizados = []
    for c in criterios:
        if isinstance(c, dict):
            nombre = c.get('criterio') or c.get('nombre')
            if not nombre:
                nombre = 'Criterio sin nombre'
            
            criterios_normalizados.append({
                'criterio': nombre,
                'detalle': c.get('detalle', ''),
                'peso': c.get('peso', 0)
            })
        else:
            nombre = getattr(c, 'criterio', getattr(c, 'nombre', 'Criterio sin nombre'))
            criterios_normalizados.append({
                'criterio': nombre,
                'detalle': getattr(c, 'detalle', ''),
                'peso': getattr(c, 'peso', 0)
            })
    
    return criterios_normalizados


# Un nombre: primera palabra capitalizada, seguida de 1 a 4 palabras más que pueden ser
# capitalizadas (más apellidos/nombres, en Título O en MAYÚSCULAS —muchos documentos
# ecuatorianos escriben el nombre del autor todo en mayúsculas en la portada) o conectores
# (de, del, la, los, las, y). Usamos [ \t] (no \s) para que la coincidencia NUNCA cruce un
# salto de línea y termine absorbiendo la primera palabra de la oración/nombre siguiente.
_NOMBRE_PATRON = (
    r'([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ]+'
    r'(?:[ \t]+(?:de|del|la|los|las|y|[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ]+)){1,4})'
)

# Distintas formas en que un documento académico suele identificar al autor.
_ETIQUETAS_NOMBRE = (
    r'(?:Nombres?\s+y\s+[Aa]pellidos|Apellidos\s+y\s+[Nn]ombres|Integrantes?|Estudiantes?|'
    r'Alumnos?|Autor(?:es)?|Realizado\s+por|Presentado\s+por|Elaborado\s+por|'
    r'Entregado\s+por|Preparado\s+por|Nombres?|Apellidos?)'
)

# Entre la etiqueta y el nombre puede haber: espacios, el separador (":" o ";"), más espacios,
# y ADEMÁS un único salto de línea (el nombre suele ir en la línea siguiente a "PRESENTADO POR:").
_SEPARADOR_ETIQUETA = r'[ \t]*[:;][ \t]*\n?[ \t]*'


def _extraer_nombre_por_etiqueta(texto):
    """Busca un nombre justo después de una etiqueta explícita ("Nombre:", "Presentado por:",
    etc., incluso si el nombre está en la línea siguiente). Es la señal más confiable porque
    está anclada a una etiqueta inequívoca, así que se prioriza incluso sobre la respuesta del LLM."""
    if not texto:
        return None
    patron = _ETIQUETAS_NOMBRE + _SEPARADOR_ETIQUETA + _NOMBRE_PATRON
    match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
    if match:
        nombre = match.group(1).strip()
        if parece_nombre_valido(nombre):
            return normalizar_nombre(nombre)
    return None


def _extraer_nombre_primera_linea(texto):
    """Respaldo más débil: si el documento empieza directamente con lo que parece un nombre
    (sin ninguna etiqueta), lo toma como candidato."""
    if not texto:
        return None
    match = re.search(r'^' + _NOMBRE_PATRON, texto, re.MULTILINE)
    if match:
        nombre = match.group(1).strip()
        if parece_nombre_valido(nombre):
            return normalizar_nombre(nombre)
    return None


def _extraer_nombre_del_texto(texto):
    """Intenta extraer el nombre del estudiante del texto: primero por etiqueta explícita,
    luego por la primera línea del documento."""
    return _extraer_nombre_por_etiqueta(texto) or _extraer_nombre_primera_linea(texto)


def calificar_tarea(enunciado: str, criterios: list, respuesta_estudiante: str, nota_maxima: float = 10.0,
                     nombre_archivo: str = "", contexto_adicional: str = "", documento_fuente: str = "") -> dict:
    try:
        api_key = get_gemini_api_key()
        if not api_key:
            return {
                "nota": 0.0,
                "nombre_estudiante": "Estudiante",
                "retroalimentacion_corta": "No hay una API key de Gemini configurada.",
                "retroalimentacion_larga": "El administrador debe configurar la API key de Gemini en el panel de administración antes de poder calificar.",
                "desglose": [],
                "prompt": "",
                "error": True
            }
        genai.configure(api_key=api_key)

        model_name = get_available_model()
        model = genai.GenerativeModel(model_name)

        criterios_normalizados = _normalizar_criterios(criterios)

        def _linea(c):
            base = f"- {c['criterio']}: {c['peso']}% del total (vale {round(c['peso'] * nota_maxima / 100, 2)} puntos)"
            detalle = c.get('detalle', '').strip()
            return f"{base}\n  Descripción: {detalle}" if detalle else base

        rubrica_texto = "\n".join([_linea(c) for c in criterios_normalizados])

        if not respuesta_estudiante or len(respuesta_estudiante.strip()) < 10:
            # Intentar extraer nombre del texto aunque esté vacío
            nombre_extraido = _extraer_nombre_del_texto(respuesta_estudiante) or "Estudiante"
            return {
                "nota": 0.0,
                "nombre_estudiante": nombre_extraido,
                "retroalimentacion_corta": "El documento del estudiante está vacío o es demasiado corto para evaluar.",
                "retroalimentacion_larga": "No se pudo evaluar el trabajo porque el documento del estudiante está vacío o contiene muy poca información.",
                "desglose": [],
                "prompt": "",
                "error": True
            }

        # Intentar extraer nombre del texto ANTES de enviar a Gemini (para tener respaldo).
        # nombre_etiqueta es la señal fuerte (ancla a "Nombre:", "Presentado por:", etc.);
        # nombre_local incluye además el respaldo más débil de "primera línea del documento".
        nombre_etiqueta = _extraer_nombre_por_etiqueta(respuesta_estudiante)
        nombre_local = nombre_etiqueta or _extraer_nombre_primera_linea(respuesta_estudiante)

        bloque_contexto = ""
        if contexto_adicional and contexto_adicional.strip():
            bloque_contexto += f"CONTEXTO ADICIONAL (objetivos, instrucciones u otras aclaraciones del profesor):\n{contexto_adicional.strip()}\n"
        if documento_fuente and documento_fuente.strip():
            texto_fuente = documento_fuente.strip()[:8000]  # límite razonable de tokens
            bloque_contexto += f"\nDOCUMENTO FUENTE DE REFERENCIA (material base para juzgar la corrección del trabajo):\n{texto_fuente}\n"

        prompt = f"""Eres un asistente académico de la Universidad Técnica de Manabí (UTM).

Analiza el siguiente documento de un estudiante y realiza estas tareas:

1. **EXTRAER NOMBRE DEL ESTUDIANTE** (¡MUY IMPORTANTE!):
   - Busca en el documento etiquetas como: "Nombre:", "Nombres:", "Apellidos:", "Nombres y Apellidos:",
     "Apellidos y Nombres:", "Estudiante:", "Estudiantes:", "Alumno:", "Autor:", "Autores:", "Integrante(s):",
     "Realizado por:", "Presentado por:", "Elaborado por:", "Entregado por:", "Preparado por:", "Cédula:", "ID:".
   - Revisa especialmente el encabezado, la portada y el pie de página del documento (primeras y últimas líneas),
     que es donde casi siempre aparece el nombre del autor en trabajos académicos.
   - Si el trabajo fue hecho en grupo y hay varios integrantes, usa el nombre del PRIMERO que aparezca en la lista.
   - Si encuentras un nombre completo (2 o más palabras que parecen un nombre y apellido real), extráelo.
   - **NUNCA inventes un nombre ni tomes como nombre una frase del contenido del trabajo** (ej. no confundas
     el inicio de una oración como "Una variable es..." con un nombre de persona).
   - **Si NO encuentras ningún nombre real en el documento, devuelve una cadena vacía ""**. Es preferible
     devolver vacío a devolver un nombre incorrecto.

2. Califica la respuesta con base en la rúbrica indicada.

3. Genera dos retroalimentaciones:
   - Una LARGA (mínimo 3 párrafos) para el profesor.
   - Una CORTA (mínimo 10 palabras, máximo 40 palabras).

ENUNCIADO:
{enunciado}
{bloque_contexto}
RÚBRICA (sobre {nota_maxima} puntos — los criterios suman 100% del total):
{rubrica_texto}

DOCUMENTO DEL ESTUDIANTE:
{respuesta_estudiante}

Responde ÚNICAMENTE con un JSON válido con esta estructura:
{{
  "nombre_estudiante": "<nombre completo extraído del documento, o cadena vacía si no se encuentra>",
  "nota": <número 0.0 a {nota_maxima}>,
  "retroalimentacion_corta": "<resumen breve de mínimo 10 palabras>",
  "retroalimentacion_larga": "<análisis detallado en mínimo 3 párrafos>",
  "desglose": [
    {{
      "criterio": "<nombre del criterio>",
      "peso": <porcentaje>,
      "obtenido": <puntos obtenidos>,
      "cumple": <true o false>,
      "comentario": "<comentario específico>"
    }}
  ]
}}
Sin texto antes ni después del JSON.
¡Es MUY IMPORTANTE que extraigas el nombre del estudiante correctamente!"""

        response = model.generate_content(prompt)
        
        texto = response.text.strip()
        texto = re.sub(r'^```json\s*|\s*```$', '', texto)
        texto = re.sub(r'^```\s*|\s*```$', '', texto)
        
        try:
            resultado = json.loads(texto)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', texto, re.DOTALL)
            if json_match:
                resultado = json.loads(json_match.group())
            else:
                raise ValueError(f"No se pudo parsear JSON: {texto[:200]}...")
        
        # --- CORRECCIÓN DEL NOMBRE ---
        nombre_obtenido = resultado.get('nombre_estudiante', '').strip()

        # Si lo que devolvió Gemini no parece un nombre de persona real (ej. tomó el título
        # del documento porque no encontró un nombre explícito), lo descartamos para no
        # quedarnos con un nombre incorrecto.
        if nombre_obtenido and not parece_nombre_valido(nombre_obtenido):
            nombre_obtenido = ''
        elif nombre_obtenido:
            nombre_obtenido = normalizar_nombre(nombre_obtenido)

        # Una coincidencia por etiqueta explícita ("Nombre:", "Presentado por:", etc.) está
        # anclada a texto inequívoco del documento, así que es más confiable que la respuesta
        # libre del LLM (que a veces confunde el título del trabajo con el nombre del autor).
        # Tiene prioridad siempre que exista, incluso sobre una respuesta válida de Gemini.
        if nombre_etiqueta:
            nombre_obtenido = nombre_etiqueta
        elif not nombre_obtenido and nombre_local:
            nombre_obtenido = nombre_local

        # Si aún no hay nombre, usar el nombre del archivo
        if not nombre_obtenido and nombre_archivo:
            # Limpiar nombre del archivo
            nombre_limpio = os.path.splitext(os.path.basename(nombre_archivo))[0]
            nombre_limpio = nombre_limpio.replace('_', ' ').replace('-', ' ').replace('.', ' ')
            partes = [p for p in nombre_limpio.split() if p]
            if len(partes) >= 2:
                nombre_obtenido = normalizar_nombre(' '.join(partes))

        # Si sigue sin nombre, usar "Estudiante"
        resultado['nombre_estudiante'] = nombre_obtenido or "Estudiante"
        
        resultado['prompt'] = prompt
        resultado['error'] = False
        
        if resultado.get('nota', 0) > nota_maxima:
            resultado['nota'] = nota_maxima
        
        return resultado
        
    except Exception as e:
        print(f"Error en calificar_tarea: {e}")
        import traceback
        traceback.print_exc()
        
        # Intentar extraer nombre del texto incluso en caso de error
        nombre_fallback = _extraer_nombre_del_texto(respuesta_estudiante) if respuesta_estudiante else None
        if not nombre_fallback and nombre_archivo:
            nombre_fallback = os.path.splitext(os.path.basename(nombre_archivo))[0]
            nombre_fallback = nombre_fallback.replace('_', ' ').replace('-', ' ')
        
        return {
            "nota": 0.0,
            "nombre_estudiante": nombre_fallback or "Estudiante",
            "retroalimentacion_corta": f"Error al conectar con Gemini: {str(e)}",
            "retroalimentacion_larga": f"Error al conectar con Gemini: {str(e)}",
            "desglose": [],
            "prompt": prompt if 'prompt' in locals() else "",
            "error": True
        }