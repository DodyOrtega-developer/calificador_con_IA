from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Tarea, Materia  # ← AÑADE ESTA IMPORTACIÓN

perfil_bp = Blueprint('perfil', __name__)

@perfil_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def index():
    # Calcular total de tareas calificadas del profesor
    total_tareas = Tarea.query.join(Materia).filter(Materia.profesor_id == current_user.id).count()
    
    if request.method == 'POST':
        nombre       = request.form.get('nombre', '').strip()
        pw_actual    = request.form.get('pw_actual', '')
        pw_nueva     = request.form.get('pw_nueva', '')
        pw_confirmar = request.form.get('pw_confirmar', '')

        if not nombre:
            flash('El nombre no puede estar vacío.', 'error')
            return redirect(url_for('perfil.index'))

        current_user.nombre = nombre

        if pw_actual or pw_nueva:
            if not current_user.check_password(pw_actual):
                flash('La contraseña actual es incorrecta.', 'error')
                return redirect(url_for('perfil.index'))
            if pw_nueva != pw_confirmar:
                flash('La nueva contraseña no coincide.', 'error')
                return redirect(url_for('perfil.index'))
            if len(pw_nueva) < 6:
                flash('La contraseña debe tener al menos 6 caracteres.', 'error')
                return redirect(url_for('perfil.index'))
            current_user.set_password(pw_nueva)

        db.session.commit()
        flash('Perfil actualizado correctamente.', 'success')
        return redirect(url_for('perfil.index'))

    # ✅ PASAR LA VARIABLE AL TEMPLATE
    return render_template('perfil.html', total_tareas=total_tareas)