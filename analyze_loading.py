#!/usr/bin/env python3
"""
Script para analizar por qué no se calculan correctamente los días al cargar órdenes desde Excel
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Agregar el directorio actual al path para importar app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Order, parse_orders_file

def analyze_file_loading():
    """Analizar el proceso de carga de archivos"""
    
    print("🔍 Análisis del Proceso de Carga de Órdenes")
    print("=" * 60)
    
    # Analizar el archivo ejemplo_comisiones.xlsx
    file_path = "uploads/ejemplo_comisiones.xlsx"
    
    if not os.path.exists(file_path):
        print("❌ Archivo no encontrado")
        return
    
    print(f"📁 Analizando archivo: {file_path}")
    
    # Leer el archivo con pandas
    try:
        df = pd.read_excel(file_path)
        print(f"✅ Archivo leído exitosamente")
        print(f"📊 Dimensiones: {len(df)} filas x {len(df.columns)} columnas")
        print(f"📋 Columnas: {list(df.columns)}")
        print()
        
        # Mostrar datos
        print("📋 Contenido del archivo:")
        print(df.to_string())
        print()
        
        # Analizar fechas
        print("📅 Análisis de fechas:")
        for idx, row in df.iterrows():
            print(f"   Fila {idx + 1}:")
            print(f"     Orden: {row['No. Orden']}")
            print(f"     Recepción: {row['Recepción']} (tipo: {type(row['Recepción'])})")
            print(f"     Completado: {row['Completado']} (tipo: {type(row['Completado'])})")
            
            # Intentar convertir fechas
            try:
                reception_date = pd.to_datetime(row['Recepción'])
                completion_date = pd.to_datetime(row['Completado'])
                
                days_ago = (datetime.now().date() - reception_date.date()).days
                print(f"     ✅ Fecha recepción convertida: {reception_date.date()}")
                print(f"     ✅ Días desde recepción: {days_ago}")
                print(f"     ✅ Es >= 15 días: {days_ago >= 15}")
                
            except Exception as e:
                print(f"     ❌ Error convirtiendo fechas: {e}")
            print()
        
    except Exception as e:
        print(f"❌ Error leyendo archivo: {e}")
        return
    
    # Probar la función parse_orders_file
    print("🔧 Probando función parse_orders_file:")
    try:
        orders = parse_orders_file(file_path)
        print(f"✅ Función ejecutada exitosamente")
        print(f"📊 Órdenes procesadas: {len(orders)}")
        
        if orders:
            print("\n📋 Primera orden procesada:")
            first_order = orders[0]
            for key, value in first_order.items():
                print(f"   {key}: {value}")
                
            # Verificar fecha de recepción
            reception_date = first_order.get('reception_date')
            if reception_date:
                days_since = (datetime.now().date() - reception_date.date()).days
                print(f"\n📅 Análisis de fecha:")
                print(f"   Fecha recepción: {reception_date.date()}")
                print(f"   Días desde recepción: {days_since}")
                print(f"   Es >= 15 días: {days_since >= 15}")
        
    except Exception as e:
        print(f"❌ Error en parse_orders_file: {e}")

def test_date_parsing():
    """Probar diferentes formatos de fecha"""
    
    print("\n🧪 Prueba de Parsing de Fechas")
    print("=" * 40)
    
    test_dates = [
        "01/10/25",
        "01/10/2025", 
        "2025-10-01",
        "01-10-25",
        "1/10/25",
        "01/Oct/25"
    ]
    
    for date_str in test_dates:
        print(f"📅 Probando: '{date_str}'")
        try:
            parsed_date = pd.to_datetime(date_str)
            days_ago = (datetime.now().date() - parsed_date.date()).days
            print(f"   ✅ Convertido: {parsed_date.date()}")
            print(f"   ✅ Días atrás: {days_ago}")
            print(f"   ✅ Es >= 15 días: {days_ago >= 15}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()

def simulate_order_creation():
    """Simular la creación de órdenes con fechas antiguas"""
    
    print("\n🧪 Simulación de Creación de Órdenes")
    print("=" * 50)
    
    with app.app_context():
        # Crear órdenes de prueba con fechas antiguas
        test_orders = [
            {'order_number': 'FC001', 'reception_date': datetime.now() - timedelta(days=20)},
            {'order_number': 'FC002', 'reception_date': datetime.now() - timedelta(days=30)},
            {'order_number': 'FC003', 'reception_date': datetime.now() - timedelta(days=45)},
        ]
        
        for order_data in test_orders:
            order = Order(
                order_number=order_data['order_number'],
                plate=f"PLATE{order_data['order_number']}",
                customer_name="Cliente Prueba",
                advisor="Asesor Prueba",
                technician="Técnico Prueba",
                service_type="Mantenimiento",
                status="RECEPCION",
                created_at=order_data['reception_date']
            )
            
            db.session.add(order)
            
            # Calcular días
            days = order.days_in_shop()
            print(f"📋 Orden {order_data['order_number']}:")
            print(f"   Fecha creación: {order_data['reception_date'].date()}")
            print(f"   Días en taller: {days}")
            print(f"   Es >= 15 días: {days >= 15}")
            print()
        
        try:
            db.session.commit()
            print("✅ Órdenes de prueba creadas exitosamente")
            
            # Verificar en la base de datos
            orders_15_plus = [o for o in Order.query.filter(Order.status != "ENTREGADO").all() if o.days_in_shop() >= 15]
            print(f"📊 Órdenes con 15+ días en BD: {len(orders_15_plus)}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creando órdenes: {e}")

if __name__ == "__main__":
    analyze_file_loading()
    test_date_parsing()
    simulate_order_creation()
