import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import Materia, Rubrica
from app.utils import extension_ok, extraer_texto
import json


def _guardar_documento_fuente(rubrica, archivo):
    """Guarda el documento fuente subido y cachea su texto extraído para usarlo como contexto en el prompt."""
    if not archivo or not archivo.filename or not extension_ok(archivo.filename):
        return
    nombre_s = secure_filename(archivo.filename)
    ruta = os.path.join(current_app.config['UPLOAD_FOLDER'], f"rubrica{rubrica.id}_{nombre_s}")
    archivo.save(ruta)
    rubrica.documento_fuente_nombre = archivo.filename
    rubrica.documento_fuente_path = ruta
    rubrica.documento_fuente_texto = extraer_texto(ruta)

materias_bp = Blueprint('materias', __name__)

@materias_bp.route('/materias')
@login_required
def index():
    return redirect(url_for('dashboard.index'))

@materias_bp.route('/materias/nueva', methods=['GET', 'POST'])
@login_required
def nueva():
    if current_user.rol != 'admin':
        flash('Solo el administrador puede crear materias.', 'error')
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        nombre  = request.form.get('nombre', '').strip()
        codigo  = request.form.get('codigo', '').strip()
        periodo = request.form.get('periodo', '').strip()
        if not nombre:
            flash('El nombre es obligatorio.', 'error')
            return redirect(url_for('materias.nueva'))
        m = Materia(profesor_id=current_user.id, nombre=nombre, codigo=codigo, periodo=periodo)
        db.session.add(m)
        db.session.commit()
        flash(f'Materia "{nombre}" creada correctamente.', 'success')
        return redirect(url_for('dashboard.index'))
    return render_template('materias/nueva.html')

