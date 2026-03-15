# acerca_de.py
from flask import Blueprint, render_template, session, redirect, url_for

acerca_de_bp = Blueprint('acerca_de', __name__, url_prefix='/acerca_de')

@acerca_de_bp.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('acerca_de.html')  # Asumiendo que el template se llama acerca_de.html con el contenido de la guía