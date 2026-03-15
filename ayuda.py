# ayuda.py
from flask import Blueprint, render_template, session, redirect, url_for

ayuda_bp = Blueprint('ayuda', __name__, url_prefix='/ayuda')

@ayuda_bp.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('ayuda.html')  # Asumiendo que el template se llama ayuda.html con el contenido de la guía