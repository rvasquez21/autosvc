# Guía de Despliegue en Render

## Configuración Requerida en Render

### 1. Variables de Entorno

Configura las siguientes variables de entorno en el dashboard de Render:

- **DATABASE_URL**: Render la proporciona automáticamente si creas una base de datos PostgreSQL
- **SECRET_KEY**: Genera una clave secreta segura (ej: `openssl rand -hex 32`)
- **FLASK_APP**: `app.py`
- **FLASK_ENV**: `production` (opcional)

### 2. Base de Datos PostgreSQL

1. En Render, crea un servicio de **PostgreSQL**
2. Render proporcionará automáticamente la variable `DATABASE_URL`
3. La aplicación convertirá automáticamente `postgres://` a `postgresql://` si es necesario

### 3. Migraciones de Base de Datos

Las migraciones se ejecutan automáticamente durante el build con:
```bash
flask db upgrade
```

Si necesitas ejecutarlas manualmente:
```bash
flask db upgrade
```

### 4. Solución de Problemas

#### Error: Internal Server Error

1. **Verifica los logs de Render** para ver el error específico
2. **Verifica que las migraciones se ejecutaron**: Revisa los logs del build
3. **Verifica la conexión a la base de datos**: Asegúrate de que `DATABASE_URL` esté configurada
4. **Verifica que `SECRET_KEY` esté configurada**: Es necesaria para Flask-WTF

#### Error: "no such table"

Ejecuta las migraciones manualmente:
```bash
flask db upgrade
```

#### Error: "connection refused"

Verifica que:
- La base de datos PostgreSQL esté creada en Render
- La variable `DATABASE_URL` esté configurada correctamente
- La base de datos esté en la misma región que tu aplicación

### 5. Comandos Útiles

**Ver logs en tiempo real:**
```bash
# En el dashboard de Render, ve a "Logs"
```

**Reiniciar la aplicación:**
```bash
# En el dashboard de Render, haz clic en "Manual Deploy" > "Clear build cache & deploy"
```

### 6. Estructura de Archivos

Asegúrate de que estos archivos estén en la raíz del proyecto:
- `Procfile` - Comando de inicio
- `requirements.txt` - Dependencias
- `app.py` - Aplicación principal
- `config.py` - Configuración
- `migrations/` - Directorio de migraciones

