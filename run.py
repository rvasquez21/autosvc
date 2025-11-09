"""
Script para ejecutar la aplicación Flask con Waitress
Uso: py run.py
"""
from waitress import serve
from app import app

if __name__ == '__main__':
    # Configuración del servidor
    host = '127.0.0.1'  # localhost
    port = 5000
    
    print(f"🚀 Iniciando servidor en http://{host}:{port}")
    print("📝 Presiona Ctrl+C para detener el servidor")
    
    # Iniciar servidor Waitress
    serve(app, host=host, port=port, threads=4)

