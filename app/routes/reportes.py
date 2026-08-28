from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Materia, Tarea, Calificacion
from sqlalchemy import func

reportes_bp = Blueprint('reportes', __name__)

@reportes_bp.route('/reportes')
@login_required
def index():
    materias = Materia.query.filter_by(profesor_id=current_user.id).all()

    # Totales globales
    total_tareas = (Tarea.query.join(Materia)
                    .filter(Materia.profesor_id == current_user.id).count())

    promedio_global = (Calificacion.query.join(Tarea).join(Materia)
                       .filter(Materia.profesor_id == current_user.id,
                               Calificacion.nota_final != None)
                       .with_entities(func.avg(Calificacion.nota_final)).scalar())

    # Rangos (escalados a /10 usando nota_maxima de la rúbrica)
    calif_list = (Calificacion.query.join(Tarea).join(Materia)
                  .filter(Materia.profesor_id == current_user.id,
                          Calificacion.nota_final != None)
                  .all())

    rangos = {'excelente': 0, 'bueno': 0, 'regular': 0, 'reprobado': 0}
    for c in calif_list:
        nota_max = c.tarea.rubrica.nota_maxima if c.tarea.rubrica else 10.0
        n10 = c.nota_final / nota_max * 10 if nota_max else 0
        if   n10 >= 9:   rangos['excelente'] += 1
        elif n10 >= 7:   rangos['bueno']     += 1
        elif n10 >= 5:   rangos['regular']   += 1
        else:            rangos['reprobado'] += 1

    # Stats por materia
    materias_stats = []
    for m in materias:
        califs = (Calificacion.query.join(Tarea)
                  .filter(Tarea.materia_id == m.id, Calificacion.nota_final != None)
                  .all())
        total_m = Tarea.query.filter_by(materia_id=m.id).count()
        if califs:
            notas_10 = [(c.nota_final / (c.tarea.rubrica.nota_maxima or 10) * 10) for c in califs]
            prom_m   = round(sum(notas_10) / len(notas_10), 1)
            aprobados = sum(1 for n in notas_10 if n >= 7)
        else:
            prom_m    = None
            aprobados = 0
        materias_stats.append({
            'materia':   m,
            'total':     total_m,
            'calificadas': len(califs),
            'promedio':  prom_m,
            'aprobados': aprobados,
            'reprobados': len(califs) - aprobados,
            'rubricas':  len(m.rubricas),
        })

    # Últimas 5 tareas calificadas
    ultimas = (Tarea.query.join(Materia)
               .filter(Materia.profesor_id == current_user.id)
               .order_by(Tarea.subida_en.desc()).limit(5).all())

    # Informe individual agregado por estudiante (agrupa por nombre a través de todas sus tareas)
    todas_tareas = (Tarea.query.join(Materia)
                     .filter(Materia.profesor_id == current_user.id)
                     .all())
    por_estudiante = {}
    for t in todas_tareas:
        d = por_estudiante.setdefault(t.estudiante_nombre, {
            'nombre': t.estudiante_nombre, 'total': 0, 'calificadas': 0,
            'notas_10': [], 'materias': set()
        })
        d['total'] += 1
        d['materias'].add(t.materia.nombre)
        if t.calificacion and t.calificacion.nota_final is not None and t.rubrica and t.rubrica.nota_maxima:
            d['calificadas'] += 1
            d['notas_10'].append(t.calificacion.nota_final / t.rubrica.nota_maxima * 10)

    estudiantes_stats = []
    for d in por_estudiante.values():
        promedio_e = round(sum(d['notas_10']) / len(d['notas_10']), 1) if d['notas_10'] else None
        estudiantes_stats.append({
            'nombre': d['nombre'],
            'total': d['total'],
            'calificadas': d['calificadas'],
            'promedio': promedio_e,
            'num_materias': len(d['materias']),
        })
    estudiantes_stats.sort(key=lambda x: x['nombre'].lower())

    return render_template('reportes.html',
        materias_stats=materias_stats,
        rangos=rangos,
        total_tareas=total_tareas,
        promedio_global=round(promedio_global, 1) if promedio_global else 0,
        ultimas=ultimas,
        estudiantes_stats=estudiantes_stats,
    )
