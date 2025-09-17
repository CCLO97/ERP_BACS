#!/usr/bin/env python3
"""
Setup completo automático para ERP BACS
Este script maneja toda la instalación y configuración del sistema
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_header(text):
    """Imprimir encabezado con formato"""
    print("\n" + "=" * 60)
    print(f"🚀 {text}")
    print("=" * 60)

def print_step(step, description):
    """Imprimir paso del proceso"""
    print(f"\n📋 Paso {step}: {description}")
    print("-" * 40)

def ejecutar_comando(comando, descripcion, critical=False):
    """Ejecutar un comando y mostrar el resultado"""
    print(f"🔄 {descripcion}...")
    try:
        resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
        if resultado.returncode == 0:
            print(f"✅ {descripcion} completado")
            return True
        else:
            print(f"❌ Error en {descripcion}:")
            print(resultado.stderr)
            if critical:
                print(f"❌ ERROR CRÍTICO: {descripcion} es requerido para continuar")
                return False
            return False
    except Exception as e:
        print(f"❌ Error ejecutando comando: {e}")
        if critical:
            return False
        return False

def verificar_python():
    """Verificar versión de Python"""
    print_step(1, "Verificando Python")
    
    version = sys.version_info
    print(f"🐍 Python: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 8:
        print("✅ Versión de Python compatible")
        return True
    else:
        print("❌ Se requiere Python 3.8 o superior")
        print("Descarga Python desde: https://www.python.org/downloads/")
        return False

def verificar_entorno_virtual():
    """Verificar si estamos en un entorno virtual"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def crear_entorno_virtual():
    """Crear entorno virtual si no existe"""
    print_step(2, "Configurando entorno virtual")
    
    if verificar_entorno_virtual():
        print("✅ Ya estás en un entorno virtual")
        return True
    
    venv_path = Path("venv")
    if venv_path.exists():
        print("✅ Entorno virtual ya existe")
        return True
    
    print("🔄 Creando entorno virtual...")
    if ejecutar_comando(f"{sys.executable} -m venv venv", "Creando entorno virtual", critical=True):
        print("\n⚠️  IMPORTANTE: Debes activar el entorno virtual:")
        print("Windows: venv\\Scripts\\activate")
        print("Linux/Mac: source venv/bin/activate")
        print("\nDespués de activarlo, ejecuta este script nuevamente")
        return False
    
    return False

def instalar_dependencias():
    """Instalar todas las dependencias"""
    print_step(3, "Instalando dependencias")
    
    # Actualizar pip
    ejecutar_comando(f"{sys.executable} -m pip install --upgrade pip", "Actualizando pip")
    
    # Verificar que requirements.txt existe
    if not os.path.exists("requirements.txt"):
        print("❌ Archivo requirements.txt no encontrado")
        return False
    
    # Instalar dependencias
    if ejecutar_comando(f"{sys.executable} -m pip install -r requirements.txt", "Instalando dependencias", critical=True):
        
        # Verificar instalaciones críticas
        print("\n🔍 Verificando instalaciones críticas...")
        
        # Verificar ReportLab
        try:
            import reportlab
            print(f"✅ ReportLab: {reportlab.Version}")
        except ImportError:
            print("❌ ReportLab no se pudo importar")
            print("🔄 Reinstalando ReportLab...")
            ejecutar_comando(f"{sys.executable} -m pip install reportlab==4.0.4", "Reinstalando ReportLab")
        
        # Verificar Pillow
        try:
            import PIL
            print(f"✅ Pillow: {PIL.__version__}")
        except ImportError:
            print("❌ Pillow no se pudo importar")
            print("🔄 Reinstalando Pillow...")
            ejecutar_comando(f"{sys.executable} -m pip install Pillow==11.3.0", "Reinstalando Pillow")
        
        # Verificar Flask
        try:
            import flask
            print(f"✅ Flask: {flask.__version__}")
        except ImportError:
            print("❌ Flask no se pudo importar")
            return False
        
        return True
    
    return False

def configurar_archivo_env():
    """Configurar archivo .env"""
    print_step(4, "Configurando variables de entorno")
    
    env_file = Path(".env")
    env_example = Path("env_example.txt")
    
    if env_file.exists():
        print("✅ Archivo .env ya existe")
        return True
    
    if not env_example.exists():
        print("❌ Archivo env_example.txt no encontrado")
        return False
    
    # Copiar archivo de ejemplo
    shutil.copy(env_example, env_file)
    print("✅ Archivo .env creado desde env_example.txt")
    
    print("\n⚠️  IMPORTANTE: Debes editar el archivo .env con tus datos:")
    print("- DB_USER: tu usuario de MySQL")
    print("- DB_PASSWORD: tu contraseña de MySQL")
    print("- SECRET_KEY: genera una clave secreta")
    print("- INITIAL_USER_EMAIL: email del administrador")
    print("- INITIAL_USER_PASSWORD: contraseña del administrador")
    
    return True

