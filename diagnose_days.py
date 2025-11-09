#!/usr/bin/env python3
"""
Script de diagnóstico para verificar el cálculo de días en órdenes
"""

import sys
import os
from datetime import datetime, timedelta

# Agregar el directorio actual al path para importar app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Order

def diagnose_days_calculation():
    """Diagnosticar el cálculo de días en órdenes"""
    
    with app.app_context():
        print("🔍 Diagnóstico de Cálculo de Días en Órdenes")
        print("=" * 60)
        
        # Obtener todas las órdenes
        orders = Order.query.all()
        print(f"📊 Total de órdenes en la base de datos: {len(orders)}")
        
        if not orders:
            print("❌ No hay órdenes en la base de datos")
            return
        
        # Analizar órdenes por días
        orders_by_days = {}
        orders_15_plus = []
        orders_7_plus = []
        
        for order in orders:
            days = order.days_in_shop()
            
            # Categorizar por días
            if days >= 15:
                orders_15_plus.append(order)
            elif days >= 7:
                orders_7_plus.append(order)
            
            # Agrupar por rangos de días
            if days < 7:
                key = "0-6 días"
            elif days < 15:
                key = "7-14 días"
            elif days < 30:
                key = "15-29 días"
            elif days < 60:
                key = "30-59 días"
            else:
                key = "60+ días"
            
            if key not in orders_by_days:
                orders_by_days[key] = []
            orders_by_days[key].append(order)
        
        print(f"\n📊 Distribución por días:")
        for key, order_list in orders_by_days.items():
            print(f"   {key}: {len(order_list)} órdenes")
        
        print(f"\n⚠️  Órdenes con 15+ días: {len(orders_15_plus)}")
        print(f"⚠️  Órdenes con 7+ días: {len(orders_7_plus)}")
        
        # Mostrar detalles de órdenes problemáticas
        if orders_15_plus:
            print(f"\n🔍 Detalles de órdenes con 15+ días:")
            print("-" * 80)
            print(f"{'ID':<5} {'Orden':<15} {'Placa':<10} {'Cliente':<20} {'Días':<8} {'Estado':<15} {'Fecha Creación'}")
            print("-" * 80)
            
            for order in orders_15_plus[:10]:  # Mostrar solo las primeras 10
                print(f"{order.id:<5} {order.order_number:<15} {order.plate:<10} {order.customer_name[:20]:<20} {order.days_in_shop():<8} {order.status:<15} {order.created_at.strftime('%d/%m/%Y')}")
            
            if len(orders_15_plus) > 10:
                print(f"... y {len(orders_15_plus) - 10} más")
        
        # Verificar el método days_in_shop
        print(f"\n🔧 Verificación del método days_in_shop():")
        if orders:
            sample_order = orders[0]
            days_calculated = sample_order.days_in_shop()
            manual_calculation = (datetime.utcnow().date() - sample_order.created_at.date()).days
            
            print(f"   Orden de muestra: {sample_order.order_number}")
            print(f"   Fecha creación: {sample_order.created_at.date()}")
            print(f"   Fecha actual: {datetime.utcnow().date()}")
            print(f"   Días calculados por método: {days_calculated}")
            print(f"   Días calculados manualmente: {manual_calculation}")
            print(f"   ✅ Método funciona correctamente: {days_calculated == manual_calculation}")
        
        # Verificar órdenes entregadas
        delivered_orders = Order.query.filter_by(status="ENTREGADO").all()
        print(f"\n📊 Órdenes entregadas: {len(delivered_orders)}")
        
        # Verificar órdenes no entregadas
        non_delivered = Order.query.filter(Order.status != "ENTREGADO").all()
        print(f"📊 Órdenes no entregadas: {len(non_delivered)}")
        
        # Verificar el filtro del dashboard
        print(f"\n🔍 Verificación del filtro del dashboard:")
        long_stays = Order.query.filter(Order.status != "ENTREGADO").all()
        long_15_dashboard = [o for o in long_stays if o.days_in_shop() >= 15]
        
        print(f"   Órdenes no entregadas: {len(long_stays)}")
        print(f"   Órdenes con 15+ días (filtro dashboard): {len(long_15_dashboard)}")
        print(f"   ✅ Filtro funciona correctamente: {len(long_15_dashboard) == len(orders_15_plus)}")

def test_specific_order():
    """Probar una orden específica"""
    
    with app.app_context():
        print(f"\n🧪 Prueba de orden específica:")
        
        # Buscar una orden con más de 15 días
        orders = Order.query.all()
        if not orders:
            print("❌ No hay órdenes para probar")
            return
        
        # Crear una orden de prueba con fecha antigua
        test_date = datetime.utcnow() - timedelta(days=20)
        
        print(f"   Fecha de prueba: {test_date.date()}")
        print(f"   Días desde entonces: {(datetime.utcnow().date() - test_date.date()).days}")
        
        # Simular el cálculo
        days_since_creation = (datetime.utcnow().date() - test_date.date()).days
        print(f"   ✅ Cálculo manual: {days_since_creation} días")
        print(f"   ✅ Es >= 15 días: {days_since_creation >= 15}")

if __name__ == "__main__":
    diagnose_days_calculation()
    test_specific_order()
