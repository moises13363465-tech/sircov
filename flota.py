from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from db_config import get_connection, get_cursor, close_db
import re

flota_bp = Blueprint('flota', __name__)

# --- CONFIGURACIÓN DE CONEXIÓN ---


def get_db_connection():
    return get_connection()

# --- VISTA PRINCIPAL (GESTIÓN DE FLOTA) ---
@flota_bp.route('/gestion_flota')
def gestion_flota():
    if 'usuario' not in session: 
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = get_cursor(conn, buffered=True)
    
    # Consulta optimizada para la tabla de gestión incluyendo operadores
    query = """SELECT m.id_maquinaria, ma.nombre AS nombre_marca, mo.nombre_modelo, 
                tm.nombre_tipo, st.nombre_subtipo, tm.categoria, m.placa, m.año_fabricacion, m.potencia, m.estado,
                m.serial_chasis, m.nro_motor, m.tipo_transmision, m.nro_eje, 
                m.nro_ruedas, m.tanque, m.observaciones,
                GROUP_CONCAT(CONCAT(o.nombres, ' ', o.apellidos) SEPARATOR ', ') as operadores
                FROM maquinaria m
                LEFT JOIN modelo mo ON m.id_modelo = mo.id_modelo
                LEFT JOIN marca ma ON mo.id_marca = ma.id_marca
                LEFT JOIN sub_tipo st ON mo.id_subtipo = st.id_subtipo
                LEFT JOIN tipomaquinaria tm ON st.id_tipo_maquinaria = tm.id_tipo_maquinaria
                LEFT JOIN operador_maquinaria om ON m.id_maquinaria = om.id_maquinaria
                LEFT JOIN operador o ON om.id_operador = o.id_operador
                GROUP BY m.id_maquinaria
                ORDER BY m.id_maquinaria DESC"""
    
    cursor.execute(query)
    equipos = cursor.fetchall()
    close_db(conn, cursor)
    return render_template('gestion_flota.html', equipos=equipos)

# --- RUTAS AJAX PARA EL FLUJO DINÁMICO (CATEGORÍA -> SUBTIPO -> MARCA -> MODELO) ---

@flota_bp.route('/get_subtipos/<string:cat_name>')
def get_subtipos(cat_name):
    conn = get_db_connection()
    cursor = get_cursor(conn)
    categoria_busqueda = cat_name.lower().strip()
    
    # Retornamos los SUBTIPOS reales (Sedán, Camión Volteo, Pick-up, etc.)
    sql = """SELECT st.id_subtipo, st.nombre_subtipo 
             FROM sub_tipo st
             JOIN tipomaquinaria tm ON st.id_tipo_maquinaria = tm.id_tipo_maquinaria
             WHERE UPPER(tm.categoria) = UPPER(%s) AND tm.nombre_tipo NOT IN ('GENERAL / OTROS')
             ORDER BY st.nombre_subtipo ASC"""
             
    cursor.execute(sql, (categoria_busqueda,))
    subtipos = cursor.fetchall()
    close_db(conn, cursor)
    return jsonify(subtipos)

@flota_bp.route('/get_marcas_filtradas/<int:id_subtipo>')
def get_marcas_filtradas(id_subtipo):
    conn = get_db_connection()
    cursor = get_cursor(conn)
    # Buscamos marcas exactas que tengan modelos para el subtipo seleccionado
    sql = """SELECT DISTINCT ma.id_marca, ma.nombre 
             FROM marca ma
             JOIN modelo mo ON ma.id_marca = mo.id_marca
             WHERE mo.id_subtipo = %s
             ORDER BY ma.nombre ASC"""
    cursor.execute(sql, (id_subtipo,))
    marcas = cursor.fetchall()
    close_db(conn, cursor)
    return jsonify(marcas)

@flota_bp.route('/get_modelos_filtrados/<int:id_marca>/<int:id_subtipo>')
def get_modelos_filtrados(id_marca, id_subtipo):
    conn = get_db_connection()
    cursor = get_cursor(conn)
    # Modelos filtrados por Marca Y Subtipo exacto (Ej: Toyota -> Sedán = Corolla)
    sql = """SELECT id_modelo, nombre_modelo 
             FROM modelo 
             WHERE id_marca = %s AND id_subtipo = %s
             ORDER BY nombre_modelo ASC"""
    cursor.execute(sql, (id_marca, id_subtipo))
    modelos = cursor.fetchall()
    close_db(conn, cursor)
    return jsonify(modelos)

