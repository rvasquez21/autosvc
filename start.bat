@echo off
REM Script de inicio para Windows
python -m waitress --listen=0.0.0.0:%PORT% app:app