@materias_bp.route('/materias/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    if current_user.rol != 'admin':
        flash('Solo el administrador puede editar materias.', 'error')
        return redirect(url_for('dashboard.index'))
    m = Materia.query.get_or_404(id)
    if request.method == 'POST':
        m.nombre  = request.form.get('nombre', '').strip()
        m.codigo  = request.form.get('codigo', '').strip()
        m.periodo = request.form.get('periodo', '').strip()
        db.session.commit()
        flash('Materia actualizada.', 'success')
        return redirect(url_for('dashboard.index'))
    return render_template('materias/editar.html', materia=m)

@materias_bp.route('/materias/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar(id):
    if current_user.rol != 'admin':
        flash('Solo el administrador puede eliminar materias.', 'error')
        return redirect(url_for('dashboard.index'))
    m = Materia.query.get_or_404(id)
    
    try:
        # Eliminar todas las rúbricas y sus tareas asociadas
        for rubrica in m.rubricas:
            # Eliminar tareas y calificaciones de cada rúbrica
            for tarea in rubrica.tareas:
                if tarea.calificacion:
                    db.session.delete(tarea.calificacion)
                db.session.delete(tarea)
            db.session.delete(rubrica)
        
        # Eliminar la materia
        db.session.delete(m)
        db.session.commit()
        
        flash(f'Materia "{m.nombre}" eliminada correctamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la materia: {str(e)}', 'error')
    
    return redirect(url_for('dashboard.index'))

# ── Rúbricas ──────────────────────────────────────────────

@materias_bp.route('/materias/<int:materia_id>/rubricas')
@login_required
def rubricas(materia_id):
    materia  = Materia.query.get_or_404(materia_id)
    rubricas = Rubrica.query.filter_by(materia_id=materia_id).all()
    
    # Calcular total de criterios
    total_criterios = sum(len(r.get_criterios()) for r in rubricas)
    
    # Para cada rúbrica, calcular su peso total
    for r in rubricas:
        criterios = r.get_criterios()
        r.peso_total = sum(c.get('peso', 0) for c in criterios)
    
    return render_template('materias/rubricas.html', 
                          materia=materia, 
                          rubricas=rubricas,
                          total_criterios=total_criterios)

@materias_bp.route('/materias/<int:materia_id>/rubricas/nueva', methods=['GET', 'POST'])
@login_required
def nueva_rubrica(materia_id):
    materia = Materia.query.get_or_404(materia_id)
    if request.method == 'POST':
        nombre     = request.form.get('nombre', '').strip()
        enunciado  = request.form.get('enunciado', '').strip()
        contexto_adicional = request.form.get('contexto_adicional', '').strip()
        criterios  = request.form.getlist('criterio[]')
        detalles   = request.form.getlist('detalle[]')
        pesos      = request.form.getlist('peso[]')

        if not nombre or not criterios:
            flash('Completa el nombre y al menos un criterio.', 'error')
            return redirect(request.url)

        nota_maxima = request.form.get('nota_maxima', type=float) or 10.0
        if nota_maxima <= 0:
            nota_maxima = 10.0

        lista = []
        total = 0
        for c, d, p in zip(criterios, detalles, pesos):
            c = c.strip()
            d = d.strip()
            try:
                p = int(p)
            except:
                p = 0
            if c:
                lista.append({'nombre': c, 'detalle': d, 'peso': p})
                total += p

        if total != 100:
            flash(f'Los pesos deben sumar 100%. Actualmente suman {total}%.', 'error')
            return redirect(request.url)

        r = Rubrica(materia_id=materia_id, nombre=nombre, nota_maxima=nota_maxima,
                    enunciado=enunciado, contexto_adicional=contexto_adicional)
        r.set_criterios(lista)
        db.session.add(r)
        db.session.flush()  # asigna r.id antes de guardar el documento fuente

        _guardar_documento_fuente(r, request.files.get('documento_fuente'))

        db.session.commit()
        flash(f'Rúbrica "{nombre}" creada.', 'success')
        return redirect(url_for('materias.rubricas', materia_id=materia_id))

    return render_template('materias/nueva_rubrica.html', materia=materia)

@materias_bp.route('/rubricas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_rubrica(id):
    r = Rubrica.query.get_or_404(id)
    
    # Verificar que el usuario sea el dueño de la materia
    if r.materia.profesor_id != current_user.id:
        flash('No tienes permiso para editar esta rúbrica.', 'error')
        return redirect(url_for('materias.rubricas', materia_id=r.materia_id))
    
    if request.method == 'POST':
        r.nombre   = request.form.get('nombre', '').strip()
        enunciado  = request.form.get('enunciado', '').strip()
        contexto_adicional = request.form.get('contexto_adicional', '').strip()
        criterios  = request.form.getlist('criterio[]')
        detalles   = request.form.getlist('detalle[]')
        pesos      = request.form.getlist('peso[]')
        quitar_documento = request.form.get('quitar_documento_fuente') == '1'

        nota_maxima = request.form.get('nota_maxima', type=float) or 10.0
        if nota_maxima <= 0:
            nota_maxima = 10.0

        lista = []
        total = 0
        for c, d, p in zip(criterios, detalles, pesos):
            c = c.strip()
            d = d.strip()
            try:
                p = int(p)
            except:
                p = 0
            if c:
                lista.append({'nombre': c, 'detalle': d, 'peso': p})
                total += p

        if total != 100:
            flash(f'Los pesos deben sumar 100%. Suman {total}%.', 'error')
            return redirect(request.url)

        r.nota_maxima = nota_maxima
        r.enunciado = enunciado
        r.contexto_adicional = contexto_adicional
        r.set_criterios(lista)

        if quitar_documento:
            r.documento_fuente_nombre = None
            r.documento_fuente_path = None
            r.documento_fuente_texto = None

        _guardar_documento_fuente(r, request.files.get('documento_fuente'))

        db.session.commit()
        flash('Rúbrica actualizada.', 'success')
        return redirect(url_for('materias.rubricas', materia_id=r.materia_id))

    return render_template('materias/editar_rubrica.html', rubrica=r)

@materias_bp.route('/rubricas/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_rubrica(id):
    r = Rubrica.query.get_or_404(id)
    materia_id = r.materia_id
    
    # Verificar que la rúbrica pertenezca a una materia del profesor actual
    if r.materia.profesor_id != current_user.id:
        flash('No tienes permiso para eliminar esta rúbrica.', 'error')
        return redirect(url_for('materias.rubricas', materia_id=materia_id))
    
    try:
        # Primero, eliminar las calificaciones y tareas asociadas a esta rúbrica
        for tarea in r.tareas:
            if tarea.calificacion:
                db.session.delete(tarea.calificacion)
            db.session.delete(tarea)
        
        # Luego eliminar la rúbrica
        db.session.delete(r)
        db.session.commit()
        
        flash(f'Rúbrica "{r.nombre}" eliminada correctamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la rúbrica: {str(e)}', 'error')
    
    return redirect(url_for('materias.rubricas', materia_id=materia_id))