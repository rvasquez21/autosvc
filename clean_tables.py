#!/usr/bin/env python3
"""
Script para limpiar las tablas de datos del sistema autosvc
Mantiene solo los usuarios y la configuración de estados
"""

import sys
import os
from datetime import datetime

# Agregar el directorio actual al path para importar app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from app import Order, TechnicianHours, Technician, Advisor, StatusHistory, OrderComment, Status

def clean_tables():
    """Limpia todas las tablas de datos, manteniendo solo usuarios y configuración"""
    
    with app.app_context():
        print("🧹 Iniciando limpieza de tablas...")
        print(f"📅 Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)
        
        # Contar registros antes de eliminar
        orders_count = Order.query.count()
        hours_count = TechnicianHours.query.count()
        technicians_count = Technician.query.count()
        advisors_count = Advisor.query.count()
        status_history_count = StatusHistory.query.count()
        comments_count = OrderComment.query.count()
        
        print(f"📊 Registros encontrados:")
        print(f"   • Órdenes: {orders_count}")
        print(f"   • Horas de técnicos: {hours_count}")
        print(f"   • Técnicos: {technicians_count}")
        print(f"   • Asesores: {advisors_count}")
        print(f"   • Historial de estados: {status_history_count}")
        print(f"   • Comentarios: {comments_count}")
        print()
        
        # Confirmar antes de proceder
        confirm = input("⚠️  ¿Estás seguro de que quieres eliminar TODOS estos datos? (escribe 'SI' para confirmar): ")
        if confirm != 'SI':
            print("❌ Operación cancelada.")
            return
        
        print("\n🗑️  Eliminando datos...")
        
        try:
            # Eliminar en orden para respetar las foreign keys
            print("   • Eliminando comentarios de órdenes...")
            OrderComment.query.delete()
            
            print("   • Eliminando historial de estados...")
            StatusHistory.query.delete()
            
            print("   • Eliminando horas de técnicos...")
            TechnicianHours.query.delete()
            
            print("   • Eliminando órdenes...")
            Order.query.delete()
            
            print("   • Eliminando técnicos...")
            Technician.query.delete()
            
            print("   • Eliminando asesores...")
            Advisor.query.delete()
            
            # Confirmar cambios
            db.session.commit()
            
            print("\n✅ Limpieza completada exitosamente!")
            print("📋 Tablas limpiadas:")
            print("   • orders")
            print("   • technician_hours") 
            print("   • technicians")
            print("   • advisors")
            print("   • status_history")
            print("   • order_comments")
            print("\n💾 Tablas preservadas:")
            print("   • users (usuarios del sistema)")
            print("   • status (configuración de estados)")
            
            print("\n🔄 Ahora puedes cargar nuevos datos desde archivos Excel.")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error durante la limpieza: {str(e)}")
            print("🔄 Se ha realizado rollback de los cambios.")
            return False
            
    return True

def show_current_data():
    """Muestra un resumen de los datos actuales"""
    with app.app_context():
        print("📊 Resumen de datos actuales:")
        print("-" * 40)
        
        orders_count = Order.query.count()
        hours_count = TechnicianHours.query.count()
        technicians_count = Technician.query.count()
        advisors_count = Advisor.query.count()
        users_count = db.session.query(db.text("SELECT COUNT(*) FROM users")).scalar()
        
        print(f"   • Órdenes: {orders_count}")
        print(f"   • Horas de técnicos: {hours_count}")
        print(f"   • Técnicos: {technicians_count}")
        print(f"   • Asesores: {advisors_count}")
        print(f"   • Usuarios: {users_count}")
        print()

if __name__ == "__main__":
    print("🔧 Script de Limpieza de Tablas - AutoSvc")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--show":
        show_current_data()
    else:
        show_current_data()
        clean_tables()
