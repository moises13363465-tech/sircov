# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from db_config import get_connection, get_cursor

# Importar los Blueprints
try:
    from usuarios import usuarios_bp
    from flota import flota_bp
    from marca import marca_bp
    from operador import operadores_bp
    from recuperacion import recuperacion_bp 
    from reporte import reportes_bp
    from ayuda import ayuda_bp
    from acerca_de import acerca_de_bp
except ImportError as e:
    print(f"Error importando Blueprints: {e}")

app = Flask(__name__)
app.secret_key = 'sircov_key_secret'

# Configuración para subida de archivos (Logo)
UPLOAD_FOLDER = 'static/img'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    return get_connection()

# --- FUNCIÓN GLOBAL DE AUDITORÍA (HISTORIAL) ---
def registrar_log(id_usuario, accion, tabla, detalle):
    """Registra cualquier movimiento en la tabla historial_sistema"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO historial_sistema (id_usuario, accion, tabla_afectada, detalle) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (id_usuario, accion, tabla, detalle))
        conn.commit()
    except Exception as e:
        print(f"Error crítico registrando historial: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# Inyectar la función en el contexto de Flask
app.jinja_env.globals.update(registrar_log=registrar_log)

# Registro de Blueprints con prefijos
app.register_blueprint(usuarios_bp, url_prefix='/usuarios')
app.register_blueprint(flota_bp, url_prefix='/flota')
app.register_blueprint(marca_bp, url_prefix='/marcas')
app.register_blueprint(operadores_bp, url_prefix='/operadores')
app.register_blueprint(recuperacion_bp, url_prefix='/recuperacion')
app.register_blueprint(reportes_bp, url_prefix='/reportes')
app.register_blueprint(ayuda_bp, url_prefix='/ayuda')  # Registrar el nuevo blueprint de ayuda
app.register_blueprint(acerca_de_bp, url_prefix='/acerca_de')

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form.get('txt_usuario')
        pass_input = request.form.get('txt_password')
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = get_cursor(conn)
            query = "SELECT id_usuario, nombre_usuario, rol, estado, contraseña_hash FROM usuario WHERE nombre_usuario = %s AND estado = 'activo'"
            cursor.execute(query, (user_input,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['contraseña_hash'], pass_input):
                session['usuario'] = user['nombre_usuario']
                session['rol'] = user['rol']
                session['id_usuario'] = user['id_usuario']
                
                registrar_log(user['id_usuario'], 'LOGIN', 'SISTEMA', 'Inicio de sesión exitoso')
                return redirect(url_for('panel'))
            else:
                return render_template('login.html', error="Credenciales inválidas")
        except Exception as e:
            return render_template('login.html', error=f"Error: {e}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
    return render_template('login.html')

@app.route('/panel')
def panel():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('panel_de_inicio.html')

# --- SECCIÓN DE CONFIGURACIÓN ---
@app.route('/configuracion')
def configuracion():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    # Control de acceso basado en roles: Solo admin puede acceder
    if session.get('rol') != 'admin':
        flash('Acceso restringido: Solo administradores pueden entrar al módulo de Configuración.', 'error')
        return redirect(url_for('panel'))
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query_catalogo = """
            SELECT ma.nombre as marca, m.nombre_modelo as modelo, m.id_modelo,
                   st.nombre_subtipo as subtipo, tm.nombre_tipo as tipo, tm.categoria
            FROM modelo m
            JOIN marca ma ON m.id_marca = ma.id_marca
            JOIN sub_tipo st ON m.id_subtipo = st.id_subtipo
            JOIN tipomaquinaria tm ON st.id_tipo_maquinaria = tm.id_tipo_maquinaria
            ORDER BY ma.nombre ASC, m.nombre_modelo ASC
        """
        cursor.execute(query_catalogo)
        catalogo = cursor.fetchall()

        # Obtener Tipos Maestros (solo los 3 principales válidos y futuros)
        cursor.execute("SELECT id_tipo_maquinaria, nombre_tipo, categoria FROM tipomaquinaria WHERE nombre_tipo NOT IN ('GENERAL / OTROS') ORDER BY categoria, nombre_tipo")
        tipos_maestros = cursor.fetchall()
        
        # Obtener Subtipos actuales (solo de los validos)
        cursor.execute("""
            SELECT st.id_subtipo, st.nombre_subtipo, tm.nombre_tipo, tm.categoria
            FROM sub_tipo st
            JOIN tipomaquinaria tm ON st.id_tipo_maquinaria = tm.id_tipo_maquinaria
            WHERE tm.nombre_tipo NOT IN ('GENERAL / OTROS')
            ORDER BY tm.categoria, tm.nombre_tipo, st.nombre_subtipo
        """)
        subtipos_disponibles = cursor.fetchall()
        
        # Obtener Marcas actuales
        cursor.execute("SELECT id_marca, nombre FROM marca ORDER BY nombre")
        marcas_lista = cursor.fetchall()

        cursor.execute("SELECT institucion, departamento, rif FROM config_reporte WHERE id = 1")
        reporte = cursor.fetchone()
        
        cursor.execute("SELECT pregunta1 FROM usuario WHERE id_usuario = %s", (session['id_usuario'],))
        usuario_data = cursor.fetchone()

        query_historial = """
            SELECT h.*, u.nombre_usuario 
            FROM historial_sistema h
            LEFT JOIN usuario u ON h.id_usuario = u.id_usuario
            ORDER BY h.fecha_registro DESC
            LIMIT 50
        """
        cursor.execute(query_historial)
        historial = cursor.fetchall()
        
        return render_template('configuracion.html', 
                               catalogo=catalogo, 
                               tipos_maestros=tipos_maestros,
                               subtipos_disponibles=subtipos_disponibles,
                               marcas_lista=marcas_lista,
                               reporte=reporte, 
                               usuario=usuario_data,
                               historial=historial)
                               
    except Exception as e:
        print(f"Error en configuracion: {e}")
        return f"Error interno: {e}", 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/agregar_catalogo', methods=['POST'])
def agregar_catalogo():
    if 'usuario' not in session: return redirect(url_for('login'))
    
    # Control de acceso basado en roles: Solo admin puede agregar
    if session.get('rol') != 'admin':
        flash('Acceso restringido: Solo administradores pueden gestionar el catálogo.', 'error')
        return redirect(url_for('panel'))
    
    marca_select = request.form.get('marca_select', '').strip()
    marca_input = request.form.get('marca', '').strip()
    
    # Determinar qué marca usar (la del select o la nueva manual)
    if marca_select and marca_select != 'OTRA':
        nombre_marca = marca_select
    else:
        nombre_marca = marca_input
        
    if not nombre_marca:
        flash("Debes ingresar o seleccionar una Marca válida.", "error")
        return redirect(url_for('configuracion'))
        
    nombre_modelo = request.form.get('modelo', '').strip()
    id_subtipo = request.form.get('id_subtipo')
    
    if not id_subtipo:
        flash("Debes seleccionar el subtipo al que pertenece la marca.", "error")
        return redirect(url_for('configuracion'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id_marca FROM marca WHERE nombre = %s", (nombre_marca,))
        res = cursor.fetchone()
        if res:
            id_marca = res['id_marca']
        else:
            cursor.execute("INSERT INTO marca (nombre) VALUES (%s)", (nombre_marca,))
            id_marca = cursor.lastrowid
            
        cursor.execute("INSERT INTO modelo (id_marca, id_subtipo, nombre_modelo) VALUES (%s, %s, %s)", (id_marca, id_subtipo, nombre_modelo))
        conn.commit()
        
        registrar_log(session['id_usuario'], 'CREAR', 'CATALOGO', f"Agregó modelo {nombre_modelo} a marca {nombre_marca}")
        flash(f"Registrado con éxito: {nombre_marca} {nombre_modelo}", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('configuracion'))

@app.route('/agregar_subtipo', methods=['POST'])
def agregar_subtipo():
    if 'usuario' not in session: return redirect(url_for('login'))
    if session.get('rol') != 'admin': return redirect(url_for('panel'))
    
    nombre_sub = request.form.get('nombre_subtipo', '').strip()
    id_tipo = request.form.get('id_tipo_maquinaria')
    
    if not nombre_sub or not id_tipo:
        flash("Debes ingresar el nombre del subtipo y seleccionar su Tipo Maestro.", "warning")
        return redirect(url_for('configuracion') + '#marcas-modelos')
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id_subtipo FROM sub_tipo WHERE UPPER(nombre_subtipo) = %s AND id_tipo_maquinaria = %s", 
                       (nombre_sub.upper(), id_tipo))
        if cursor.fetchone():
            flash("Esa categoría (Subtipo) ya existe para el Tipo seleccionado.", "warning")
        else:
            cursor.execute("INSERT INTO sub_tipo (nombre_subtipo, id_tipo_maquinaria) VALUES (%s, %s)", 
                           (nombre_sub.capitalize(), id_tipo))
            conn.commit()
            registrar_log(session['id_usuario'], 'CREAR', 'CATALOGO', f"Agregó nuevo subtipo '{nombre_sub}'")
            flash("Subtipo añadido exitosamente", "success")
    except Exception as e:
        flash(f"Error al agregar subtipo: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('configuracion') + '#marcas-modelos')

@app.route('/configuracion/editar_modelo/<int:id>', methods=['POST'])
def editar_modelo(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    if session.get('rol') != 'admin': return redirect(url_for('panel'))
    
    nuevo_nombre = request.form.get('nuevo_nombre')
    if not nuevo_nombre:
        flash("El nombre no puede estar vacío.", "error")
        return redirect(url_for('configuracion', tab='eliminar') + '#marcas-modelos')
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE modelo SET nombre_modelo = %s WHERE id_modelo = %s", (nuevo_nombre.upper(), id))
        conn.commit()
        registrar_log(session['id_usuario'], 'EDITAR', 'CATALOGO', f"Editó el modelo a: {nuevo_nombre.upper()}")
        flash("Modelo editado correctamente", "success")
    except Exception as e:
        flash(f"Error al editar: {e}", "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('configuracion', tab='eliminar') + '#marcas-modelos')

@app.route('/configuracion/editar_subtipo/<int:id>', methods=['POST'])
def editar_subtipo(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    if session.get('rol') != 'admin': return redirect(url_for('panel'))
    
    nuevo_nombre = request.form.get('nuevo_nombre')
    if not nuevo_nombre:
        flash("El nombre no puede estar vacío.", "error")
        return redirect(url_for('configuracion', tab='eliminar') + '#marcas-modelos')
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE sub_tipo SET nombre_subtipo = %s WHERE id_subtipo = %s", (nuevo_nombre.upper(), id))
        conn.commit()
        registrar_log(session['id_usuario'], 'EDITAR', 'CATALOGO', f"Editó el subtipo a: {nuevo_nombre.upper()}")
        flash("Subtipo editado correctamente", "success")
    except Exception as e:
        flash(f"Error al editar: {e}", "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('configuracion', tab='eliminar') + '#marcas-modelos')

@app.route('/configuracion/editar_marca/<int:id>', methods=['POST'])
def editar_marca(id):
    if 'usuario' not in session: return redirect(url_for('login'))
    if session.get('rol') != 'admin': return redirect(url_for('panel'))
    
    nuevo_nombre = request.form.get('nuevo_nombre')
    if not nuevo_nombre:
        flash("El nombre no puede estar vacío.", "error")
        return redirect(url_for('configuracion', tab='eliminar') + '#marcas-modelos')
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE marca SET nombre = %s WHERE id_marca = %s", (nuevo_nombre.upper(), id))
        conn.commit()
        registrar_log(session['id_usuario'], 'EDITAR', 'CATALOGO', f"Editó la marca a: {nuevo_nombre.upper()}")
        flash("Marca editada correctamente", "success")
    except Exception as e:
        flash(f"Error al editar: {e}", "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('configuracion', tab='eliminar') + '#marcas-modelos')

@app.route('/configurar_membrete', methods=['POST'])
def configurar_membrete():
    if 'usuario' not in session: return redirect(url_for('login'))
    
    # Control de acceso basado en roles: Solo admin puede configurar
    if session.get('rol') != 'admin':
        flash('Acceso restringido: Solo administradores pueden configurar el membrete.', 'error')
        return redirect(url_for('panel'))
    
    inst = request.form.get('institucion')
    dept = request.form.get('departamento')
    rif = request.form.get('rif')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE config_reporte SET institucion=%s, departamento=%s, rif=%s WHERE id=1", (inst, dept, rif))
        if cursor.rowcount == 0:
            cursor.execute("INSERT INTO config_reporte (id, institucion, departamento, rif) VALUES (1, %s, %s, %s)", (inst, dept, rif))
        conn.commit()
        
        registrar_log(session['id_usuario'], 'ACTUALIZAR', 'CONFIGURACION', "Actualizó el membrete de los reportes")
        flash("Membrete guardado", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('configuracion'))

@app.route('/subir_logo_reporte', methods=['POST'])
def subir_logo_reporte():
    if 'usuario' not in session: return redirect(url_for('login'))
    
    # Control de acceso basado en roles: Solo admin puede subir logo
    if session.get('rol') != 'admin':
        flash('Acceso restringido: Solo administradores pueden actualizar el logo.', 'error')
        return redirect(url_for('panel'))
    
    if 'file_logo' not in request.files: return redirect(url_for('configuracion'))
    
    file = request.files['file_logo']
    if file and file.filename != '':
        filename = "SIRCOV2.png"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        registrar_log(session['id_usuario'], 'ACTUALIZAR', 'CONFIGURACION', "Actualizó el logo del sistema")
        flash("Logo actualizado", "success")
    return redirect(url_for('configuracion'))

@app.route('/logout')
def logout():
    if 'id_usuario' in session:
        registrar_log(session['id_usuario'], 'LOGOUT', 'SISTEMA', 'Cerró sesión')
    session.clear()
    return redirect(url_for('login'))

# --- RUTAS DE CONSULTA DINÁMICA (CORREGIDAS SEGÚN TU DB) ---

@app.route('/get_subtipos/<int:id_tipo>')
def get_subtipos(id_tipo):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Nombres de tabla y columnas extraídos de tu imagen de phpMyAdmin
        query = "SELECT id_subtipo, nombre_subtipo FROM sub_tipo WHERE id_tipo_maquinaria = %s"
        cursor.execute(query, (id_tipo,))
        return jsonify(cursor.fetchall())
    except Exception as e:
        print(f"Error en get_subtipos: {e}")
        return jsonify([]), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/get_marcas_filtradas/<int:id_subtipo>')
def get_marcas_filtradas(id_subtipo):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Se asume la columna 'id_subtipo' en la tabla modelo según el patrón de la DB
        query = """SELECT DISTINCT ma.id_marca, ma.nombre 
                   FROM marca ma 
                   INNER JOIN modelo mo ON ma.id_marca = mo.id_marca 
                   WHERE mo.id_subtipo = %s"""
        cursor.execute(query, (id_subtipo,))
        return jsonify(cursor.fetchall())
    except Exception as e:
        print(f"Error en get_marcas: {e}")
        return jsonify([]), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/get_modelos_filtrados/<int:id_marca>/<int:id_subtipo>')
def get_modelos_filtrados(id_marca, id_subtipo):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id_modelo, nombre_modelo FROM modelo WHERE id_marca = %s AND id_subtipo = %s"
        cursor.execute(query, (id_marca, id_subtipo))
        return jsonify(cursor.fetchall())
    except Exception as e:
        print(f"Error en get_modelos: {e}")
        return jsonify([]), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    # Usar puerto de Render si existe, de lo contrario 8080 local
    port = int(os.environ.get('PORT', 8080))
    # Debug False si estamos en Render
    is_debug = os.environ.get('DATABASE_URL') is None
    app.run(host='0.0.0.0', port=port, debug=is_debug)