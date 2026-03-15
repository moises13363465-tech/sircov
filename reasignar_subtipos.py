import mysql.connector

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '', 
    'database': 'sircov_'
}

REMAP = {
    "Retroexcavadora": "RETROEXCAVADORA CARGADORA",
    "RETROEXCAVADORA": "RETROEXCAVADORA CARGADORA",
    "RETRO EXCAVADORA CON MARTILLO": "RETROEXCAVADORA CARGADORA",
    "Tractor": "TRACTOR DE ORUGAS (BULLDOZER)",
    "TRACTOR": "TRACTOR DE ORUGAS (BULLDOZER)",
    "MOTONIVELADORA": "MOTONIVELADORA",
    "BOMBA": "BOMBA INDUSTRIAL DE CAUDAL",
    "COMPRESOR": "COMPRESOR DE AIRE PORTÁTIL",
    "TIENDETUBOS": "TIENDETUBOS (SIDE BOOM)",
    "TRAILER CAMA BAJA": "CARRETÓN TIPO LOW BOY",
    "EXCAVADORA HIDRÁULICA": "EXCAVADORA DE ORUGAS",
    "CARGADOR FRONTAL": "CARGADOR FRONTAL SOBRE RUEDAS",
    "GRÚA TELESCÓPICA": "GRÚA TELESCÓPICA SOBRE CAMIÓN",
    "BOMBA INDUSTRIAL": "BOMBA INDUSTRIAL DE CAUDAL",
    "COMPRESOR DE AIRE PORTÁTIL": "COMPRESOR DE AIRE PORTÁTIL"
}

def reasignar():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(buffered=True)
    
    total_updated = 0
    
    for old_name, new_name in REMAP.items():
        # Buscar el ID del nuevo subtipo (creado en la expansión)
        cursor.execute("SELECT id_subtipo FROM sub_tipo WHERE UPPER(nombre_subtipo) = %s", (new_name.upper(),))
        nuevo_res = cursor.fetchone()
        
        if not nuevo_res:
            print(f"ERROR: Nuevo subtipo '{new_name}' no encontrado en BD.")
            continue
            
        nuevo_id = nuevo_res[0]
        
        # Buscar el ID del viejo subtipo
        cursor.execute("SELECT id_subtipo FROM sub_tipo WHERE nombre_subtipo = %s OR UPPER(nombre_subtipo) = %s", (old_name, old_name.upper()))
        viejos = cursor.fetchall()
        
        for viejo_row in viejos:
            viejo_id = viejo_row[0]
            if viejo_id == nuevo_id: continue
            
            # Reasignar todos los modelos que usan el viejo_id al nuevo_id
            cursor.execute("UPDATE modelo SET id_subtipo = %s WHERE id_subtipo = %s", (nuevo_id, viejo_id))
            if cursor.rowcount > 0:
                print(f"Reasignados {cursor.rowcount} modelos de '{old_name}' a '{new_name}'.")
                total_updated += cursor.rowcount
                
            # Eliminar el viejo subtipo si ya no tiene modelos
            try:
                cursor.execute("DELETE FROM sub_tipo WHERE id_subtipo = %s", (viejo_id,))
            except Exception as e:
                pass
                
    conn.commit()
    print(f"Reasignación completada. Total modelos actualizados: {total_updated}")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    reasignar()
