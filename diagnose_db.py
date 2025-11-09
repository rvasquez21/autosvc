#!/usr/bin/env python3
"""
Script de diagnóstico para verificar la conexión y estado de la base de datos
"""
import os
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError

# Cargar configuración
from dotenv import load_dotenv
load_dotenv()

def diagnose_database():
    """Diagnosticar problemas con la base de datos"""
    print("=" * 60)
    print("DIAGNÓSTICO DE BASE DE DATOS")
    print("=" * 60)
    
    # Obtener DATABASE_URL
    database_url = os.environ.get("DATABASE_URL", "sqlite:///autosvc.db")
    
    # Convertir postgres:// a postgresql:// si es necesario
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    print(f"\n1. DATABASE_URL configurado: {'Sí' if database_url else 'No'}")
    if database_url:
        # Ocultar credenciales en el output
        safe_url = database_url
        if '@' in safe_url:
            parts = safe_url.split('@')
            if len(parts) == 2:
                safe_url = f"***@{parts[1]}"
        print(f"   URL: {safe_url}")
    
    # Intentar conectar
    print("\n2. Intentando conectar a la base de datos...")
    try:
        engine = create_engine(database_url, echo=False)
        with engine.connect() as conn:
            print("   ✅ Conexión exitosa")
            
            # Verificar tablas
            print("\n3. Verificando tablas...")
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            required_tables = [
                'users', 'orders', 'status', 'advisors', 
                'technicians', 'order_comments', 'notifications', 
                'advisor_contacts', 'status_history'
            ]
            
            print(f"   Tablas encontradas: {len(tables)}")
            print(f"   Tablas requeridas: {len(required_tables)}")
            
            missing_tables = []
            for table in required_tables:
                if table in tables:
                    print(f"   ✅ {table}")
                else:
                    print(f"   ❌ {table} - FALTA")
                    missing_tables.append(table)
            
            if missing_tables:
                print(f"\n⚠️  ADVERTENCIA: Faltan {len(missing_tables)} tablas:")
                for table in missing_tables:
                    print(f"   - {table}")
                print("\n💡 SOLUCIÓN: Ejecuta las migraciones:")
                print("   flask db upgrade")
                return False
            else:
                print("\n✅ Todas las tablas requeridas existen")
            
            # Verificar estructura de tabla orders
            print("\n4. Verificando estructura de tabla 'orders'...")
            if 'orders' in tables:
                columns = [col['name'] for col in inspector.get_columns('orders')]
                required_columns = ['id', 'order_number', 'plate', 'modelo', 'brand', 'status']
                missing_columns = [col for col in required_columns if col not in columns]
                
                if missing_columns:
                    print(f"   ❌ Faltan columnas: {', '.join(missing_columns)}")
                    print("   💡 Ejecuta: flask db upgrade")
                    return False
                else:
                    print("   ✅ Todas las columnas requeridas existen")
            
            # Verificar que hay datos
            print("\n5. Verificando datos...")
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                print(f"   Usuarios: {user_count}")
                
                if 'orders' in tables:
                    result = conn.execute(text("SELECT COUNT(*) FROM orders"))
                    order_count = result.scalar()
                    print(f"   Órdenes: {order_count}")
            except Exception as e:
                print(f"   ⚠️  Error verificando datos: {e}")
            
            print("\n" + "=" * 60)
            print("✅ DIAGNÓSTICO COMPLETADO - Base de datos OK")
            print("=" * 60)
            return True
            
    except OperationalError as e:
        print(f"   ❌ Error de conexión: {e}")
        print("\n💡 POSIBLES SOLUCIONES:")
        print("   1. Verifica que DATABASE_URL esté correctamente configurado")
        print("   2. Verifica que el servidor de base de datos esté corriendo")
        print("   3. Verifica credenciales y permisos")
        return False
    except ProgrammingError as e:
        print(f"   ❌ Error de SQL: {e}")
        print("\n💡 POSIBLES SOLUCIONES:")
        print("   1. Verifica que la base de datos exista")
        print("   2. Ejecuta: flask db upgrade")
        return False
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = diagnose_database()
    sys.exit(0 if success else 1)

