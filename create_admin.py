#!/usr/bin/env python3
"""
Script para crear un usuario administrador inicial
"""
from app import app, db, User

def create_admin_user():
    with app.app_context():
        # Verificar si ya existe un admin
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print("ERROR: Ya existe un usuario administrador con el nombre 'admin'")
            return
        
        # Crear usuario administrador
        admin = User(
            username='admin',
            email='admin@autosvc.com',
            full_name='Administrador del Sistema',
            role='ADMIN'
        )
        admin.set_password('admin123')  # Cambiar en producción
        
        db.session.add(admin)
        db.session.commit()
        
        print("SUCCESS: Usuario administrador creado exitosamente:")
        print(f"   Usuario: admin")
        print(f"   Contraseña: admin123")
        print(f"   Email: admin@autosvc.com")
        print(f"   Rol: ADMIN")
        print("\nIMPORTANTE: Cambia la contraseña después del primer login")

def create_sample_users():
    """Crear algunos usuarios de ejemplo"""
    with app.app_context():
        # Crear técnico de ejemplo
        tech = User.query.filter_by(username='tecnico1').first()
        if not tech:
            tech = User(
                username='tecnico1',
                email='tecnico1@autosvc.com',
                full_name='Juan Pérez',
                role='TECNICO'
            )
            tech.set_password('tecnico123')
            db.session.add(tech)
        
        # Crear asesor de ejemplo
        advisor = User.query.filter_by(username='asesor1').first()
        if not advisor:
            advisor = User(
                username='asesor1',
                email='asesor1@autosvc.com',
                full_name='María García',
                role='ASESOR'
            )
            advisor.set_password('asesor123')
            db.session.add(advisor)
        
        db.session.commit()
        print("SUCCESS: Usuarios de ejemplo creados:")
        print("   Técnico: tecnico1 / tecnico123")
        print("   Asesor: asesor1 / asesor123")

if __name__ == "__main__":
    print("Creando usuarios iniciales para AutoSVC...")
    create_admin_user()
    create_sample_users()
    print("\nConfiguracion completada! Puedes iniciar la aplicacion.")
