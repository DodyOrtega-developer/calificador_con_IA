from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from app.models import Usuario

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo   = request.form.get('correo', '').strip()
        password = request.form.get('password', '')
        usuario  = Usuario.query.filter_by(correo=correo).first()
        if usuario and usuario.check_password(password):
            login_user(usuario)
            if usuario.rol == 'admin':
                return redirect(url_for('admin.index'))
            return redirect(url_for('dashboard.index'))
        flash('Correo o contraseña incorrectos.', 'error')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
