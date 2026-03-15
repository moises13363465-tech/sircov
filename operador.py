from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from db_config import get_connection, get_cursor, close_db
from mysql.connector import Error
import os
from werkzeug.utils import secure_filename

operadores_bp = Blueprint('operadores', __name__, url_prefix='/operadores')

# Configuración de subida de archivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'operadores')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Configuración de la base de datos


def get_db_connection():
    return get_connection()

# Función auxiliar para registrar acciones en el historial
def _registrar_log(id_usuario, accion, tabla, detalle):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)
        query = """
            INSERT INTO historial_sistema 
            (id_usuario, accion, tabla_afectada, detalle) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (id_usuario, accion, tabla, detalle))
        conn.commit()
    except Exception as e:
        print(f"Error al registrar log: {e}")
    finally:
        close_db(conn, cursor if 'cursor' in locals() else None)

# ────────────────────────────────────────────────
# LISTADO DE OPERADORES
# ────────────────────────────────────────────────
@operadores_bp.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))  # Ajusta según tu ruta de login

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)

        query = """
            SELECT 
                o.id_operador,
                o.cedula,
                o.nombres,
                o.apellidos,
                o.edad,
                o.estado,
                o.telefono,
                GROUP_CONCAT(m.placa SEPARATOR ', ') AS maquinarias_asignadas
            FROM operador o
            LEFT JOIN operador_maquinaria om ON o.id_operador = om.id_operador
            LEFT JOIN maquinaria m ON om.id_maquinaria = m.id_maquinaria
            GROUP BY o.id_operador
            ORDER BY o.apellidos ASC, o.nombres ASC
        """
        cursor.execute(query)
        operadores = cursor.fetchall()

        return render_template('operador.html', operadores=operadores)

    except Exception as e:
        print(f"Error al listar operadores: {e}")
        flash(f"Error al cargar la lista de operadores: {str(e)}", "error")
        return render_template('operador.html', operadores=[])

    finally:
        close_db(conn, cursor if 'cursor' in locals() else None)

# ────────────────────────────────────────────────
# AGREGAR NUEVO OPERADOR
# ────────────────────────────────────────────────
@operadores_bp.route('/agregar', methods=['GET', 'POST'])
def agregar():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)

        # Cargar datos para los selects del formulario
        cursor.execute("""
            SELECT 
                m.id_maquinaria, m.placa, mo.id_subtipo, m.año_fabricacion, m.estado,
                mo.nombre_modelo, ma.nombre AS nombre_marca, tm.nombre_tipo
            FROM maquinaria m 
            LEFT JOIN modelo mo ON m.id_modelo = mo.id_modelo
            LEFT JOIN marca ma ON mo.id_marca = ma.id_marca
            LEFT JOIN sub_tipo st ON mo.id_subtipo = st.id_subtipo
            LEFT JOIN tipomaquinaria tm ON st.id_tipo_maquinaria = tm.id_tipo_maquinaria
            ORDER BY m.placa
        """)
        maquinas = cursor.fetchall()

        cursor.execute("SELECT id, nombre FROM nivel_instruccion ORDER BY id")
        niveles = cursor.fetchall()

        if request.method == 'POST':
            # Construir teléfono completo
            cod_telf = request.form.get('cod_telf', '')
            num_telf = request.form.get('num_telf', '')
            telefono = f"{cod_telf}{num_telf}".strip() if cod_telf and num_telf else None

            # Teléfono: verificar largo
            if telefono and len(telefono) != 11:
                flash("El teléfono debe tener 11 dígitos en total (4 de código y 7 de número)", "error")
                return render_template('agregar_operador.html', maquinas=maquinas, niveles=niveles)

            # Validación de cédula con prefijo
            tipo_cedula = request.form.get('tipo_cedula', 'V-')
            cedula_num = request.form.get('cedula', '').strip()
            if not cedula_num.isdigit() or not (7 <= len(cedula_num) <= 8):
                flash("El número de cédula debe contener solo números y tener entre 7 y 8 dígitos", "error")
                return render_template('agregar_operador.html', maquinas=maquinas, niveles=niveles)
            cedula_completa = f"{tipo_cedula}{cedula_num}"

            # Manejo de archivos escaneados
            doc_cedula = None
            if 'file_cedula' in request.files:
                file = request.files['file_cedula']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(f"cedula_{cedula_completa}_{file.filename}")
                    save_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(save_path)
                    doc_cedula = f"static/uploads/operadores/{filename}"

            # Insertar operador
            data_operador = (
                cedula_completa,
                request.form.get('nombres', '').strip(),
                request.form.get('apellidos', '').strip(),
                telefono,
                request.form.get('edad'),
                request.form.get('tipo_sangre'),
                request.form.get('condicion_salud'),
                request.form.get('estado', 'OPERATIVO'),
                request.form.get('id_nivel_instruccion'),
                doc_cedula
            )

            cursor.execute("""
                INSERT INTO operador 
                (cedula, nombres, apellidos, telefono, edad, tipo_sangre, condicion_salud, estado, id_nivel_instruccion, doc_cedula)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, data_operador)
            id_operador = cursor.lastrowid

            # Certificado de salud (opcional)
            fecha_exp_salud = request.form.get('fecha_exp_salud')
            fecha_ven_salud = request.form.get('fecha_ven_salud')
            doc_certificado = None
            if 'file_certificado' in request.files:
                file = request.files['file_certificado']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(f"certificado_{cedula_completa}_{file.filename}")
                    save_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(save_path)
                    doc_certificado = f"static/uploads/operadores/{filename}"

            if (fecha_exp_salud and fecha_ven_salud) or doc_certificado:
                cursor.execute("""
                    INSERT INTO operador_certificado 
                    (id_operador, fecha_expedicion, fecha_vencimiento, doc_certificado)
                    VALUES (%s, %s, %s, %s)
                """, (id_operador, fecha_exp_salud, fecha_ven_salud, doc_certificado))

            # Licencia (opcional)
            tipo_licencia = request.form.get('tipo_licencia')
            fecha_exp_lic = request.form.get('fecha_exp_licencia')
            fecha_ven_lic = request.form.get('fecha_ven_licencia')
            doc_licencia = None
            if 'file_licencia' in request.files:
                file = request.files['file_licencia']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(f"licencia_{cedula_completa}_{file.filename}")
                    save_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(save_path)
                    doc_licencia = f"static/uploads/operadores/{filename}"

            if (tipo_licencia and fecha_exp_lic and fecha_ven_lic) or doc_licencia:
                cursor.execute("""
                    INSERT INTO operador_licencia 
                    (id_operador, tipo_licencia, fecha_expedicion, fecha_vencimiento, doc_licencia)
                    VALUES (%s, %s, %s, %s, %s)
                """, (id_operador, tipo_licencia, fecha_exp_lic, fecha_ven_lic, doc_licencia))

            # Asignación de maquinarias (máximo 5)
            id_maquinarias = request.form.getlist('id_maquinarias[]')
            inserted = 0
            for maq_id in id_maquinarias:
                if maq_id and maq_id.strip().isdigit():
                    try:
                        cursor.execute("""
                            INSERT INTO operador_maquinaria 
                            (id_operador, id_maquinaria) 
                            VALUES (%s, %s)
                        """, (id_operador, int(maq_id)))
                        inserted += 1
                        if inserted >= 5:
                            break
                    except Error as e:
                        if e.errno == 1062:  # duplicate entry
                            continue
                        raise

            conn.commit()

            nombre_completo = f"{request.form.get('nombres')} {request.form.get('apellidos')}".strip()
            _registrar_log(
                session.get('id_usuario'),
                'CREAR',
                'OPERADOR',
                f"Registró al operador {nombre_completo}"
            )

            flash("Operador registrado exitosamente", "success")
            return redirect(url_for('operadores.index'))

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"ERROR al guardar operador: {str(e)}")
        flash(f"Error al guardar el operador: {str(e)}", "error")

    finally:
        close_db(conn, cursor if 'cursor' in locals() else None)

    return render_template('agregar_operador.html', maquinas=maquinas, niveles=niveles)

