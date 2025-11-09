#!/usr/bin/env python3
"""
Script de prueba para verificar el procesamiento de archivos Excel
"""

import os
import sys
from app import app, parse_excel_file, read_html_robust

def test_file_processing():
    """Probar el procesamiento de archivos"""
    with app.app_context():
        # Verificar si hay archivos de ejemplo en la carpeta uploads
        uploads_dir = 'uploads'
        if not os.path.exists(uploads_dir):
            print("❌ La carpeta 'uploads' no existe")
            return
        
        # Buscar archivos Excel
        excel_files = []
        for file in os.listdir(uploads_dir):
            if file.endswith(('.xls', '.xlsx')):
                excel_files.append(os.path.join(uploads_dir, file))
        
        if not excel_files:
            print("❌ No se encontraron archivos Excel en la carpeta 'uploads'")
            print("   Coloca un archivo Excel (.xls o .xlsx) en la carpeta 'uploads' para probar")
            return
        
        print(f"✅ Se encontraron {len(excel_files)} archivo(s) Excel:")
        for file_path in excel_files:
            print(f"   - {file_path}")
        
        # Probar cada archivo
        for file_path in excel_files:
            print(f"\n🔍 Probando archivo: {file_path}")
            try:
                # Verificar tamaño del archivo
                file_size = os.path.getsize(file_path)
                print(f"   Tamaño: {file_size} bytes")
                
                if file_size == 0:
                    print("   ❌ El archivo está vacío")
                    continue
                
                # Probar lectura con método robusto
                try:
                    df_list = read_html_robust(file_path)
                    print(f"   ✅ Lectura exitosa: {len(df_list)} tabla(s) encontrada(s)")
                    
                    # Mostrar información de la primera tabla
                    if df_list and len(df_list) > 0:
                        df = df_list[0]
                        print(f"   📊 Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
                        print(f"   📋 Columnas: {list(df.columns)}")
                        
                        # Probar procesamiento completo
                        try:
                            processed_data = parse_excel_file(file_path)
                            print(f"   ✅ Procesamiento exitoso: {len(processed_data)} registros procesados")
                        except Exception as e:
                            print(f"   ❌ Error en procesamiento: {str(e)}")
                    
                except Exception as e:
                    print(f"   ❌ Error en lectura: {str(e)}")
                    
            except Exception as e:
                print(f"   ❌ Error general: {str(e)}")

if __name__ == "__main__":
    print("🧪 Prueba de procesamiento de archivos Excel")
    print("=" * 50)
    test_file_processing()
    print("\n✅ Prueba completada")
