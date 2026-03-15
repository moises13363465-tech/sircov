from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from db_config import get_connection, get_cursor, close_db
import sys

reportes_bp = Blueprint('reportes', __name__)



def obtener_conexion():
    return mysql.connector.connect(**db_config)

@reportes_bp.route('/reporte')
def generar_reporte():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    conn = None
    try:
        conn = obtener_conexion()
        cursor = get_cursor(conn)
        
        # 1. Consultar el membrete dinámico configurado por el usuario
        cursor.execute("SELECT institucion, departamento, rif FROM config_reporte LIMIT 1")
        config_encabezado = cursor.fetchone()
        
        # 2. Consulta de los datos de la flota
        query = """
            SELECT 
                maq.id_maquinaria, 
                mar.nombre AS nombre_marca, 
                mo.nombre_modelo, 
                tm.nombre_tipo,
                tm.categoria,
                maq.placa, 
                maq.nro_motor, 
                maq.serial_chasis AS serial, 
                maq.año_fabricacion, 
                maq.tanque, 
                maq.potencia,
                maq.estado
            FROM maquinaria maq
            LEFT JOIN modelo mo ON maq.id_modelo = mo.id_modelo
            LEFT JOIN marca mar ON mo.id_marca = mar.id_marca
            LEFT JOIN sub_tipo st ON mo.id_subtipo = st.id_subtipo
            LEFT JOIN tipomaquinaria tm ON st.id_tipo_maquinaria = tm.id_tipo_maquinaria
            ORDER BY maq.id_maquinaria ASC
        """
        cursor.execute(query)
        datos = cursor.fetchall()
        
        return render_template('reporte.html', 
                               datos=datos, 
                               encabezado=config_encabezado, 
                               titulo="Reporte General de Flota")
                               
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        flash("Error al cargar los datos del reporte", "danger")
        return redirect(url_for('panel'))
    finally:
        if conn and conn.is_connected():
            conn.close()

@reportes_bp.route('/reporte/operadores')
def generar_reporte_operadores():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    conn = None
    try:
        conn = obtener_conexion()
        cursor = get_cursor(conn)
        
        # 1. Consultar el membrete dinámico
        cursor.execute("SELECT institucion, departamento, rif FROM config_reporte LIMIT 1")
        config_encabezado = cursor.fetchone()
        
        # 2. Consultar datos de operadores
        query = """
            SELECT 
                op.cedula,
                op.nombres,
                op.apellidos,
                op.telefono,
                op.edad,
                op.estado,
                ol.tipo_licencia
            FROM operador op
            LEFT JOIN operador_licencia ol ON op.id_operador = ol.id_operador
            ORDER BY op.nombres ASC, op.apellidos ASC
        """
        cursor.execute(query)
        datos = cursor.fetchall()
        
        return render_template('reporte_operadores.html', 
                               datos=datos, 
                               encabezado=config_encabezado, 
                               titulo="Reporte General de Operadores")
                               
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        flash("Error al cargar los datos del reporte de operadores", "danger")
        return redirect(url_for('panel'))
    finally:
        if conn and conn.is_connected():
            conn.close()

@reportes_bp.route('/reporte/graficos')
def generar_reporte_graficos():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    conn = None
    try:
        conn = obtener_conexion()
        cursor = get_cursor(conn)
        
        # 1. Consultar el membrete dinámico
        cursor.execute("SELECT institucion, departamento, rif FROM config_reporte LIMIT 1")
        config_encabezado = cursor.fetchone()
        
        # 2. Estadísticas por Estado
        cursor.execute("SELECT estado, COUNT(*) as cantidad FROM maquinaria GROUP BY estado")
        stats_estado = cursor.fetchall()
        
        # 3. Estadísticas por Tipo (Categoría Maestra: Liviana, Pesada, Maquinaria)
        query_tipo = """
            SELECT COALESCE(tm.categoria, 'SIN CATEGORÍA') as tipo, COUNT(m.id_maquinaria) as cantidad 
            FROM maquinaria m
            LEFT JOIN modelo mo ON m.id_modelo = mo.id_modelo
            LEFT JOIN sub_tipo st ON mo.id_subtipo = st.id_subtipo
            LEFT JOIN tipomaquinaria tm ON st.id_tipo_maquinaria = tm.id_tipo_maquinaria
            GROUP BY tm.categoria
        """
        cursor.execute(query_tipo)
        stats_tipo = cursor.fetchall()

        # 4. Estadísticas por Subtipo (Específicos: Silverado, Retroexcavadora, etc.)
        query_subtipo = """
            SELECT COALESCE(st.nombre_subtipo, 'OTRO') as subtipo, COUNT(m.id_maquinaria) as cantidad 
            FROM maquinaria m
            LEFT JOIN modelo mo ON m.id_modelo = mo.id_modelo
            LEFT JOIN sub_tipo st ON mo.id_subtipo = st.id_subtipo
            GROUP BY st.nombre_subtipo
            ORDER BY cantidad DESC
        """
        cursor.execute(query_subtipo)
        stats_subtipo = cursor.fetchall()
        
        return render_template('reporte_graficos.html', 
                               stats_estado=stats_estado,
                               stats_tipo=stats_tipo,
                               stats_subtipo=stats_subtipo,
                               encabezado=config_encabezado, 
                               titulo="Análisis Estadístico de Flota")
                               
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        flash("Error al cargar las estadísticas", "danger")
        return redirect(url_for('reportes.generar_reporte'))
    finally:
        if conn and conn.is_connected():
            conn.close()

# --- RUTA PARA REGISTRAR LA ACCIÓN DE IMPRESIÓN ---
@reportes_bp.route('/log_impresion', methods=['POST'])
def log_impresion():
    if 'usuario' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 403
    
    try:
        # Importación dinámica para evitar importación circular con app.py
        from app import registrar_log
        
        data = request.get_json() or {}
        tipo_reporte = data.get('tipo', 'Flota')
        
        id_usuario_actual = session.get('id_usuario')
        usuario_nombre = session.get('usuario')
        
        # Registramos el evento en la tabla de historial_sistema
        registrar_log(
            id_usuario_actual, 
            'IMPRIMIR', 
            'REPORTES', 
            f"El usuario {usuario_nombre} generó/imprimió el Reporte General de {tipo_reporte}"
        )
        
        return jsonify({"status": "success", "message": "Impresión registrada en historial"})
    except Exception as e:
        print(f"Error al registrar log de impresión: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500