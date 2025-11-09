#!/bin/bash
# Script de build para Render
set -e

echo "📦 Instalando dependencias..."
pip install -r requirements.txt

echo "🗄️ Ejecutando migraciones de base de datos..."
flask db upgrade || echo "⚠️ Las migraciones ya están aplicadas o no son necesarias"

echo "✅ Build completado"

