from flask import Flask, render_template
import mysql.connector

app = Flask(__name__, template_folder='templates')

db_config = {'host': 'localhost', 'user': 'root', 'password': '', 'database': 'sircov_'}

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def test_render():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id_tipo_maquinaria, nombre_tipo, categoria FROM tipomaquinaria ORDER BY categoria, nombre_tipo")
        tipos_maestros = cursor.fetchall()
        
        cursor.execute("""
            SELECT st.id_subtipo, st.nombre_subtipo, tm.nombre_tipo, tm.categoria
            FROM sub_tipo st
            JOIN tipomaquinaria tm ON st.id_tipo_maquinaria = tm.id_tipo_maquinaria
            ORDER BY tm.categoria, tm.nombre_tipo, st.nombre_subtipo
        """)
        subtipos_disponibles = cursor.fetchall()

        return render_template('configuracion.html', 
                               usuario={}, 
                               catalogo=[], 
                               tipos_maestros=tipos_maestros,
                               subtipos_disponibles=subtipos_disponibles,
                               reporte={},
                               historial=[],
                               session={'usuario': 'test'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return str(e)
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    with app.test_request_context('/'):
        print("Rendering...")
        print(test_render())