# --- PROCESO DE REGISTRO PASO 1 (DATOS GENERALES) ---
@flota_bp.route('/agregar_paso1', methods=['GET', 'POST'])
def agregar_paso1():
    if 'usuario' not in session: 
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        id_modelo = request.form.get('id_modelo')
        id_subtipo = request.form.get('id_subtipo')
        
        # Validación de seguridad: no permitir avanzar si el modelo no fue seleccionado
        if not id_modelo or not id_subtipo:
            flash("Error: Debe seleccionar un Subtipo, Marca y Modelo válidos para continuar.", "error")
            return redirect(url_for('flota.agregar_paso1'))

        # Guardamos en sesión para persistir entre pasos
        session['reg_equipo'] = {
            'categoria': request.form.get('categoria'),
            'id_modelo': id_modelo,
            'id_subtipo': id_subtipo,
            'observaciones': request.form.get('observaciones')
        }
        session.modified = True
        return redirect(url_for('flota.agregar_paso2'))

    return render_template('agregar_equipo.html')

# --- PASO 2: IDENTIFICACIÓN (PLACA Y SERIALES) ---
@flota_bp.route('/agregar_paso2', methods=['GET', 'POST'])
def agregar_paso2():
    if 'usuario' not in session: 
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        placa = request.form.get('placa', '').strip().upper()
        nro_motor = request.form.get('nro_motor', '').strip().upper()
        serial_chasis = request.form.get('serial_chasis', '').strip().upper()
        año = request.form.get('año_fabricacion')

        # Validación de seguridad
        regex_flexible = r'^[A-Z\d\-\s]{4,25}$'

        if nro_motor and not re.match(regex_flexible, nro_motor):
            flash("Formato de Número de Motor no válido.", "error")
            return redirect(url_for('flota.agregar_paso2'))

        datos = session.get('reg_equipo', {})
        datos.update({
            'placa': placa if placa != "" else "S/P",
            'nro_motor': nro_motor,
            'serial_chasis': serial_chasis,
            'año_fabricacion': año
        })
        
        session['reg_equipo'] = datos
        session.modified = True
        return redirect(url_for('flota.agregar_paso3'))

    return render_template('agregar_paso2.html')

# --- PASO 3: ESPECIFICACIONES TÉCNICAS Y GUARDADO ---
@flota_bp.route('/agregar_paso3', methods=['GET', 'POST'])
def agregar_paso3():
    if 'usuario' not in session: 
        return redirect(url_for('login'))

    if request.method == 'POST':
        datos_previos = session.get('reg_equipo', {})
        id_usuario_actual = session.get('id_usuario')
        
        try:
            tanque_litros = float(request.form.get('tanque', 0))
        except:
            tanque_litros = 0.0

        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            sql = """INSERT INTO maquinaria 
                      (serial_chasis, nro_motor, año_fabricacion, placa, 
                       id_modelo, tipo_transmision, nro_eje, nro_ruedas, 
                       codigo_neumaticos, potencia, tanque, id_usuario, observaciones, estado) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'OPERATIVO')"""
            
            valores = (
                datos_previos.get('serial_chasis'),
                datos_previos.get('nro_motor'),
                datos_previos.get('año_fabricacion'),
                datos_previos.get('placa'),
                datos_previos.get('id_modelo'),
                request.form.get('tipo_transmision'),
                request.form.get('nro_eje'),
                request.form.get('nro_ruedas'),
                request.form.get('codigo_neumaticos'),
                request.form.get('potencia'),
                tanque_litros,
                id_usuario_actual,
                datos_previos.get('observaciones')
            )
            
            cur.execute(sql, valores)
            id_maquinaria = cur.lastrowid
            
            operadores_ids = request.form.getlist('operadores')
            if operadores_ids:
                for op_id in operadores_ids:
                    cur.execute("INSERT INTO operador_maquinaria (id_operador, id_maquinaria) VALUES (%s, %s)", (op_id, id_maquinaria))
            
            conn.commit()
            
            # Auditoría
            from app import registrar_log
            registrar_log(id_usuario_actual, 'CREAR', 'MAQUINARIA', f"Registró equipo placa: {datos_previos.get('placa')}")
            
            session.pop('reg_equipo', None)
            flash("¡Maquinaria registrada con éxito!", "success")
            return redirect(url_for('flota.gestion_flota'))
            
        except Exception as err:
            if conn: conn.rollback()
            flash(f"Error al guardar: {err}", "error")
            return redirect(url_for('flota.agregar_paso1'))
        finally:
            close_db(conn, cur)

    conn = get_db_connection()
    cur = get_cursor(conn)
    cur.execute("SELECT id_operador, nombres, apellidos FROM operador WHERE estado = 'OPERATIVO' ORDER BY nombres")
    operadores = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('agregar_paso3.html', operadores=operadores)

