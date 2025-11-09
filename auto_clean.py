#!/usr/bin/env python3
"""
Script para limpiar todas las tablas automáticamente
"""

import sys
import os
from datetime import datetime

# Agregar el directorio actual al path para importar app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from app import Order, TechnicianHours, Technician, Advisor, StatusHistory, OrderComment

def clean_all_tables():
    """Limpia todas las tablas de datos automáticamente"""
    
    with app.app_context():
        print("🧹 Limpieza Automática de Tablas - AutoSvc")
        print("=" * 50)
        print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
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
        
        if orders_count == 0 and hours_count == 0 and technicians_count == 0:
            print("ℹ️  No hay datos para limpiar.")
            return True
        
        print("🗑️  Iniciando limpieza automática...")
        
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
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error durante la limpieza: {str(e)}")
            print("🔄 Se ha realizado rollback de los cambios.")
            return False

if __name__ == "__main__":
    clean_all_tables()
