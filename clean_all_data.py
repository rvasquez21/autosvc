#!/usr/bin/env python3
"""
Script para limpiar todos los datos de la aplicación
Mantiene la estructura de las tablas pero elimina todos los registros
"""
import os
import sys
from app import app, db
# Importar todos los modelos
from app import (
    User, Order, OrderComment, StatusHistory, Status,
    Technician, TechnicianHours, Advisor, AdvisorContact,
    Notification, PaintShopInfo
)

# Intentar importar Repuesto si existe
try:
    from app import Repuesto
except ImportError:
    Repuesto = None

def clean_all_data(skip_confirmation=False):
    """Eliminar todos los datos de todas las tablas"""
    print("=" * 60)
    print("LIMPIEZA DE DATOS DE LA APLICACIÓN")
    print("=" * 60)
    print("\n⚠️  ADVERTENCIA: Esta operación eliminará TODOS los datos de la aplicación.")
    print("   La estructura de las tablas se mantendrá intacta.")
    print("\nTablas que se limpiarán:")
    print("  - users (excepto si eres el único usuario)")
    print("  - orders")
    print("  - order_comments")
    print("  - status_history")
    print("  - status (se mantendrán los estatus del sistema)")
    print("  - technicians")
    print("  - technician_hours")
    print("  - advisors")
    print("  - advisor_contacts")
    print("  - notifications")
    print("  - paint_shop_info")
    print("  - repuestos")
    
    # Confirmación
    if not skip_confirmation:
        response = input("\n¿Estás seguro de que deseas continuar? (escribe 'SI' para confirmar): ")
        if response.upper() != 'SI':
            print("❌ Operación cancelada.")
            return False
    else:
        print("\n✅ Confirmación automática activada. Procediendo con la limpieza...")
    
    with app.app_context():
        try:
            # Contar registros antes de eliminar
            counts_before = {
                'users': User.query.count(),
                'orders': Order.query.count(),
                'order_comments': OrderComment.query.count(),
                'status_history': StatusHistory.query.count(),
                'technicians': Technician.query.count(),
                'technician_hours': TechnicianHours.query.count(),
                'advisors': Advisor.query.count(),
                'advisor_contacts': AdvisorContact.query.count(),
                'notifications': Notification.query.count(),
                'paint_shop_info': PaintShopInfo.query.count(),
                'repuestos': Repuesto.query.count() if Repuesto else 0,
            }
            
            print("\n📊 Registros antes de la limpieza:")
            for table, count in counts_before.items():
                print(f"   {table}: {count}")
            
            print("\n🗑️  Iniciando limpieza...")
            
            # Eliminar en orden para respetar foreign keys
            # Primero las tablas dependientes (que tienen foreign keys)
            
            # 1. Eliminar relaciones y datos dependientes de orders
            print("   Eliminando advisor_contacts...")
            AdvisorContact.query.delete()
            
            print("   Eliminando notifications...")
            Notification.query.delete()
            
            print("   Eliminando technician_hours...")
            TechnicianHours.query.delete()
            
            print("   Eliminando order_comments...")
            OrderComment.query.delete()
            
            print("   Eliminando status_history...")
            StatusHistory.query.delete()
            
            # 2. Eliminar datos que dependen de orders (antes de eliminar orders)
            print("   Eliminando paint_shop_info...")
            PaintShopInfo.query.delete()
            
            # Intentar eliminar repuestos si existe (depende de orders)
            if Repuesto:
                print("   Eliminando repuestos...")
                Repuesto.query.delete()
            else:
                print("   (Tabla repuestos no encontrada, omitiendo)")
            
            # 3. Ahora eliminar orders (ya no tiene dependencias)
            print("   Eliminando orders...")
            Order.query.delete()
            
            # 4. Eliminar entidades principales
            print("   Eliminando technicians...")
            Technician.query.delete()
            
            print("   Eliminando advisors...")
            Advisor.query.delete()
            
            # 5. Eliminar usuarios (excepto el actual si es el único)
            print("   Eliminando users...")
            # Mantener al menos un usuario admin si es necesario
            admin_users = User.query.filter_by(role='ADMIN').all()
            if len(admin_users) == 1:
                print("   ⚠️  Se mantendrá un usuario ADMIN para evitar bloqueo del sistema")
                User.query.filter(User.role != 'ADMIN').delete()
            else:
                User.query.delete()
            
            # 4. NO eliminar status - son configuración del sistema
            print("   (Manteniendo status - configuración del sistema)")
            
            # Commit de todos los cambios
            db.session.commit()
            
            print("\n✅ Limpieza completada exitosamente!")
            
            # Contar registros después
            counts_after = {
                'users': User.query.count(),
                'orders': Order.query.count(),
                'order_comments': OrderComment.query.count(),
                'status_history': StatusHistory.query.count(),
                'technicians': Technician.query.count(),
                'technician_hours': TechnicianHours.query.count(),
                'advisors': Advisor.query.count(),
                'advisor_contacts': AdvisorContact.query.count(),
                'notifications': Notification.query.count(),
                'paint_shop_info': PaintShopInfo.query.count(),
            }
            
            print("\n📊 Registros después de la limpieza:")
            for table, count in counts_after.items():
                print(f"   {table}: {count}")
            
            print("\n💡 Próximos pasos sugeridos:")
            print("   1. Crear un usuario administrador: python create_admin.py")
            print("   2. Crear datos de prueba (opcional): python seeds.py")
            print("   3. Crear técnicos y asesores desde la interfaz web")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error durante la limpieza: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    # Verificar si se pasó --yes como argumento
    skip_confirmation = '--yes' in sys.argv or '-y' in sys.argv
    success = clean_all_data(skip_confirmation=skip_confirmation)
    sys.exit(0 if success else 1)

