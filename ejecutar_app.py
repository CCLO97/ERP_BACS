#!/usr/bin/env python3
"""
Script para ejecutar la aplicación ERP BACS
"""

import os
import sys

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Función principal para ejecutar la aplicación"""
    print("🚀 Iniciando ERP BACS...")
    print("=" * 50)
    
    try:
        # Importar y ejecutar la aplicación
        from app import app, init_db
        
        print("✅ Aplicación importada correctamente")
        
        # Inicializar base de datos
        print("📊 Inicializando base de datos...")
        init_db()
        
        print("🌐 Iniciando servidor web...")
        print("📍 URL: http://localhost:5000")
        print("=" * 50)
        
        # Ejecutar la aplicación
        app.run(debug=True, host='0.0.0.0', port=5000)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
