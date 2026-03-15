from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db_config import get_connection, get_cursor, close_db
from werkzeug.security import generate_password_hash
import re

usuarios_bp = Blueprint('usuarios', __name__)

def get_db_connection():
    return get_connection()

def existe_usuario_o_codigo(nombre, codigo, exclude_id=None):
    conn = get_db_connection()
    cursor = get_cursor(conn)
    try:
        if exclude_id:
            query = "SELECT id_usuario FROM usuario WHERE (nombre_usuario = %s OR cod_usuario = %s) AND id_usuario != %s"
            cursor.execute(query, (nombre, codigo, exclude_id))
        else:
            query = "SELECT id_usuario FROM usuario WHERE nombre_usuario = %s OR cod_usuario = %s"
            cursor.execute(query, (nombre, codigo))
        return cursor.fetchone()
    finally:
        close_db(conn, cursor)

# Expresión regular: Una letra, un número, un símbolo y mínimo 8 caracteres
PATRON_SEGURIDAD = r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"

# --- RUTAS DE GESTIÓN (VISTAS) ---

@usuarios_bp.route('/gestion_usuarios')
def gestion_usuarios():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    usuario_activo = session.get('usuario')
    try:
        conn = get_db_connection()
        cursor = get_cursor(conn)
        query = "SELECT id_usuario, nombre_usuario, cod_usuario, rol, fecha_registro, estado FROM usuario"
        cursor.execute(query)
        usuarios_db = cursor.fetchall()
        return render_template('gestion_de_usuario.html', usuarios=usuarios_db, usuario_activo=usuario_activo)
    except Exception as e:
        print(f"Error en gestion_usuarios: {e}")
        return f"Error: {e}"
    finally:
        close_db(conn, cursor)

@usuarios_bp.route('/agregar_usuario')
def vista_agregar_usuario():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    usuario_activo = session.get('usuario')
    return render_template('agregar_usuario.html', usuario_activo=usuario_activo)

