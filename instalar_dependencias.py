#!/usr/bin/env python3
"""
Script para instalar todas las dependencias necesarias para el ERP BACS
"""

import subprocess
import sys
import os

def instalar_dependencias():
    """Instalar todas las dependencias necesarias"""
    
    dependencias = [
        "Flask==2.3.3",
        "Flask-SQLAlchemy==3.0.5", 
        "Flask-Login==0.6.3",
        "Flask-WTF==1.1.1",
        "WTForms==3.0.1",
        "Werkzeug==2.3.7",
        "PyMySQL==1.1.0",
        "python-dotenv==1.0.0",
        "reportlab==4.0.4",
        "Pillow==11.3.0",
        "bcrypt==4.0.1"
    ]
    
    print("🔧 Instalando dependencias para ERP BACS...")
    print("=" * 50)
    
    for dep in dependencias:
        try:
            print(f"📦 Instalando {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"✅ {dep} instalado correctamente")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error instalando {dep}: {e}")
            return False
    
    print("=" * 50)
    print("🎉 Todas las dependencias han sido instaladas correctamente!")
    print("\n📋 Dependencias instaladas:")
    for dep in dependencias:
        print(f"   • {dep}")
    
    print("\n🚀 Ahora puedes ejecutar la aplicación:")
    print("   python app.py")
    
    return True

def verificar_dependencias():
    """Verificar que todas las dependencias estén instaladas"""
    
    dependencias_verificar = [
        "flask",
        "flask_sqlalchemy", 
        "flask_login",
        "flask_wtf",
        "wtforms",
        "werkzeug",
        "pymysql",
        "dotenv",
        "reportlab",
        "PIL",
        "bcrypt"
    ]
    
    print("🔍 Verificando dependencias...")
    print("=" * 30)
    
    todas_instaladas = True
    
    for dep in dependencias_verificar:
        try:
            __import__(dep)
            print(f"✅ {dep} - OK")
        except ImportError:
            print(f"❌ {dep} - FALTANTE")
            todas_instaladas = False
    
    if todas_instaladas:
        print("\n🎉 Todas las dependencias están instaladas!")
        return True
    else:
        print("\n⚠️  Faltan algunas dependencias. Ejecuta la instalación.")
        return False

if __name__ == "__main__":
    print("ERP BACS - Instalador de Dependencias")
    print("=" * 40)
    
    # Verificar si ya están instaladas
    if verificar_dependencias():
        print("\n✅ No es necesario instalar dependencias.")
    else:
        print("\n🔧 Instalando dependencias faltantes...")
        if instalar_dependencias():
            print("\n🔍 Verificando instalación...")
            verificar_dependencias()
        else:
            print("\n❌ Error en la instalación. Revisa los mensajes anteriores.")
            sys.exit(1)
