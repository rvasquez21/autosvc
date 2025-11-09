# Scripts de Limpieza de Datos - AutoSvc

Este conjunto de scripts te permite limpiar los datos de las tablas para volver a cargar información desde archivos Excel.

## Scripts Disponibles

### 1. `cleanup.py` - Script Principal (Recomendado)
Script interactivo con menú que permite elegir entre diferentes opciones:

```bash
python cleanup.py
```

**Opciones disponibles:**
- 📊 Ver datos actuales
- 🧹 Limpiar datos operativos (mantiene configuración)
- 🗑️ Limpiar todo (mantiene solo usuarios)
- 💾 Backup + Limpiar datos operativos
- ❌ Salir

### 2. `clean_data.py` - Limpieza Rápida
Limpia solo los datos operativos manteniendo la configuración:

```bash
python clean_data.py
```

### 3. `clean_tables.py` - Limpieza Completa
Limpia todas las tablas excepto usuarios y configuración de estados:

```bash
python clean_tables.py
```

### 4. `backup_and_clean.py` - Con Backup
Crea un backup automático antes de limpiar:

```bash
python backup_and_clean.py
```

## ¿Qué se Elimina?

### Datos Operativos (Opciones 2 y 4):
- ✅ Órdenes (`orders`)
- ✅ Horas de técnicos (`technician_hours`)
- ✅ Técnicos (`technicians`)
- ✅ Asesores (`advisors`)
- ✅ Historial de estados (`status_history`)
- ✅ Comentarios de órdenes (`order_comments`)

### Limpieza Completa (Opción 3):
- ✅ Todo lo anterior
- ⚠️ **CUIDADO**: Elimina también técnicos y asesores

## ¿Qué se Preserva?

- ✅ Usuarios del sistema (`users`)
- ✅ Configuración de estados (`status`)
- ✅ Configuración general de la aplicación

## Uso Recomendado

1. **Para limpieza normal**: Usa `cleanup.py` y selecciona opción 2
2. **Para limpieza con seguridad**: Usa `cleanup.py` y selecciona opción 4 (crea backup)
3. **Para ver datos actuales**: Usa `cleanup.py` y selecciona opción 1

## Después de Limpiar

Una vez limpiadas las tablas, puedes:

1. Cargar técnicos desde Excel (función "Cargar Excel" en técnicos)
2. Cargar asesores desde Excel (función "Cargar Excel" en asesores)
3. Cargar órdenes desde Excel (función "Cargar Excel" en órdenes)
4. Registrar horas de técnicos manualmente o desde Excel

## Backups

Los backups se guardan en la carpeta `backups/` con formato:
`autosvc_backup_YYYYMMDD_HHMMSS.db`

## ⚠️ Advertencias

- **SIEMPRE** confirma que quieres proceder escribiendo 'SI'
- Los datos eliminados **NO se pueden recuperar** sin backup
- Recomendado hacer backup antes de limpiar datos importantes
- Los usuarios del sistema siempre se preservan

## Solución de Problemas

Si encuentras errores:
1. Verifica que la aplicación no esté ejecutándose
2. Asegúrate de tener permisos de escritura en la base de datos
3. Revisa que el archivo `instance/autosvc.db` exista
4. Usa el backup si algo sale mal