@usuarios_bp.route('/editar_usuario/<int:id>', methods=['GET'])
def vista_editar_usuario(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario_activo = session.get('usuario')
    try:
        conn = get_db_connection()
        cursor = get_cursor(conn)
        cursor.execute("SELECT * FROM usuario WHERE id_usuario = %s", (id,))
        usuario_data = cursor.fetchone()
        
        if not usuario_data:
            flash("Usuario no encontrado", "error")
            return redirect(url_for('usuarios.gestion_usuarios'))

        return render_template('editar_usuario.html', user=usuario_data, usuario_activo=usuario_activo)

    except Exception as e:
        flash(f"Error al cargar datos: {e}", "error")
        return redirect(url_for('usuarios.gestion_usuarios'))
    finally:
        close_db(conn, cursor)

# --- RUTAS DE ACCIÓN (PROCESAMIENTO) ---

@usuarios_bp.route('/crear_usuario', methods=['POST'])
def crear_usuario():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    nombre = request.form.get('nombre_usuario', '').strip()
    codigo = request.form.get('cod_usuario', '').strip()
    password_plana = request.form.get('contraseña_hash', '').strip()
    rol = request.form.get('rol')
    
    estado_input = request.form.get('estado')
    estado = 'activo' if estado_input in ['1', 'activo'] else 'inactivo'
    
    p1 = request.form.get('pregunta1')
    r1 = request.form.get('respuesta1', "").strip().lower()
    p2 = request.form.get('pregunta2')
    r2 = request.form.get('respuesta2', "").strip().lower()
    p3 = request.form.get('pregunta3')
    r3 = request.form.get('respuesta3', "").strip().lower()

    if not all([nombre, codigo, password_plana, r1, r2, r3]):
        flash("Todos los campos son obligatorios", "error")
        return redirect(url_for('usuarios.vista_agregar_usuario'))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        password_encriptada = generate_password_hash(password_plana)

        query = """INSERT INTO usuario 
                   (nombre_usuario, cod_usuario, contraseña_hash, rol, estado, 
                   pregunta1, respuesta1, pregunta2, respuesta2, pregunta3, respuesta3) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        
        valores = (nombre, codigo, password_encriptada, rol, estado, p1, r1, p2, r2, p3, r3)
        cursor.execute(query, valores)
        conn.commit()

        # --- REGISTRO EN HISTORIAL ---
        from app import registrar_log
        registrar_log(session['id_usuario'], 'CREAR', 'USUARIOS', f"Creó al usuario: {nombre} (Código: {codigo})")
        
        flash("¡Usuario guardado exitosamente!", "success")
        return redirect(url_for('usuarios.gestion_usuarios'))

    except mysql.connector.Error as err:
        if err.errno == 1062:
            flash("Error: El usuario o código ya existen.", "error")
        else:
            flash(f"Error de base de datos: {err.msg}", "error")
        return redirect(url_for('usuarios.vista_agregar_usuario'))
    finally:
        close_db(conn, cursor)

@usuarios_bp.route('/actualizar_usuario/<int:id>', methods=['POST'])
def actualizar_usuario(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    nombre = request.form.get('nombre_usuario', '').strip()
    codigo = request.form.get('cod_usuario', '').strip()
    rol = request.form.get('rol')
    estado = request.form.get('estado')
    
    p1 = request.form.get('pregunta1')
    r1 = request.form.get('respuesta1', '').strip().lower()
    p2 = request.form.get('pregunta2')
    r2 = request.form.get('respuesta2', '').strip().lower()
    p3 = request.form.get('pregunta3')
    r3 = request.form.get('respuesta3', '').strip().lower()

    if existe_usuario_o_codigo(nombre, codigo, exclude_id=id):
        flash("Error: El nombre o código ya pertenecen a otro usuario.", "error")
        return redirect(url_for('usuarios.vista_editar_usuario', id=id))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """UPDATE usuario 
                   SET nombre_usuario=%s, cod_usuario=%s, rol=%s, estado=%s, 
                       pregunta1=%s, respuesta1=%s, pregunta2=%s, respuesta2=%s,
                       pregunta3=%s, respuesta3=%s 
                   WHERE id_usuario=%s"""
        
        valores = (nombre, codigo, rol, estado, p1, r1, p2, r2, p3, r3, id)
        cursor.execute(query, valores)
        conn.commit()

        # --- REGISTRO EN HISTORIAL ---
        from app import registrar_log
        registrar_log(session['id_usuario'], 'ACTUALIZAR', 'USUARIOS', f"Modificó datos del usuario: {nombre} (ID: {id})")
        
        flash("Usuario actualizado correctamente", "success")
        
    except Exception as e:
        flash(f"Error al actualizar: {e}", "error")
        return redirect(url_for('usuarios.vista_editar_usuario', id=id))
    finally:
        close_db(conn, cursor)
    
    return redirect(url_for('usuarios.gestion_usuarios'))

@usuarios_bp.route('/eliminar_usuario/<int:id>')
def eliminar_usuario(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener nombre antes de eliminar para el log
        cursor.execute("SELECT nombre_usuario FROM usuario WHERE id_usuario = %s", (id,))
        res = cursor.fetchone()
        nombre_eliminado = res[0] if res else "Desconocido"

        cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (id,))
        conn.commit()

        # --- REGISTRO EN HISTORIAL ---
        from app import registrar_log
        registrar_log(session['id_usuario'], 'ELIMINAR', 'USUARIOS', f"Eliminó al usuario: {nombre_eliminado} (ID: {id})")
        
        flash("Usuario eliminado correctamente", "success")
    except Exception as e:
        flash("No se pudo eliminar el usuario", "error")
    finally:
        close_db(conn, cursor)
    
    return redirect(url_for('usuarios.gestion_usuarios'))