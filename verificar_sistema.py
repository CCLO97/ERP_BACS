#!/usr/bin/env python3
"""
Script para verificar que el sistema ERP BACS esté correctamente configurado
"""

import sys
import os

def verificar_python():
    """Verificar versión de Python"""
    print("🐍 Verificando Python...")
    version = sys.version_info
    print(f"   Versión: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 8:
        print("   ✅ Versión compatible")
        return True
    else:
        print("   ❌ Versión no compatible (se requiere Python 3.8+)")
        return False

def verificar_dependencias():
    """Verificar dependencias críticas"""
    print("\n📦 Verificando dependencias...")
    
    dependencias_criticas = {
        "flask": "Flask",
        "flask_sqlalchemy": "Flask-SQLAlchemy", 
        "flask_login": "Flask-Login",
        "flask_wtf": "Flask-WTF",
        "wtforms": "WTForms",
        "werkzeug": "Werkzeug",
        "pymysql": "PyMySQL",
        "dotenv": "python-dotenv",
        "reportlab": "ReportLab",
        "PIL": "Pillow",
        "bcrypt": "bcrypt"
    }
    
    todas_ok = True
    
    for modulo, nombre in dependencias_criticas.items():
        try:
            __import__(modulo)
            print(f"   ✅ {nombre}")
        except ImportError:
            print(f"   ❌ {nombre} - FALTANTE")
            todas_ok = False
    
    return todas_ok

def verificar_archivos():
    """Verificar archivos críticos del sistema"""
    print("\n📁 Verificando archivos del sistema...")
    
    archivos_criticos = [
        "app.py",
        "config.py", 
        "requirements.txt",
        "templates/base.html",
        "static/css/style.css"
    ]
    
    todos_ok = True
    
    for archivo in archivos_criticos:
        if os.path.exists(archivo):
            print(f"   ✅ {archivo}")
        else:
            print(f"   ❌ {archivo} - FALTANTE")
            todos_ok = False
    
    return todos_ok

def verificar_directorios():
    """Verificar directorios necesarios"""
    print("\n📂 Verificando directorios...")
    
    directorios = [
        "templates",
        "static",
        "static/css", 
        "uploads",
        "files"
    ]
    
    todos_ok = True
    
    for directorio in directorios:
        if os.path.exists(directorio):
            print(f"   ✅ {directorio}/")
        else:
            print(f"   ❌ {directorio}/ - FALTANTE")
            todos_ok = False
    
    return todos_ok

def main():
    """Función principal de verificación"""
    print("ERP BACS - Verificación del Sistema")
    print("=" * 40)
    
    # Verificaciones
    python_ok = verificar_python()
    deps_ok = verificar_dependencias()
    archivos_ok = verificar_archivos()
    directorios_ok = verificar_directorios()
    
    # Resumen
    print("\n📊 RESUMEN DE VERIFICACIÓN")
    print("=" * 30)
    print(f"Python: {'✅' if python_ok else '❌'}")
    print(f"Dependencias: {'✅' if deps_ok else '❌'}")
    print(f"Archivos: {'✅' if archivos_ok else '❌'}")
    print(f"Directorios: {'✅' if directorios_ok else '❌'}")
    
    # Estado general
    if python_ok and deps_ok and archivos_ok and directorios_ok:
        print("\n🎉 ¡Sistema completamente configurado!")
        print("🚀 Puedes ejecutar: python app.py")
        return True
    else:
        print("\n⚠️  El sistema necesita configuración adicional.")
        if not deps_ok:
            print("💡 Ejecuta: python instalar_dependencias.py")
        return False

if __name__ == "__main__":
    main()
