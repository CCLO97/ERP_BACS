#!/usr/bin/env python3
"""
Script para migrar la base de datos ERP BACS
Este script crea todas las tablas necesarias y datos iniciales
"""

import os
import sys
from sqlalchemy import text

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def migrar_base_datos():
    """Función principal para migrar la base de datos"""
    print("INICIANDO MIGRACION DE BASE DE DATOS ERP BACS...")
    print("=" * 60)
    
    # Verificar que existe el archivo .env
    if not os.path.exists('.env'):
        print("ERROR: No se encontro el archivo .env")
        print("Por favor:")
        print("   1. Copia env_example.txt a .env")
        print("   2. Configura tus credenciales de MySQL")
        print("   3. Ejecuta nuevamente: python migrar_db.py")
        return 1
    
    try:
        # Importar la aplicación y configuración
        from app import app, db
        from config import Config
        
        print("OK - Aplicacion importada correctamente")
        print(f"Conectando a base de datos: {Config.SQLALCHEMY_DATABASE_URI}")
        
        # Verificar que las credenciales están configuradas
        if not Config.INITIAL_USER_EMAIL or not Config.INITIAL_USER_PASSWORD:
            print("ERROR: Credenciales de usuario inicial no configuradas")
            print("Por favor configura en tu archivo .env:")
            print("   INITIAL_USER_EMAIL=tu_email@empresa.com")
            print("   INITIAL_USER_PASSWORD=tu_contraseña_segura")
            return 1
        
        with app.app_context():
            # Crear todas las tablas usando SQLAlchemy
            print("Creando tablas de la base de datos...")
            db.create_all()
            print("OK - Tablas creadas correctamente")
            
            # Crear datos iniciales
            print("Creando datos iniciales...")
            
            # Crear roles si no existen
            from app import Rol
            if not Rol.query.first():
                print("Creando roles del sistema...")
                roles = [
                    Rol(nombre='Administrador', descripcion='Acceso completo al sistema'),
                    Rol(nombre='Coordinador', descripcion='Gestion de incidencias y asignacion a tecnicos'),
                    Rol(nombre='Tecnico', descripcion='Edicion de incidencias asignadas'),
                    Rol(nombre='Usuario', descripcion='Usuario estandar del sistema')
                ]
                for rol in roles:
                    db.session.add(rol)
                db.session.commit()
                print("OK - Roles creados")
            
            # Crear sistemas por defecto si no existen
            from app import Sistema
            if not Sistema.query.first():
                print("Creando sistemas por defecto...")
                sistemas = [
                    Sistema(nombre='CCTV', descripcion='Sistema de videovigilancia y camaras de seguridad'),
                    Sistema(nombre='Control de Acceso', descripcion='Sistemas de control de acceso y tarjetas'),
                    Sistema(nombre='Alarmas', descripcion='Sistemas de alarmas y deteccion de intrusos'),
                    Sistema(nombre='Redes', descripcion='Infraestructura de red y comunicaciones'),
                    Sistema(nombre='Automatizacion', descripcion='Sistemas de automatizacion y control'),
                    Sistema(nombre='Iluminacion', descripcion='Sistemas de iluminacion inteligente'),
                    Sistema(nombre='Climatizacion', descripcion='Sistemas de climatizacion y HVAC'),
                    Sistema(nombre='Seguridad', descripcion='Sistemas de seguridad perimetral'),
                    Sistema(nombre='Comunicaciones', descripcion='Sistemas de comunicacion interna'),
                    Sistema(nombre='Otros', descripcion='Otros sistemas y servicios')
                ]
                for sistema in sistemas:
                    db.session.add(sistema)
                db.session.commit()
                print("OK - Sistemas creados")
            
            # Crear usuario administrador inicial
            from app import User
            from werkzeug.security import generate_password_hash
            
            if not User.query.first():
                print("Creando usuario administrador inicial...")
                
                # Obtener el rol de administrador
                admin_rol = Rol.query.filter_by(nombre='Administrador').first()
                
                if admin_rol:
                    # Crear usuario administrador
                    admin_user = User(
                        nombre='Administrador del Sistema',
                        tipo_documento='CC',
                        numero_documento='12345678',
                        telefono='3000000000',
                        correo=Config.INITIAL_USER_EMAIL,
                        password_hash=generate_password_hash(Config.INITIAL_USER_PASSWORD),
                        rol_id=admin_rol.id
                    )
                    db.session.add(admin_user)
                    db.session.commit()
                    print("OK - Usuario administrador creado")
                    print(f"   Email: {Config.INITIAL_USER_EMAIL}")
                    print(f"   Contraseña: {Config.INITIAL_USER_PASSWORD}")
                else:
                    print("ERROR - No se encontro el rol de Administrador")
            
            # Crear indices por defecto
            from app import Indice
            if not Indice.query.first():
                print("Creando indices por defecto...")
                indices = [
                    Indice(prefijo='INC', numero_actual=0, formato='000000'),
                    Indice(prefijo='INF', numero_actual=0, formato='000000'),
                    Indice(prefijo='CLI', numero_actual=0, formato='000000')
                ]
                for indice in indices:
                    db.session.add(indice)
                db.session.commit()
                print("OK - Indices creados")
            
            print("=" * 60)
            print("MIGRACION COMPLETADA EXITOSAMENTE!")
            print("=" * 60)
            print("Resumen de la migracion:")
            print(f"   - Base de datos: {Config.SQLALCHEMY_DATABASE_URI}")
            print(f"   - Tablas creadas: {len(db.metadata.tables)}")
            print(f"   - Roles creados: {Rol.query.count()}")
            print(f"   - Sistemas creados: {Sistema.query.count()}")
            print(f"   - Usuarios creados: {User.query.count()}")
            print(f"   - Indices creados: {Indice.query.count()}")
            print("=" * 60)
            print("Ahora puedes ejecutar: python ejecutar_app.py")
            print("Accede a: http://localhost:5000")
            print("=" * 60)
            
    except Exception as e:
        print(f"ERROR durante la migracion: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(migrar_base_datos())