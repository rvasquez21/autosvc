#!/usr/bin/env python3
"""
Script para limpiar solo las tablas de datos operativos
Mantiene usuarios, estados y configuración del sistema
"""

import sys
import os
from datetime import datetime

# Agregar el directorio actual al path para importar app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from app import Order, TechnicianHours, Technician, Advisor, StatusHistory, OrderComment

def clean_operational_data():
    """Limpia solo los datos operativos, manteniendo configuración"""
    
    with app.app_context():
        print("🧹 Limpiando datos operativos...")
        print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)
        
        # Contar registros
        orders_count = Order.query.count()
        hours_count = TechnicianHours.query.count()
        technicians_count = Technician.query.count()
        advisors_count = Advisor.query.count()
        
        print(f"📊 Datos a eliminar:")
        print(f"   • Órdenes: {orders_count}")
        print(f"   • Horas de técnicos: {hours_count}")
        print(f"   • Técnicos: {technicians_count}")
        print(f"   • Asesores: {advisors_count}")
        print()
        
        if orders_count == 0 and hours_count == 0:
            print("ℹ️  No hay datos operativos para limpiar.")
            return True
        
        # Confirmar
        confirm = input("⚠️  ¿Eliminar datos operativos? (escribe 'SI'): ")
        if confirm != 'SI':
            print("❌ Operación cancelada.")
            return False
        
        try:
            print("\n🗑️  Eliminando datos operativos...")
            
            # Eliminar datos relacionados primero
            OrderComment.query.delete()
            StatusHistory.query.delete()
            TechnicianHours.query.delete()
            Order.query.delete()
            
            # Eliminar maestros
            Technician.query.delete()
            Advisor.query.delete()
            
            db.session.commit()
            
            print("✅ Datos operativos eliminados exitosamente!")
            print("\n💾 Configuración preservada:")
            print("   • Usuarios del sistema")
            print("   • Estados configurados")
            print("   • Configuración general")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {str(e)}")
            return False

if __name__ == "__main__":
    clean_operational_data()