# ────────────────────────────────────────────────
# EDITAR OPERADOR
# ────────────────────────────────────────────────
@operadores_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)

        # Cargar catálogos
        cursor.execute("SELECT id, nombre FROM nivel_instruccion ORDER BY id")
        niveles = cursor.fetchall()

        cursor.execute("""
            SELECT 
                m.id_maquinaria, m.placa, mo.id_subtipo, m.año_fabricacion, m.estado,
                mo.nombre_modelo, ma.nombre AS nombre_marca, tm.nombre_tipo
            FROM maquinaria m 
            LEFT JOIN modelo mo ON m.id_modelo = mo.id_modelo
            LEFT JOIN marca ma ON mo.id_marca = ma.id_marca
            LEFT JOIN sub_tipo st ON mo.id_subtipo = st.id_subtipo
            LEFT JOIN tipomaquinaria tm ON st.id_tipo_maquinaria = tm.id_tipo_maquinaria
            ORDER BY m.placa
        """)
        maquinas = cursor.fetchall()

        # Obtener datos del operador + certificados y licencia
        cursor.execute("""
            SELECT o.*, 
                   oc.fecha_expedicion AS fecha_exp_salud, 
                   oc.fecha_vencimiento AS fecha_ven_salud,
                   oc.doc_certificado,
                   ol.tipo_licencia, 
                   ol.fecha_expedicion AS fecha_exp_licencia, 
                   ol.fecha_vencimiento AS fecha_ven_licencia,
                   ol.doc_licencia
            FROM operador o 
            LEFT JOIN operador_certificado oc ON o.id_operador = oc.id_operador
            LEFT JOIN operador_licencia ol ON o.id_operador = ol.id_operador
            WHERE o.id_operador = %s
        """, (id,))
        operador = cursor.fetchone()

        if not operador:
            flash("Operador no encontrado", "error")
            return redirect(url_for('operadores.index'))

        # Maquinarias ya asignadas
        cursor.execute("""
            SELECT id_maquinaria 
            FROM operador_maquinaria 
            WHERE id_operador = %s
        """, (id,))
        asignadas = [row['id_maquinaria'] for row in cursor.fetchall()]

        # Separar teléfono para precargar
        telefono = operador.get('telefono') or ''
        cod_telf = telefono[:4] if len(telefono) >= 4 else ''
        num_telf = telefono[4:] if len(telefono) > 4 else ''

        # Separar cédula
        cedula_completa = operador.get('cedula') or ''
        if cedula_completa.startswith('V-') or cedula_completa.startswith('E-'):
            tipo_cedula = cedula_completa[:2]
            cedula_num = cedula_completa[2:]
        else:
            tipo_cedula = 'V-'
            cedula_num = cedula_completa

        if request.method == 'POST':
            # Construir teléfono
            cod_telf_post = request.form.get('cod_telf', '')
            num_telf_post = request.form.get('num_telf', '')
            telefono_post = f"{cod_telf_post}{num_telf_post}".strip() if cod_telf_post and num_telf_post else None

            # Teléfono verificar
            if telefono_post and len(telefono_post) != 11:
                flash("El teléfono debe tener 11 dígitos en total (4 de código y 7 de número)", "error")
                return render_template('editar_operador.html', 
                                     operador=operador, 
                                     maquinas=maquinas, 
                                     niveles=niveles, 
                                     asignadas_ids=asignadas,
                                     cod_telf=cod_telf_post,
                                     num_telf=num_telf_post,
                                     tipo_cedula=request.form.get('tipo_cedula', 'V-'),
                                     cedula_num=request.form.get('cedula', '').strip())

            # Validar cédula
            tipo_cedula_post = request.form.get('tipo_cedula', 'V-')
            cedula_num_post = request.form.get('cedula', '').strip()
            if not cedula_num_post.isdigit() or not (7 <= len(cedula_num_post) <= 8):
                flash("El número de cédula debe contener solo números y tener entre 7 y 8 dígitos", "error")
                return render_template('editar_operador.html', 
                                     operador=operador, 
                                     maquinas=maquinas, 
                                     niveles=niveles, 
                                     asignadas_ids=asignadas,
                                     cod_telf=cod_telf_post,
                                     num_telf=num_telf_post,
                                     tipo_cedula=tipo_cedula_post,
                                     cedula_num=cedula_num_post)
            
            cedula_completa_post = f"{tipo_cedula_post}{cedula_num_post}"

            # Actualizar datos del operador
            # Manejo de cédula escaneada
            doc_cedula = operador.get('doc_cedula')
            if 'file_cedula' in request.files:
                file = request.files['file_cedula']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(f"cedula_{cedula_completa_post}_{file.filename}")
                    file.save(os.path.join(UPLOAD_FOLDER, filename))
                    doc_cedula = os.path.join(UPLOAD_FOLDER, filename)

            cursor.execute("""
                UPDATE operador SET 
                    cedula = %s,
                    nombres = %s,
                    apellidos = %s,
                    telefono = %s,
                    edad = %s,
                    tipo_sangre = %s,
                    condicion_salud = %s,
                    estado = %s,
                    id_nivel_instruccion = %s,
                    doc_cedula = %s
                WHERE id_operador = %s
            """, (
                cedula_completa_post,
                request.form.get('nombres', '').strip(),
                request.form.get('apellidos', '').strip(),
                telefono_post,
                request.form.get('edad'),
                request.form.get('tipo_sangre'),
                request.form.get('condicion_salud'),
                request.form.get('estado'),
                request.form.get('id_nivel_instruccion'),
                doc_cedula,
                id
            ))

            # Certificado de salud
            fecha_exp_salud = request.form.get('fecha_exp_salud')
            fecha_ven_salud = request.form.get('fecha_ven_salud')
            
            doc_certificado = operador.get('doc_certificado')
            if 'file_certificado' in request.files:
                file = request.files['file_certificado']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(f"certificado_{cedula_completa_post}_{file.filename}")
                    file.save(os.path.join(UPLOAD_FOLDER, filename))
                    doc_certificado = os.path.join(UPLOAD_FOLDER, filename)

            cursor.execute("DELETE FROM operador_certificado WHERE id_operador = %s", (id,))
            if (fecha_exp_salud and fecha_ven_salud) or doc_certificado:
                cursor.execute("""
                    INSERT INTO operador_certificado 
                    (id_operador, fecha_expedicion, fecha_vencimiento, doc_certificado)
                    VALUES (%s, %s, %s, %s)
                """, (id, fecha_exp_salud, fecha_ven_salud, doc_certificado))

            # Licencia
            tipo_licencia = request.form.get('tipo_licencia')
            fecha_exp_lic = request.form.get('fecha_exp_licencia')
            fecha_ven_lic = request.form.get('fecha_ven_licencia')
            
            doc_licencia = operador.get('doc_licencia')
            if 'file_licencia' in request.files:
                file = request.files['file_licencia']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(f"licencia_{cedula_completa_post}_{file.filename}")
                    file.save(os.path.join(UPLOAD_FOLDER, filename))
                    doc_licencia = os.path.join(UPLOAD_FOLDER, filename)

            cursor.execute("DELETE FROM operador_licencia WHERE id_operador = %s", (id,))
            if (tipo_licencia and fecha_exp_lic and fecha_ven_lic) or doc_licencia:
                cursor.execute("""
                    INSERT INTO operador_licencia 
                    (id_operador, tipo_licencia, fecha_expedicion, fecha_vencimiento, doc_licencia)
                    VALUES (%s, %s, %s, %s, %s)
                """, (id, tipo_licencia, fecha_exp_lic, fecha_ven_lic, doc_licencia))

            # Actualizar asignaciones de maquinaria
            cursor.execute("DELETE FROM operador_maquinaria WHERE id_operador = %s", (id,))
            id_maquinarias = request.form.getlist('id_maquinarias[]')
            inserted = 0
            for maq_id in id_maquinarias:
                if maq_id and maq_id.strip().isdigit():
                    try:
                        cursor.execute("""
                            INSERT INTO operador_maquinaria 
                            (id_operador, id_maquinaria) 
                            VALUES (%s, %s)
                        """, (id, int(maq_id)))
                        inserted += 1
                        if inserted >= 5:
                            break
                    except Error as e:
                        if e.errno == 1062:
                            continue
                        raise

            conn.commit()

            nombre_completo = f"{request.form.get('nombres')} {request.form.get('apellidos')}".strip()
            _registrar_log(
                session.get('id_usuario'),
                'ACTUALIZAR',
                'OPERADOR',
                f"Actualizó operador ID {id} - {nombre_completo}"
            )

            flash("Operador actualizado correctamente", "success")
            return redirect(url_for('operadores.index'))

        # GET: mostrar formulario con datos actuales
        return render_template('editar_operador.html',
                             operador=operador,
                             maquinas=maquinas,
                             niveles=niveles,
                             asignadas_ids=asignadas,
                             cod_telf=cod_telf,
                             num_telf=num_telf,
                             tipo_cedula=tipo_cedula,
                             cedula_num=cedula_num)

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"ERROR en editar operador: {str(e)}")
        flash(f"Error al cargar/editar operador: {str(e)}", "error")
        return redirect(url_for('operadores.index'))

    finally:
        close_db(conn, cursor if 'cursor' in locals() else None)