# --- EDITAR EQUIPO ---
@flota_bp.route('/editar/<int:id_maquinaria>', methods=['GET', 'POST'])
def editar_maquinaria(id_maquinaria):
    if 'usuario' not in session: return redirect(url_for('login'))
    
    # Restricción: Solo administradores pueden editar
    if session.get('rol') != 'admin':
        flash('Acceso denegado: Solo el administrador puede editar equipos.', 'error')
        return redirect(url_for('flota.gestion_flota'))
    
    conn = get_db_connection()
    cursor = get_cursor(conn)

    if request.method == 'POST':
        # Captura de todos los campos técnicos
        placa = request.form.get('placa', 'S/P').strip().upper()
        serial_chasis = request.form.get('serial_chasis', '').strip().upper()
        nro_motor = request.form.get('nro_motor', '').strip().upper()
        anio = request.form.get('año_fabricacion')
        transmision = request.form.get('tipo_transmision')
        ejes = request.form.get('nro_eje')
        ruedas = request.form.get('nro_ruedas')
        neumaticos = request.form.get('codigo_neumaticos')
        potencia = request.form.get('potencia')
        estado = request.form.get('estado')
        obs = request.form.get('observaciones')
        
        try:
            tanque = float(request.form.get('tanque', 0))
        except:
            tanque = 0.0

        sql = """UPDATE maquinaria SET 
                 placa=%s, serial_chasis=%s, nro_motor=%s, año_fabricacion=%s,
                 tipo_transmision=%s, nro_eje=%s, nro_ruedas=%s, codigo_neumaticos=%s,
                 potencia=%s, tanque=%s, estado=%s, observaciones=%s 
                 WHERE id_maquinaria=%s"""
        
        cursor.execute(sql, (placa, serial_chasis, nro_motor, anio, transmision, 
                            ejes, ruedas, neumaticos, potencia, tanque, estado, obs, id_maquinaria))
        
        # Actualizar asignación de operadores
        cursor.execute("DELETE FROM operador_maquinaria WHERE id_maquinaria = %s", (id_maquinaria,))
        operadores_seleccionados = request.form.getlist('operadores')
        for op_id in operadores_seleccionados:
            cursor.execute("INSERT INTO operador_maquinaria (id_operador, id_maquinaria) VALUES (%s, %s)", (op_id, id_maquinaria))
            
        conn.commit()
        
        from app import registrar_log
        registrar_log(session['id_usuario'], 'ACTUALIZAR', 'MAQUINARIA', f"Editó equipo ID: {id_maquinaria}")
        flash('Equipo actualizado correctamente', 'success')
        close_db(conn, cursor)
        return redirect(url_for('flota.gestion_flota'))
    
    # Consulta ampliada para mostrar info del modelo actual
    query = """SELECT m.*, ma.nombre AS nombre_marca, mo.nombre_modelo, tm.nombre_tipo
               FROM maquinaria m
               LEFT JOIN modelo mo ON m.id_modelo = mo.id_modelo
               LEFT JOIN marca ma ON mo.id_marca = ma.id_marca
               LEFT JOIN sub_tipo st ON mo.id_subtipo = st.id_subtipo
               LEFT JOIN tipomaquinaria tm ON st.id_tipo_maquinaria = tm.id_tipo_maquinaria
               WHERE m.id_maquinaria = %s"""
    cursor.execute(query, (id_maquinaria,))
    equipo = cursor.fetchone()

    # Obtener todos los operadores para la asignación
    cursor.execute("SELECT id_operador, nombres, apellidos FROM operador ORDER BY nombres ASC")
    todos_operadores = cursor.fetchall()

    # Obtener IDs de operadores ya asignados
    cursor.execute("SELECT id_operador FROM operador_maquinaria WHERE id_maquinaria = %s", (id_maquinaria,))
    asignados_ids = [row['id_operador'] for row in cursor.fetchall()]

    close_db(conn, cursor)
    return render_template('editar_flota.html', 
                          equipo=equipo, 
                          operadores=todos_operadores,
                          asignados_ids=asignados_ids)

