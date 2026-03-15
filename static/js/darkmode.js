/**
 * Script Global para Modo Oscuro en SIRCOV
 * Requiere un atributo data-theme='dark' en :root (html) 
 */

// Inicialización temprana: Se ejecuta ni bien el script carga para evitar destellos blancos.
(function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
})();

// Función auxiliar que puede ser llamada desde el Toggle en Configuración
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    if (newTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
    } else {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
    }

    // Si hay un checkbox en la vista actual, sincronizarlo.
    const themeCheckbox = document.getElementById('dark-mode-toggle');
    if (themeCheckbox) {
        themeCheckbox.checked = newTheme === 'dark';
    }
}

// Al terminar de cargar el DOM (en Configuración), sincronizar el estado visual del Switch.
window.addEventListener('DOMContentLoaded', () => {
    const themeCheckbox = document.getElementById('dark-mode-toggle');
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';

    if (themeCheckbox) {
        themeCheckbox.checked = currentTheme === 'dark';
        themeCheckbox.addEventListener('change', () => {
            toggleTheme();
        });
    }

    // Colorear dinámicamente todos los elementos select dependiendo de su valor textual (para estados operativos)
    const applySelectStatusColors = () => {
        document.querySelectorAll('select').forEach(select => {
            const updateColor = () => {
                // Limpiar clases previas
                select.classList.remove('bg-operativo', 'bg-activo', 'bg-ok', 'bg-inactivo', 'bg-fuera', 'bg-danger', 'bg-mantenimiento', 'bg-warning');

                const text = select.options[select.selectedIndex]?.text.toUpperCase() || "";
                const val = select.value.toUpperCase();

                if (text.includes('ACTIVO') || text.includes('OPERATIVO') || val === 'ACTIVO' || val === 'OPERATIVO') {
                    select.classList.add('bg-activo');
                } else if (text.includes('INACTIVO') || text.includes('SUSPENDIDO') || text.includes('FUERA') || val === 'INACTIVO') {
                    select.classList.add('bg-inactivo');
                } else if (text.includes('REPOSO') || text.includes('PERMISO') || text.includes('MANTENIMIENTO')) {
                    select.classList.add('bg-mantenimiento');
                }
            };

            // Si el select tiene alguna de esas palabras en sus opciones, escuchamos el cambio
            if (Array.from(select.options).some(opt => opt.text.toUpperCase().match(/(ACTIVO|INACTIVO|OPERATIVO|FUERA|MANTENIMIENTO|REPOSO|PERMISO)/))) {
                select.addEventListener('change', updateColor);
                if (select.value) updateColor();
            }
        });
    };

    applySelectStatusColors();
});
