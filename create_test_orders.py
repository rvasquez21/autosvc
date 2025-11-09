#!/usr/bin/env python3
"""
Script para crear órdenes de prueba con fechas antiguas
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Agregar el directorio actual al path para importar app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Order, Technician, Advisor

def create_test_orders():
    """Crear órdenes de prueba con fechas antiguas"""
    
    with app.app_context():
        print("🧪 Creando órdenes de prueba con fechas antiguas")
        print("=" * 60)
        
        # Verificar si ya hay órdenes
        existing_orders = Order.query.count()
        print(f"📊 Órdenes existentes: {existing_orders}")
        
        if existing_orders > 0:
            confirm = input("⚠️  ¿Crear órdenes de prueba adicionales? (escribe 'SI'): ")
            if confirm != 'SI':
                print("❌ Operación cancelada")
                return
        
        # Datos de prueba
        test_plates = ['ABC123', 'XYZ789', 'DEF456', 'GHI012', 'JKL345']
        test_customers = ['Juan Pérez', 'María García', 'Carlos López', 'Ana Martínez', 'Pedro Rodríguez']
        test_brands = ['Toyota', 'Honda', 'Ford', 'Chevrolet', 'Nissan']
        test_statuses = ['RECEPCION', 'EN_PROCESO', 'ESPERANDO_REPUESTOS', 'LISTO_PARA_ENTREGA']
        
        # Crear órdenes con diferentes fechas
        test_orders = [
            {'days_ago': 5, 'count': 3},    # Órdenes recientes
            {'days_ago': 10, 'count': 2},   # Órdenes de 1-2 semanas
            {'days_ago': 20, 'count': 3},   # Órdenes con 15+ días
            {'days_ago': 30, 'count': 2},   # Órdenes muy antiguas
            {'days_ago': 45, 'count': 1},   # Órdenes extremadamente antiguas
        ]
        
        orders_created = 0
        
        for test_group in test_orders:
            days_ago = test_group['days_ago']
            count = test_group['count']
            
            print(f"📅 Creando {count} órdenes de hace {days_ago} días...")
            
            for i in range(count):
                # Crear fecha de creación
                created_date = datetime.utcnow() - timedelta(days=days_ago)
                
                # Generar datos aleatorios
                plate = random.choice(test_plates) + str(random.randint(100, 999))
                customer = random.choice(test_customers)
                brand = random.choice(test_brands)
                status = random.choice(test_statuses)
                
                # Crear orden
                order = Order(
                    order_number=f"TEST{orders_created + 1:04d}",
                    plate=plate,
                    vin=f"VIN{random.randint(100000, 999999)}",
                    chasis=f"CHASIS{random.randint(100000, 999999)}",
                    brand=brand,
                    customer_name=customer,
                    advisor="Sistema",
                    technician="Técnico Prueba",
                    service_type="Mantenimiento",
                    status=status,
                    symptom=f"Orden de prueba creada hace {days_ago} días",
                    priority="NORMAL",
                    created_at=created_date,
                    updated_at=created_date
                )
                
                db.session.add(order)
                orders_created += 1
        
        # Confirmar cambios
        try:
            db.session.commit()
            print(f"\n✅ Se crearon {orders_created} órdenes de prueba")
            
            # Verificar el resultado
            total_orders = Order.query.count()
            orders_15_plus = [o for o in Order.query.filter(Order.status != "ENTREGADO").all() if o.days_in_shop() >= 15]
            orders_7_plus = [o for o in Order.query.filter(Order.status != "ENTREGADO").all() if o.days_in_shop() >= 7]
            
            print(f"\n📊 Resultado:")
            print(f"   Total de órdenes: {total_orders}")
            print(f"   Órdenes con 7+ días: {len(orders_7_plus)}")
            print(f"   Órdenes con 15+ días: {len(orders_15_plus)}")
            
            if orders_15_plus:
                print(f"\n🔍 Órdenes con 15+ días:")
                for order in orders_15_plus[:5]:
                    print(f"   {order.order_number}: {order.days_in_shop()} días ({order.created_at.strftime('%d/%m/%Y')})")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creando órdenes: {e}")

if __name__ == "__main__":
    create_test_orders()