def verificar_mysql():
    """Verificar conexión a MySQL"""
    print_step(5, "Verificando MySQL")
    
    try:
        import pymysql
        print("✅ PyMySQL disponible")
    except ImportError:
        print("❌ PyMySQL no disponible")
        return False
    
    # Intentar leer configuración del .env
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ Archivo .env no encontrado")
        return False
    
    # Leer configuración básica
    print("✅ Archivo .env encontrado")
    print("⚠️  Asegúrate de que:")
    print("1. MySQL esté ejecutándose")
    print("2. La base de datos 'erp_bacs' exista")
    print("3. Las credenciales en .env sean correctas")
    
    return True

def ejecutar_migracion():
    """Ejecutar migración de base de datos"""
    print_step(6, "Ejecutando migración de base de datos")
    
    migrar_script = Path("migrar_db.py")
    if not migrar_script.exists():
        print("❌ Script migrar_db.py no encontrado")
        return False
    
    print("🔄 Ejecutando migración...")
    if ejecutar_comando(f"{sys.executable} migrar_db.py", "Migración de base de datos", critical=True):
        print("✅ Migración completada exitosamente")
        return True
    else:
        print("❌ Error en la migración")
        print("Verifica:")
        print("1. MySQL esté ejecutándose")
        print("2. Base de datos 'erp_bacs' exista")
        print("3. Credenciales en .env sean correctas")
        return False

def verificar_sistema():
    """Verificar que el sistema funcione"""
    print_step(7, "Verificando sistema")
    
    # Verificar archivos principales
    archivos_criticos = [
        "app.py",
        "config.py", 
        "ejecutar_app.py",
        "requirements.txt"
    ]
    
    for archivo in archivos_criticos:
        if os.path.exists(archivo):
            print(f"✅ {archivo}")
        else:
            print(f"❌ {archivo} no encontrado")
            return False
    
    # Verificar directorios
    directorios = ["static", "templates", "uploads"]
    for directorio in directorios:
        if os.path.exists(directorio):
            print(f"✅ directorio {directorio}/")
        else:
            print(f"⚠️  directorio {directorio}/ no encontrado (se creará automáticamente)")
    
    return True

def mostrar_resumen():
    """Mostrar resumen de instalación"""
    print_header("RESUMEN DE INSTALACIÓN")
    
    print("🎉 ¡Instalación completada exitosamente!")
    
    print("\n📋 Próximos pasos:")
    print("1. Verifica que el archivo .env tenga tus datos correctos")
    print("2. Asegúrate de que MySQL esté ejecutándose")
    print("3. Ejecuta: python ejecutar_app.py")
    print("4. Abre tu navegador en: http://localhost:5000")
    
    print("\n🔧 Comandos útiles:")
    print("- Activar entorno virtual: venv\\Scripts\\activate (Windows)")
    print("- Ejecutar aplicación: python ejecutar_app.py")
    print("- Ejecutar migración: python migrar_db.py")
    
    print("\n📞 Si tienes problemas:")
    print("- Revisa el archivo .env")
    print("- Verifica que MySQL esté ejecutándose")
    print("- Consulta la sección de solución de problemas en README.md")

def main():
    """Función principal"""
    print_header("SETUP COMPLETO - ERP BACS")
    print("Este script configurará completamente el sistema ERP BACS")
    
    # Verificar Python
    if not verificar_python():
        return False
    
    # Verificar entorno virtual
    if not verificar_entorno_virtual():
        print("\n⚠️  No estás en un entorno virtual")
        if crear_entorno_virtual():
            return False
        else:
            print("\n🔄 Entorno virtual creado. Actívalo y ejecuta este script nuevamente")
            return False
    
    # Instalar dependencias
    if not instalar_dependencias():
        print("\n❌ Error instalando dependencias")
        return False
    
    # Configurar .env
    if not configurar_archivo_env():
        print("\n❌ Error configurando .env")
        return False
    
    # Verificar MySQL
    if not verificar_mysql():
        print("\n❌ Error verificando MySQL")
        return False
    
    # Ejecutar migración
    if not ejecutar_migracion():
        print("\n❌ Error en migración")
        print("Puedes ejecutar manualmente: python migrar_db.py")
        return False
    
    # Verificar sistema
    if not verificar_sistema():
        print("\n❌ Error verificando sistema")
        return False
    
    # Mostrar resumen
    mostrar_resumen()
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ Setup completado exitosamente")
            sys.exit(0)
        else:
            print("\n❌ Setup falló")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelado por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)
