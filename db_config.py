import os

def get_connection():
  
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        # --> ESTAMOS EN RENDER (Producción Web) <--
        import psycopg2
        try:
            # Forzamos sslmode para Render si es necesario
            connection = psycopg2.connect(DATABASE_URL)
            return connection
        except Exception as err:
            print(f"Error de conexión a PostgreSQL (Render): {err}")
            return None
    else:
        # --> ESTAMOS EN LA PC LOCAL (XAMPP) <--
        import mysql.connector
        try:
            connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='',
                database='sircov_',
                charset='utf8mb4'
            )
            return connection
        except mysql.connector.Error as err:
            print(f"Error de conexión a MySQL (Local/XAMPP): {err}")
            return None

def get_cursor(conn, **kwargs):
    """Retorna un cursor que devuelve diccionarios, detectando el tipo de conexión."""
    if hasattr(conn, 'cursor_factory'): # Probablemente psycopg2
        from psycopg2.extras import RealDictCursor
        kwargs.pop('buffered', None) # Postgres no usa buffered
        return conn.cursor(cursor_factory=RealDictCursor, **kwargs)
    else: # Probablemente mysql-connector
        kwargs.setdefault('dictionary', True)
        return conn.cursor(**kwargs)

def close_db(conn, cursor=None):
    """Cierra el cursor y la conexión de forma segura."""
    if cursor:
        try:
            cursor.close()
        except:
            pass
    if conn:
        try:
            # Para MySQL usamos is_connected(), para Postgres simplemente cerramos si existe
            if hasattr(conn, 'is_connected'):
                if conn.is_connected():
                    conn.close()
            else:
                conn.close()
        except:
            pass