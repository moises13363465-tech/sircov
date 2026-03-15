import mysql.connector

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '', 
    'database': 'sircov_'
}

def asegurar_integridad():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(buffered=True, dictionary=True)
    
    # 1. Asegurar que haya un Tipo "GENÉRICO" por si acaso
    cursor.execute("SELECT id_tipo_maquinaria FROM tipomaquinaria WHERE nombre_tipo = 'GENERAL / OTROS'")
    res = cursor.fetchone()
    if res:
        id_tipo_gen = res['id_tipo_maquinaria']
    else:
        c = conn.cursor()
        c.execute("INSERT INTO tipomaquinaria (nombre_tipo, categoria) VALUES ('GENERAL / OTROS', 'maquinaria')")
        conn.commit()
        id_tipo_gen = c.lastrowid
        c.close()
        
    # 2. Asegurar que haya un Subtipo "GENÉRICO" asignado a ese Tipo
    cursor.execute("SELECT id_subtipo FROM sub_tipo WHERE nombre_subtipo = 'EQUIPO MULTIPROPÓSITO'")
    res = cursor.fetchone()
    if res:
        id_subtipo_gen = res['id_subtipo']
    else:
        c = conn.cursor()
        c.execute("INSERT INTO sub_tipo (nombre_subtipo, id_tipo_maquinaria) VALUES ('EQUIPO MULTIPROPÓSITO', %s)", (id_tipo_gen,))
        conn.commit()
        id_subtipo_gen = c.lastrowid
        c.close()
        
    # 3. ASEGURAR QUE CADA TIPO TENGA AL MENOS UN SUBTIPO
    cursor.execute("SELECT id_tipo_maquinaria, nombre_tipo FROM tipomaquinaria")
    tipos = cursor.fetchall()
    tipos_arreglados = 0
    for tipo in tipos:
        cursor.execute("SELECT count(*) as c FROM sub_tipo WHERE id_tipo_maquinaria = %s", (tipo['id_tipo_maquinaria'],))
        if cursor.fetchone()['c'] == 0:
            c = conn.cursor()
            c.execute("INSERT INTO sub_tipo (nombre_subtipo, id_tipo_maquinaria) VALUES ('SUBTIPO GENERAL', %s)", (tipo['id_tipo_maquinaria'],))
            conn.commit()
            c.close()
            tipos_arreglados += 1
            print(f"Tipo '{tipo['nombre_tipo']}' no tenía subtipos. Se le añadió uno general.")
            
    # 4. ASEGURAR QUE CADA MARCA TENGA AL MENOS UN MODELO
    cursor.execute("SELECT id_marca, nombre FROM marca")
    marcas = cursor.fetchall()
    marcas_arregladas = 0
    for marca in marcas:
        cursor.execute("SELECT count(*) as c FROM modelo WHERE id_marca = %s", (marca['id_marca'],))
        if cursor.fetchone()['c'] == 0:
            c = conn.cursor()
            c.execute("INSERT INTO modelo (nombre_modelo, id_marca, id_subtipo) VALUES ('MODELO ESTÁNDAR', %s, %s)", (marca['id_marca'], id_subtipo_gen))
            conn.commit()
            c.close()
            marcas_arregladas += 1
            print(f"Marca '{marca['nombre']}' no tenía modelos. Se le añadió 'MODELO ESTÁNDAR'.")
            
    # 5. ASEGURAR QUE NINGÚN MODELO TENGA UN SUBTIPO HUÉRFANO O NULO
    cursor.execute("""
        SELECT m.id_modelo 
        FROM modelo m 
        LEFT JOIN sub_tipo st ON m.id_subtipo = st.id_subtipo
        WHERE st.id_subtipo IS NULL OR m.id_subtipo IS NULL OR m.id_subtipo = 0
    """)
    modelos_huerfanos = cursor.fetchall()
    modelos_arreglados = 0
    for modelo in modelos_huerfanos:
        cursor.execute("UPDATE modelo SET id_subtipo = %s WHERE id_modelo = %s", (id_subtipo_gen, modelo['id_modelo']))
        modelos_arreglados += 1
        
    conn.commit()
    
    print("\n--- RESUMEN DE INTEGRACIÓN DE CASCADAS ---")
    print(f"Tipos sin subtipos arreglados: {tipos_arreglados}")
    print(f"Marcas sin modelos arregladas: {marcas_arregladas}")
    print(f"Modelos con subtipo invisible/inexistente arreglados: {modelos_arreglados}")
    print("Misión completada. Cascada 100% blindada.")

    cursor.close()
    conn.close()

if __name__ == '__main__':
    asegurar_integridad()
