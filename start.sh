#!/bin/bash
# Script de inicio para producción
if command -v waitress-serve &> /dev/null; then
    waitress-serve --listen=0.0.0.0:$PORT app:app
elif command -v gunicorn &> /dev/null; then
    gunicorn --bind 0.0.0.0:$PORT app:app
else
    python -m waitress --listen=0.0.0.0:$PORT app:app
fi

