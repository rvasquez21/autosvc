"""
Script para ejecutar la aplicación Flask con Waitress
Uso: py run.py
"""
import os
from waitress import serve
from app import app

if __name__ == '__main__':
    # Obtener configuración del entorno o usar valores por defecto
    host = os.environ.get('HOST', '127.0.0.1')  # localhost por defecto
    port = int(os.environ.get('PORT', 5000))  # Puerto 5000 por defecto
    
    print(f"🚀 Iniciando servidor en http://{host}:{port}")
    print("📝 Presiona Ctrl+C para detener el servidor")
    
    # Iniciar servidor Waitress
    # En producción, usar 0.0.0.0 para aceptar conexiones externas
    if os.environ.get('ENV') == 'production' or os.environ.get('PORT'):
        serve(app, host='0.0.0.0', port=port, threads=4)
    else:
        serve(app, host=host, port=port, threads=4)

