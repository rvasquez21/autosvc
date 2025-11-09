import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    # Render proporciona DATABASE_URL automáticamente para PostgreSQL
    # Si no existe, usar SQLite como fallback
    database_url = os.environ.get("DATABASE_URL", "sqlite:///autosvc.db")
    
    # Render puede proporcionar DATABASE_URL con postgres://, necesitamos convertir a postgresql://
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,  # Verificar conexiones antes de usarlas
        "pool_recycle": 300,     # Reciclar conexiones cada 5 minutos
    }
    SECRET_KEY = os.environ.get("SECRET_KEY", "devkey-change-me-in-production")
