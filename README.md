# AutoSVC - Seguimiento de Órdenes de Taller

Aplicación Flask sencilla y lista para usar que permite:
- Crear y listar órdenes
- Actualizar estado con un clic (SweetAlert)
- Dashboard con conteo por estatus y alerta de órdenes con 15+ días
- Búsqueda por número de orden, placa, cliente, VIN, asesor o técnico
- Configuración por `.env` para usar MySQL o SQLite

## Instalación rápida

1) Requisitos: Python 3.10+
2) Crear entorno:
```bash
python -m venv .venv && source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
3) Copia `.env.example` a `.env` y ajusta `DATABASE_URL` (MySQL o SQLite)
4) Inicializa DB:
```bash
flask db init
flask db migrate -m "init"
flask db upgrade
python seeds.py  # Datos de ejemplo
```
5) Ejecuta:
```bash
python app.py
# Abre http://localhost:5000
```

## Estados predefinidos
RECEPCION, DIAGNOSTICO, PRESUPUESTO, APROBACION, EN_REPARACION, ESPERA_REPUESTO, LAVADO, CONTROL_CALIDAD, FACTURACION, ENTREGADO

## Deploy rápido (VPS)
- Instala Python 3.10+, `pip`, `venv`
- Configura variables de entorno (`.env`), apunta a MySQL
- Usa `gunicorn --bind 0.0.0.0:5000 app:app` detrás de Nginx
- Activa un servicio systemd para mantenerlo activo

## Próximos pasos sugeridos
- Autenticación (Flask-Login) por roles (asesor, técnico, admin)
- Historial de cambios de estado
- Subida de fotos en la orden
- Socket en vivo para actualizaciones instantáneas
- Exportar a Excel/CSV
