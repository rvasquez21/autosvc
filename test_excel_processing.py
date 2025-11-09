#!/usr/bin/env python3
"""
Script de prueba para verificar el procesamiento de archivos Excel
"""

import sys
import os
import pandas as pd

# Agregar el directorio actual al path para importar app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, parse_orders_file

def test_file_processing():
    """Probar el procesamiento de archivos"""
    
    print("🧪 Script de Prueba - Procesamiento de Archivos Excel")
    print("=" * 60)
    
    # Verificar archivos en uploads
    uploads_dir = "uploads"
    if not os.path.exists(uploads_dir):
        print("❌ Directorio uploads no existe")
        return
    
    files = os.listdir(uploads_dir)
    excel_files = [f for f in files if f.endswith(('.xlsx', '.xls'))]
    
    if not excel_files:
        print("❌ No se encontraron archivos Excel en uploads/")
        return
    
    print(f"📁 Archivos Excel encontrados: {excel_files}")
    print()
    
    with app.app_context():
        for file_name in excel_files:
            file_path = os.path.join(uploads_dir, file_name)
            print(f"🔍 Probando archivo: {file_name}")
            print(f"📊 Tamaño: {os.path.getsize(file_path)} bytes")
            
            try:
                # Probar con pandas directamente primero
                print("   📋 Probando lectura directa con pandas...")
                try:
                    df = pd.read_excel(file_path)
                    print(f"   ✅ Lectura directa exitosa: {len(df)} filas, {len(df.columns)} columnas")
                    print(f"   📋 Columnas: {list(df.columns[:5])}")
                except Exception as e:
                    print(f"   ❌ Error en lectura directa: {e}")
                
                # Probar con nuestra función
                print("   🔧 Probando función parse_orders_file...")
                try:
                    orders = parse_orders_file(file_path)
                    print(f"   ✅ Procesamiento exitoso: {len(orders)} órdenes encontradas")
                    
                    if orders:
                        print("   📋 Primera orden:")
                        first_order = orders[0]
                        for key, value in first_order.items():
                            print(f"      {key}: {value}")
                    
                except Exception as e:
                    print(f"   ❌ Error en procesamiento: {e}")
                
            except Exception as e:
                print(f"   ❌ Error general: {str(e)}")
            
            print("-" * 40)

if __name__ == "__main__":
    test_file_processing()
