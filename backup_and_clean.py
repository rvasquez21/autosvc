#!/usr/bin/env python3
"""
Script para hacer backup y limpiar tablas de AutoSvc
"""

import sys
import os
import shutil
from datetime import datetime

# Agregar el directorio actual al path para importar app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from app import Order, TechnicianHours, Technician, Advisor, StatusHistory, OrderComment

def backup_database():
    """Crea un backup de la base de datos antes de limpiar"""
    
    db_path = "instance/autosvc.db"
    if not os.path.exists(db_path):
        print("❌ No se encontró la base de datos.")
        return False
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backups/autosvc_backup_{timestamp}.db"
    
    # Crear directorio de backups si no existe
    os.makedirs("backups", exist_ok=True)
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup creado: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Error creando backup: {str(e)}")
        return False

def clean_with_backup():
    """Limpia las tablas después de crear un backup"""
    
    print("🔧 Script de Limpieza con Backup - AutoSvc")
    print("=" * 50)
    
    # Crear backup
    print("📦 Creando backup de la base de datos...")
    backup_path = backup_database()
    
    if not backup_path:
        confirm = input("⚠️  ¿Continuar sin backup? (escribe 'SI'): ")
        if confirm != 'SI':
            print("❌ Operación cancelada.")
            return
    
    # Mostrar datos actuales
    with app.app_context():
        orders_count = Order.query.count()
        hours_count = TechnicianHours.query.count()
        technicians_count = Technician.query.count()
        advisors_count = Advisor.query.count()
        
        print(f"\n📊 Datos actuales:")
        print(f"   • Órdenes: {orders_count}")
        print(f"   • Horas de técnicos: {hours_count}")
        print(f"   • Técnicos: {technicians_count}")
        print(f"   • Asesores: {advisors_count}")
        print()
        
        if orders_count == 0 and hours_count == 0:
            print("ℹ️  No hay datos para limpiar.")
            return
        
        # Confirmar limpieza
        confirm = input("⚠️  ¿Proceder con la limpieza? (escribe 'SI'): ")
        if confirm != 'SI':
            print("❌ Operación cancelada.")
            return
        
        # Limpiar datos
        try:
            print("\n🗑️  Limpiando datos...")
            
            OrderComment.query.delete()
            StatusHistory.query.delete()
            TechnicianHours.query.delete()
            Order.query.delete()
            Technician.query.delete()
            Advisor.query.delete()
            
            db.session.commit()
            
            print("✅ Limpieza completada!")
            print(f"💾 Backup disponible en: {backup_path}")
            print("\n🔄 Ahora puedes cargar nuevos datos desde archivos Excel.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error durante la limpieza: {str(e)}")

if __name__ == "__main__":
    clean_with_backup()
