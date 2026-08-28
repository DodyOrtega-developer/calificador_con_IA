from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Usuario, Materia, Configuracion

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso restringido. Se requiere rol de administrador.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@login_required
@admin_required
def index():
    profesores = Usuario.query.filter_by(rol='profesor').order_by(Usuario.nombre).all()
    for p in profesores:
        p.total_materias = len(p.materias)
    return render_template('admin/index.html', profesores=profesores)


@admin_bp.route('/profesores/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_profesor():
    if request.method == 'POST':
        nombre   = request.form.get('nombre', '').strip()
        correo   = request.form.get('correo', '').strip()
        password = request.form.get('password', '')

        if not nombre or not correo or not password:
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('admin.nuevo_profesor'))

        if Usuario.query.filter_by(correo=correo).first():
            flash('Ya existe un usuario con ese correo.', 'error')
            return redirect(url_for('admin.nuevo_profesor'))

        u = Usuario(nombre=nombre, correo=correo, rol='profesor')
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash(f'Profesor "{nombre}" creado correctamente.', 'success')
        return redirect(url_for('admin.index'))

    return render_template('admin/nuevo_profesor.html')


@admin_bp.route('/profesores/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_profesor(id):
    profesor = Usuario.query.get_or_404(id)
    if profesor.rol == 'admin':
        flash('No se puede editar a otro administrador.', 'error')
        return redirect(url_for('admin.index'))

    if request.method == 'POST':
        nombre   = request.form.get('nombre', '').strip()
        correo   = request.form.get('correo', '').strip()
        password = request.form.get('password', '')

        if not nombre or not correo:
            flash('Nombre y correo son obligatorios.', 'error')
            return redirect(url_for('admin.editar_profesor', id=id))

        existing = Usuario.query.filter_by(correo=correo).first()
        if existing and existing.id != id:
            flash('Ese correo ya está en uso por otro usuario.', 'error')
            return redirect(url_for('admin.editar_profesor', id=id))

        profesor.nombre = nombre
        profesor.correo = correo
        if password:
            profesor.set_password(password)
        db.session.commit()
        flash(f'Profesor "{nombre}" actualizado.', 'success')
        return redirect(url_for('admin.index'))

    return render_template('admin/editar_profesor.html', profesor=profesor)


@admin_bp.route('/profesores/<int:id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_profesor(id):
    profesor = Usuario.query.get_or_404(id)
    if profesor.rol == 'admin':
        flash('No se puede eliminar a un administrador.', 'error')
        return redirect(url_for('admin.index'))

    try:
        for materia in profesor.materias:
            for rubrica in materia.rubricas:
                for tarea in rubrica.tareas:
                    if tarea.calificacion:
                        db.session.delete(tarea.calificacion)
                    db.session.delete(tarea)
                db.session.delete(rubrica)
            for tarea in materia.tareas:
                if tarea.calificacion:
                    db.session.delete(tarea.calificacion)
                db.session.delete(tarea)
            db.session.delete(materia)
        db.session.delete(profesor)
        db.session.commit()
        flash(f'Profesor "{profesor.nombre}" eliminado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {str(e)}', 'error')

    return redirect(url_for('admin.index'))


@admin_bp.route('/profesores/<int:id>/materias')
@login_required
@admin_required
def materias_profesor(id):
    profesor = Usuario.query.get_or_404(id)
    materias = Materia.query.filter_by(profesor_id=id).order_by(Materia.nombre).all()
    return render_template('admin/materias_profesor.html', profesor=profesor, materias=materias)


@admin_bp.route('/profesores/<int:id>/materias/nueva', methods=['GET', 'POST'])
@login_required
@admin_required
def nueva_materia(id):
    profesor = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        nombre  = request.form.get('nombre', '').strip()
        codigo  = request.form.get('codigo', '').strip()
        periodo = request.form.get('periodo', '').strip()

        if not nombre:
            flash('El nombre de la materia es obligatorio.', 'error')
            return redirect(url_for('admin.nueva_materia', id=id))

        m = Materia(profesor_id=id, nombre=nombre, codigo=codigo, periodo=periodo)
        db.session.add(m)
        db.session.commit()
        flash(f'Materia "{nombre}" asignada a {profesor.nombre}.', 'success')
        return redirect(url_for('admin.materias_profesor', id=id))

    return render_template('admin/nueva_materia.html', profesor=profesor)


@admin_bp.route('/configuracion', methods=['GET', 'POST'])
@login_required
@admin_required
def configuracion():
    cfg = Configuracion.obtener()

    if request.method == 'POST':
        nueva_key = request.form.get('gemini_api_key', '').strip()
        if not nueva_key:
            flash('La API key no puede estar vacía.', 'error')
            return redirect(url_for('admin.configuracion'))

        cfg.gemini_api_key = nueva_key
        db.session.commit()
        flash('API key de Gemini actualizada correctamente.', 'success')
        return redirect(url_for('admin.configuracion'))

    return render_template('admin/configuracion.html', cfg=cfg)


@admin_bp.route('/materias/<int:materia_id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_materia(materia_id):
    m = Materia.query.get_or_404(materia_id)
    profesor_id = m.profesor_id

    try:
        for rubrica in m.rubricas:
            for tarea in rubrica.tareas:
                if tarea.calificacion:
                    db.session.delete(tarea.calificacion)
                db.session.delete(tarea)
            db.session.delete(rubrica)
        for tarea in m.tareas:
            if tarea.calificacion:
                db.session.delete(tarea.calificacion)
            db.session.delete(tarea)
        db.session.delete(m)
        db.session.commit()
        flash(f'Materia "{m.nombre}" eliminada.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la materia: {str(e)}', 'error')

    return redirect(url_for('admin.materias_profesor', id=profesor_id))
