from flask import Blueprint, render_template, request, redirect, url_for, flash
from db_config import get_connection, get_cursor, close_db
from werkzeug.security import generate_password_hash
import re

# 1. Definición del Blueprint (Evita el NameError)
recuperacion_bp = Blueprint('recuperacion', __name__)

def get_db_connection():
    return get_connection()

# 2. TU PATRÓN EXACTO: Una letra, un número, un símbolo y mínimo 8 caracteres
PATRON_SEGURIDAD = r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"

@recuperacion_bp.route('/recuperar-password', methods=['GET'])
def mostrar_recuperacion():
    return render_template('recuperar_password.html')

@recuperacion_bp.route('/verificar-preguntas', methods=['POST'])
def verificar_y_actualizar():
    username = request.form.get('username')
    nueva_pass = request.form.get('new_password')
    
    # Captura de las 3 respuestas
    p1, r1 = request.form.get('pregunta1'), request.form.get('respuesta1', '').strip().lower()
    p2, r2 = request.form.get('pregunta2'), request.form.get('respuesta2', '').strip().lower()
    p3, r3 = request.form.get('pregunta3'), request.form.get('respuesta3', '').strip().lower()

    # Validación con TU PATRÓN
    if not nueva_pass or not re.match(PATRON_SEGURIDAD, nueva_pass):
        flash("La contraseña no cumple: debe tener 8 caracteres, una letra, un número y un símbolo.", "error")
        return render_template('recuperar_password.html', username=username, pregunta1=p1, respuesta1=r1, pregunta2=p2, respuesta2=r2, pregunta3=p3, respuesta3=r3)

    conn = get_db_connection()
    cursor = get_cursor(conn)

    try:
        cursor.execute("SELECT * FROM usuario WHERE nombre_usuario = %s", (username,))
        user = cursor.fetchone()

        if not user:
            flash("Usuario no encontrado.", "error")
            return render_template('recuperar_password.html', username=username, pregunta1=p1, respuesta1=r1, pregunta2=p2, respuesta2=r2, pregunta3=p3, respuesta3=r3)

        # Verificación triple
        check1 = str(user['pregunta1']) == str(p1) and str(user['respuesta1']).strip().lower() == r1
        check2 = str(user['pregunta2']) == str(p2) and str(user['respuesta2']).strip().lower() == r2
        check3 = str(user['pregunta3']) == str(p3) and str(user['respuesta3']).strip().lower() == r3

        if check1 and check2 and check3:
            nueva_pass_hash = generate_password_hash(nueva_pass)
            cursor.execute("UPDATE usuario SET contraseña_hash = %s WHERE id_usuario = %s", 
                         (nueva_pass_hash, user['id_usuario']))
            conn.commit()
            flash("¡Éxito! Contraseña actualizada correctamente.", "success")
            return redirect(url_for('login')) 
        else:
            flash("Las respuestas de seguridad no son correctas.", "error")
            return render_template('recuperar_password.html', username=username, pregunta1=p1, respuesta1=r1, pregunta2=p2, respuesta2=r2, pregunta3=p3, respuesta3=r3)

    except Exception as e:
        print(f"Error: {e}")
        flash("Error interno del servidor.", "error")
        return render_template('recuperar_password.html', username=username, pregunta1=p1, respuesta1=r1, pregunta2=p2, respuesta2=r2, pregunta3=p3, respuesta3=r3)
    finally:
        close_db(conn, cursor)