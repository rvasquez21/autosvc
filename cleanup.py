#!/usr/bin/env python3
"""
Script principal para limpiar datos de AutoSvc
Permite elegir entre diferentes opciones de limpieza
"""

import sys
import os
from datetime import datetime

# Agregar el directorio actual al path para importar app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from app import Order, TechnicianHours, Technician, Advisor, StatusHistory, OrderComment

def show_menu():
    """Muestra el menú de opciones"""
    print("\n🔧 Script de Limpieza de Datos - AutoSvc")
    print("=" * 50)
    print("Selecciona una opción:")
    print()
    print("1. 📊 Ver datos actuales")
    print("2. 🧹 Limpiar datos operativos (mantiene configuración)")
    print("3. 🗑️  Limpiar todo (mantiene solo usuarios)")
    print("4. 💾 Backup + Limpiar datos operativos")
    print("5. ❌ Salir")
    print()

def show_current_data():
    """Muestra un resumen de los datos actuales"""
    with app.app_context():
        print("\n📊 Resumen de datos actuales:")
        print("-" * 40)
        
        orders_count = Order.query.count()
        hours_count = TechnicianHours.query.count()
        technicians_count = Technician.query.count()
        advisors_count = Advisor.query.count()
        
        # Contar usuarios usando SQL directo
        try:
            users_count = db.session.execute(db.text("SELECT COUNT(*) FROM users")).scalar()
        except:
            users_count = 0
        
        print(f"   • Órdenes: {orders_count}")
        print(f"   • Horas de técnicos: {hours_count}")
        print(f"   • Técnicos: {technicians_count}")
        print(f"   • Asesores: {advisors_count}")
        print(f"   • Usuarios: {users_count}")
        print()

def clean_operational_data():
    """Limpia solo los datos operativos"""
    with app.app_context():
        orders_count = Order.query.count()
        hours_count = TechnicianHours.query.count()
        
        if orders_count == 0 and hours_count == 0:
            print("ℹ️  No hay datos operativos para limpiar.")
            return True
        
        print(f"📊 Eliminando:")
        print(f"   • {orders_count} órdenes")
        print(f"   • {hours_count} registros de horas")
        print(f"   • Técnicos y asesores")
        print()
        
        confirm = input("⚠️  ¿Continuar? (escribe 'SI'): ")
        if confirm != 'SI':
            print("❌ Operación cancelada.")
            return False
        
        try:
            print("🗑️  Eliminando datos...")
            
            OrderComment.query.delete()
            StatusHistory.query.delete()
            TechnicianHours.query.delete()
            Order.query.delete()
            Technician.query.delete()
            Advisor.query.delete()
            
            db.session.commit()
            
            print("✅ Datos operativos eliminados!")
            print("💾 Configuración preservada (usuarios, estados)")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {str(e)}")
            return False

def clean_all_data():
    """Limpia todos los datos excepto usuarios"""
    with app.app_context():
        orders_count = Order.query.count()
        hours_count = TechnicianHours.query.count()
        technicians_count = Technician.query.count()
        advisors_count = Advisor.query.count()
        
        print(f"📊 Eliminando TODOS los datos:")
        print(f"   • {orders_count} órdenes")
        print(f"   • {hours_count} registros de horas")
        print(f"   • {technicians_count} técnicos")
        print(f"   • {advisors_count} asesores")
        print()
        print("⚠️  Solo se mantendrán los usuarios del sistema")
        print()
        
        confirm = input("⚠️  ¿Estás SEGURO? (escribe 'SI'): ")
        if confirm != 'SI':
            print("❌ Operación cancelada.")
            return False
        
        try:
            print("🗑️  Eliminando todos los datos...")
            
            OrderComment.query.delete()
            StatusHistory.query.delete()
            TechnicianHours.query.delete()
            Order.query.delete()
            Technician.query.delete()
            Advisor.query.delete()
            
            db.session.commit()
            
            print("✅ Todos los datos eliminados!")
            print("💾 Solo usuarios preservados")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {str(e)}")
            return False

def backup_and_clean():
    """Crea backup y limpia datos operativos"""
    import shutil
    
    db_path = "instance/autosvc.db"
    if not os.path.exists(db_path):
        print("❌ No se encontró la base de datos.")
        return False
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backups/autosvc_backup_{timestamp}.db"
    
    # Crear directorio de backups
    os.makedirs("backups", exist_ok=True)
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup creado: {backup_path}")
        
        if clean_operational_data():
            print(f"\n💾 Backup disponible en: {backup_path}")
            return True
        return False
        
    except Exception as e:
        print(f"❌ Error creando backup: {str(e)}")
        return False

def main():
    """Función principal"""
    while True:
        show_menu()
        
        try:
            choice = input("Ingresa tu opción (1-5): ").strip()
            
            if choice == '1':
                show_current_data()
                
            elif choice == '2':
                clean_operational_data()
                
            elif choice == '3':
                clean_all_data()
                
            elif choice == '4':
                backup_and_clean()
                
            elif choice == '5':
                print("👋 ¡Hasta luego!")
                break
                
            else:
                print("❌ Opción inválida. Intenta de nuevo.")
                
        except KeyboardInterrupt:
            print("\n👋 Operación cancelada por el usuario.")
            break
        except Exception as e:
            print(f"❌ Error inesperado: {str(e)}")
        
        input("\nPresiona Enter para continuar...")

if __name__ == "__main__":
    main()
