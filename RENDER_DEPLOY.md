# Guía de Despliegue en Render

## 🔍 Diagnóstico de Errores 500

Si ves un error 500 después del despliegue, sigue estos pasos:

### 1. Verificar Logs en Render
1. Ve a tu servicio en Render
2. Haz clic en "Logs" en el menú lateral
3. Busca mensajes de error que indiquen:
   - `no such table` → Las migraciones no se aplicaron
   - `connection refused` → Problema con DATABASE_URL
   - `column does not exist` → Migraciones desactualizadas

### 2. Ejecutar Diagnóstico Localmente
Si tienes acceso a la base de datos, ejecuta:
```bash
python diagnose_db.py
```

Este script verificará:
- ✅ Conexión a la base de datos
- ✅ Existencia de tablas requeridas
- ✅ Estructura de columnas
- ✅ Datos básicos

### 3. Problemas Comunes y Soluciones

#### Error: "no such table: orders"
**Causa:** Las migraciones no se aplicaron
**Solución:**
```bash
# En Render, ve a "Shell" y ejecuta:
flask db upgrade
```

#### Error: "connection refused" o "could not connect"
**Causa:** DATABASE_URL incorrecto o base de datos no disponible
**Solución:**
1. Verifica que DATABASE_URL esté configurado en Render (Environment)
2. Verifica que el servicio de PostgreSQL esté corriendo
3. Verifica que las credenciales sean correctas

#### Error: "column does not exist: orders.modelo"
**Causa:** Migraciones desactualizadas
**Solución:**
```bash
# En Render Shell:
flask db upgrade
```

### 4. Forzar Re-ejecución de Migraciones
Si las migraciones fallaron durante el build:
1. Ve a "Environment" en Render
2. Agrega variable: `FORCE_MIGRATE=true`
3. Guarda y espera el redeploy
4. O ejecuta manualmente en Shell:
```bash
flask db upgrade --sql  # Ver SQL sin ejecutar
flask db upgrade        # Ejecutar migraciones
```

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