@operadores_bp.route('/expediente/<int:id>')
def expediente(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)

        # 1. Datos básicos del operador
        cursor.execute("SELECT * FROM operador WHERE id_operador = %s", (id,))
        operador = cursor.fetchone()
        
        if not operador:
            flash("Operador no encontrado", "error")
            return redirect(url_for('operadores.index'))

        # 2. Certificado de salud
        cursor.execute("SELECT * FROM operador_certificado WHERE id_operador = %s", (id,))
        certificado = cursor.fetchone()

        # 3. Licencia
        cursor.execute("SELECT * FROM operador_licencia WHERE id_operador = %s", (id,))
        licencia = cursor.fetchone()

        # 4. Maquinaria asignada
        cursor.execute("""
            SELECT m.placa, ma.nombre AS marca, mo.nombre_modelo AS modelo, st.nombre_subtipo AS tipo
            FROM maquinaria m
            JOIN modelo mo ON m.id_modelo = mo.id_modelo
            JOIN marca ma ON mo.id_marca = ma.id_marca
            JOIN sub_tipo st ON mo.id_subtipo = st.id_subtipo
            JOIN operador_maquinaria om ON m.id_maquinaria = om.id_maquinaria
            WHERE om.id_operador = %s
        """, (id,))
        maquinas = cursor.fetchall()

        # 5. Configuración del sistema (para el encabezado)
        cursor.execute("SELECT * FROM config_reporte LIMIT 1")
        encabezado = cursor.fetchone()

        return render_template('expediente_operador.html', 
                               operador=operador, 
                               certificado=certificado, 
                               licencia=licencia, 
                               maquinas=maquinas,
                               encabezado=encabezado)

    except Exception as e:
        print(f"Error al generar expediente: {e}")
        flash("Error al generar el expediente", "error")
        return redirect(url_for('operadores.index'))
    finally:
        close_db(conn, cursor if 'cursor' in locals() else None)

# ────────────────────────────────────────────────
# ELIMINAR OPERADOR
# ────────────────────────────────────────────────
@operadores_bp.route('/eliminar/<int:id>')
def eliminar(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True, dictionary=True)

        # Obtener nombre para el log
        cursor.execute("SELECT nombres, apellidos FROM operador WHERE id_operador = %s", (id,))
        op = cursor.fetchone()
        nombre = f"{op['nombres']} {op['apellidos']}" if op else "Desconocido"

        cursor.execute("DELETE FROM operador WHERE id_operador = %s", (id,))
        conn.commit()

        _registrar_log(
            session.get('id_usuario'),
            'ELIMINAR',
            'OPERADOR',
            f"Eliminó al operador {nombre} (ID: {id})"
        )

        flash("Operador eliminado correctamente", "success")

    except Exception as e:
        print(f"ERROR al eliminar operador: {str(e)}")
        flash(f"No se pudo eliminar el operador: {str(e)}", "error")

    finally:
        close_db(conn, cursor if 'cursor' in locals() else None)

    return redirect(url_for('operadores.index'))