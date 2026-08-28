from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Materia, Tarea, Calificacion
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def index():
    materias = Materia.query.filter_by(profesor_id=current_user.id).order_by(Materia.nombre).all()

    total_tareas = Tarea.query.join(Materia).filter(Materia.profesor_id==current_user.id).count()

    promedio = (Calificacion.query.join(Tarea).join(Materia)
        .filter(Materia.profesor_id==current_user.id, Calificacion.nota_final!=None)
        .with_entities(func.avg(Calificacion.nota_final)).scalar())

    # Por cada materia: tareas ordenadas más recientes primero
    materias_data = []
    for m in materias:
        tareas = (Tarea.query
            .filter_by(materia_id=m.id)
            .order_by(Tarea.subida_en.desc())
            .all())
        prom_m = (Calificacion.query.join(Tarea)
            .filter(Tarea.materia_id==m.id, Calificacion.nota_final!=None)
            .with_entities(func.avg(Calificacion.nota_final)).scalar())
        materias_data.append({
            'materia': m,
            'tareas': tareas,
            'total': len(tareas),
            'promedio': round(prom_m, 1) if prom_m else None,
        })

    return render_template('dashboard.html',
        materias_data=materias_data,
        total_materias=len(materias),
        total_tareas=total_tareas,
        promedio=round(promedio, 1) if promedio else 0)
