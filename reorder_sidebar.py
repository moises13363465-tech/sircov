import os
import re
import glob

# Ruta a la carpeta de plantillas
templates_dir = r"c:\xampp\htdocs\sircov\templates"

# Patrón regex para encontrar el bloque <nav class="sidebar-nav">...<ul>...</ul> y opcionalmente el </nav> 
# Intentaremos capturar el contenido interno del <ul>
pattern = re.compile(
    r'(<nav class="sidebar-nav">.*?<ul>)(.*?)(</ul>)',
    re.DOTALL | re.IGNORECASE
)

# Nuevo orden solicitado:
# 1. Inicio
# 2. Gestión de Usuario
# 3. Flota vehicular
# 4. Operadores
# 5. Reporte
# 6. Configuración (con su if admin)
# 7. Ayuda
# 8. Acerca de

def reorder_menu_items(html_content):
    # Buscar el bloque <nav> en el contenido
    match = pattern.search(html_content)
    if not match:
        return html_content, False
    
    prefix = match.group(1)
    menu_items_str = match.group(2)
    suffix = match.group(3)
    
    # Extraer los elementos individuales <li> y el bloque {% if admin %}...{% endif %}
    # Usaremos una extracción manual rudimentaria pero efectiva buscando '<li>'
    
    # Lista de diccionarios para almacenar los items encontrados
    items = {
        'inicio': '',
        'usuarios': '',
        'flota': '',
        'operadores': '',
        'reporte': '',
        'configuracion': '',  # esto incluirá el bloque {% if ... %}
        'ayuda': '',
        'acerca': ''
    }
    
    # Extraer configuración con todo y su bloque IF
    config_pattern = re.compile(r'{%\s*if\s+session\.rol\s*==\s*\'admin\'\s*%}.*?<li><a href="\{\{\s*url_for\(\'configuracion\'\)\s*\}\}".*?>.*?Configuración</a></li>\s*{%\s*endif\s*%}', re.DOTALL | re.IGNORECASE)
    
    config_match = config_pattern.search(menu_items_str)
    if config_match:
        items['configuracion'] = config_match.group(0)
        # remover del string original para no duplicar buscando <li>
        menu_items_str = menu_items_str.replace(config_match.group(0), '')
    else:
        # Intento alternativo por si el formato del if varía ligeramente
         config_pattern2 = re.compile(r'{%\s*if[^%]+%}\s*<li[^>]*>.*?Configuración.*?</li[^>]*>\s*{%\s*endif\s*%}', re.DOTALL | re.IGNORECASE)
         config_match2 = config_pattern2.search(menu_items_str)
         if config_match2:
             items['configuracion'] = config_match2.group(0)
             menu_items_str = menu_items_str.replace(config_match2.group(0), '')
    
    # Extraer los <li> restantes
    li_pattern = re.compile(r'<li[^>]*>.*?</li>', re.DOTALL | re.IGNORECASE)
    lis = li_pattern.findall(menu_items_str)
    
    for li in lis:
        li_lower = li.lower()
        if 'panel' in li_lower or 'inicio' in li_lower:
            items['inicio'] = li
        elif 'gestion_usuarios' in li_lower or 'gestión de usuario' in li_lower:
            items['usuarios'] = li
        elif 'gestion_flota' in li_lower or 'flota vehicular' in li_lower:
            items['flota'] = li
        elif 'operadores.index' in li_lower or 'operadores' in li_lower:
            items['operadores'] = li
        elif 'reportes.generar_reporte' in li_lower or 'reporte' in li_lower:
            items['reporte'] = li
        elif 'ayuda.index' in li_lower or 'ayuda' in li_lower:
            items['ayuda'] = li
        elif 'acerca_de.index' in li_lower or 'acerca de' in li_lower:
            items['acerca'] = li
            
    # Reconstruir en el nuevo orden
    new_menu = "\n"
    
    order = ['inicio', 'usuarios', 'flota', 'operadores', 'reporte', 'configuracion', 'ayuda', 'acerca']
    
    for key in order:
        if items[key]:
            # Mantener identación
            if key == 'configuracion':
                new_menu += f"                    {items[key].strip()}\n"
            else:
                new_menu += f"                    {items[key].strip()}\n"
                
    new_menu += "                "
    
    # Reemplazar en el html content
    new_html = html_content[:match.start()] + prefix + new_menu + suffix + html_content[match.end():]
    
    return new_html, True

# Procesar archivos
files = glob.glob(os.path.join(templates_dir, "*.html"))
modified_count = 0

for file_path in files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    new_content, modified = reorder_menu_items(content)
    
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        modified_count += 1
        print(f"Modificado: {os.path.basename(file_path)}")

print(f"Total archivos modificados: {modified_count}")