# --- EXPEDIENTE DE MAQUINARIA ---
@flota_bp.route('/expediente/<int:id_maquinaria>')
def expediente_maquinaria(id_maquinaria):
    if 'usuario' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = get_cursor(conn)
    
    # 1. Datos técnicos del equipo
    query_equipo = """SELECT m.*, ma.nombre AS nombre_marca, mo.nombre_modelo, 
                             tm.nombre_tipo, tm.categoria
                      FROM maquinaria m
                      LEFT JOIN modelo mo ON m.id_modelo = mo.id_modelo
                      LEFT JOIN marca ma ON mo.id_marca = ma.id_marca
                      LEFT JOIN sub_tipo st ON mo.id_subtipo = st.id_subtipo
                      LEFT JOIN tipomaquinaria tm ON st.id_tipo_maquinaria = tm.id_tipo_maquinaria
                      WHERE m.id_maquinaria = %s"""
    cursor.execute(query_equipo, (id_maquinaria,))
    equipo = cursor.fetchone()
    
    if not equipo:
        flash("Equipo no encontrado", "error")
        return redirect(url_for('flota.gestion_flota'))
        
    # 2. Operadores asignados
    query_ops = """SELECT o.id_operador, o.cedula, o.nombres, o.apellidos, o.telefono
                   FROM operador o
                   JOIN operador_maquinaria om ON o.id_operador = om.id_operador
                   WHERE om.id_maquinaria = %s"""
    cursor.execute(query_ops, (id_maquinaria,))
    operadores = cursor.fetchall()
    
    # 3. Datos de configuración (encabezado)
    cursor.execute("SELECT * FROM config_reporte LIMIT 1")
    encabezado = cursor.fetchone()
    
    close_db(conn, cursor)
    
    return render_template('expediente_maquinaria.html', 
                           equipo=equipo, 
                           operadores=operadores,
                           encabezado=encabezado)



# --- ELIMINAR EQUIPO ---
@flota_bp.route('/eliminar/<int:id_maquinaria>')
def eliminar_maquinaria(id_maquinaria):
    if 'usuario' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM maquinaria WHERE id_maquinaria = %s", (id_maquinaria,))
        conn.commit()
        from app import registrar_log
        registrar_log(session['id_usuario'], 'ELIMINAR', 'MAQUINARIA', f"Eliminó ID: {id_maquinaria}")
        flash('Equipo eliminado', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    finally:
        close_db(conn, cursor)
    return redirect(url_for('flota.gestion_flota'))


# --- ELIMINAR TODA LA MAQUINARIA (Masivo) ---
@flota_bp.route('/eliminar_todo')
def eliminar_todas_maquinarias():
    if 'usuario' not in session: return redirect(url_for('login'))
    
    # Restricción: Solo administradores pueden realizar esta acción
    if session.get('rol') != 'admin':
        flash('Acceso denegado: Solo el administrador puede realizar la eliminación masiva.', 'error')
        return redirect(url_for('flota.gestion_flota'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Eliminar asignaciones de operadores primero (por integridad referencial)
        cursor.execute("DELETE FROM operador_maquinaria")
        
        # 2. Eliminar toda la maquinaria
        cursor.execute("DELETE FROM maquinaria")
        
        conn.commit()
        
        from app import registrar_log
        registrar_log(session['id_usuario'], 'ELIMINAR', 'MAQUINARIA', "REALIZÓ ELIMINACIÓN MASIVA DE TODA LA FLOTA")
        
        flash('¡Toda la flota ha sido eliminada con éxito!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al realizar la eliminación masiva: {str(e)}', 'error')
    finally:
        close_db(conn, cursor)
        
    return redirect(url_for('flota.gestion_flota'))
