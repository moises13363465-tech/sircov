#!C:/Users/Asus/AppData/Local/Programs/Python/Python313/python.exe
from flask import Blueprint, render_template, session, redirect, url_for, request, flash

# Definimos el blueprint para la gestión de marcas
marca_bp = Blueprint('marca', __name__)

@marca_bp.route('/registro_marca', methods=['GET', 'POST'])
def registro_marca():
    # 1. Verificar si el usuario está logueado
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    # 2. Si el usuario envía el formulario (botón Guardar)
    if request.method == 'POST':
        # Capturamos los datos del formulario
        nombre = request.form.get('nombre_marca')
        origen = request.form.get('origen_marca')
        categorias = request.form.getlist('cat')  # Para los checkboxes
        modelos = request.form.getlist('modelos[]') # Para la lista dinámica
        
        # --- AQUÍ PROCESARÍAS LA INSERCIÓN EN TU BASE DE DATOS ---
        # Ejemplo: db.ejecutar("INSERT INTO marcas...")
        
        # Depuración en consola
        print(f"Marca recibida: {nombre}, Origen: {origen}, Modelos: {modelos}") 
        
        # Mensaje de éxito para el usuario
        flash(f"¡Excelente! La marca '{nombre}' ha sido registrada correctamente.", "success")
        
        # Redirigir para limpiar el formulario y evitar re-envíos al actualizar
        return redirect(url_for('marca.registro_marca'))

    # 3. Mostrar la interfaz (Asegúrate que el archivo se llame agregar_marca.html)
    return render_template('agregar_marca.html')