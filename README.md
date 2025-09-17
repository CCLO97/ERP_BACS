# ERP BACS - Sistema de Gestión de Incidencias

## 📋 Descripción del Sistema

El ERP BACS es un sistema de gestión empresarial desarrollado específicamente para la empresa BACS (Building Automation and Control System SAS). Este sistema permite la gestión integral de incidencias técnicas, clientes, usuarios, sedes y sistemas, proporcionando una plataforma centralizada para el seguimiento y resolución de problemas técnicos.

## 🚀 Instalación y Configuración Completa

### Requisitos Previos

Antes de instalar el sistema, asegúrate de tener instalado en tu computadora:

1. **Python 3.8 o superior** - Descárgalo desde [python.org](https://www.python.org/downloads/)
2. **MySQL Server** - Descárgalo desde [mysql.com](https://dev.mysql.com/downloads/mysql/)
3. **Git** (opcional) - Para clonar el repositorio desde [git-scm.com](https://git-scm.com/downloads)

### Instalación Automática (Recomendado)

Para una instalación completa y automática, ejecuta:

```bash
python setup_completo.py
```

Este script se encargará de:
- ✅ Crear el entorno virtual
- ✅ Instalar todas las dependencias
- ✅ Configurar la base de datos
- ✅ Crear el archivo .env
- ✅ Ejecutar las migraciones
- ✅ Verificar que todo funcione correctamente

### Instalación Manual Paso a Paso

#### 1. Preparar el Entorno de Desarrollo

```bash
# Crear un directorio para el proyecto
mkdir erp_bacs
cd erp_bacs

# Crear un entorno virtual de Python
python -m venv venv

# Activar el entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate
```

#### 2. Instalar Dependencias

```bash
# Actualizar pip
python -m pip install --upgrade pip setuptools wheel

# Instalar todas las librerías necesarias
pip install -r requirements.txt
```

**⚠️ Si tienes problemas con imports (como "reportlab not found"):**

```bash
# Reinstalar ReportLab específicamente
pip uninstall reportlab
pip install reportlab==4.0.4

# Reinstalar Pillow específicamente
pip uninstall Pillow
pip install Pillow==11.3.0

# Verificar instalación
python -c "import reportlab; print('ReportLab OK')"
python -c "import PIL; print('Pillow OK')"
```

#### 3. Configurar Variables de Entorno

1. Copia el archivo `env_example.txt` y renómbralo a `.env`
2. Edita el archivo `.env` con tus datos de conexión:

```env
# Configuración de la base de datos
DB_HOST=localhost
DB_USER=tu_usuario_mysql
DB_PASSWORD=tu_contraseña_mysql
DB_NAME=erp_bacs

# Configuración de la aplicación
SECRET_KEY=tu_clave_secreta_muy_segura_aqui_2024
FLASK_ENV=development
FLASK_DEBUG=True

# Usuario inicial del sistema (administrador)
INITIAL_USER_EMAIL=admin@tuempresa.com
INITIAL_USER_PASSWORD=tu_contraseña_segura_aqui
```

#### 4. Configurar la Base de Datos MySQL

1. Abre MySQL Workbench, phpMyAdmin o tu cliente MySQL preferido
2. Crea una nueva base de datos llamada `erp_bacs`:
   ```sql
   CREATE DATABASE erp_bacs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

#### 5. Migración de la Base de Datos

```bash
# Ejecutar script de migración
python migrar_db.py
```

**Lo que hace la migración:**
- ✅ Crea todas las tablas del sistema
- ✅ Crea roles del sistema (Administrador, Coordinador, Técnico, Usuario)
- ✅ Crea sistemas por defecto (CCTV, Control de Acceso, Alarmas, etc.)
- ✅ Crea el usuario administrador inicial
- ✅ Configura índices de numeración automática

**Tablas que se crean:**
- `user` - Gestión de usuarios del sistema
- `rol` - Roles y permisos
- `cliente` - Información de clientes
- `sede` - Sedes de los clientes
- `sistema` - Catálogo de sistemas tecnológicos
- `incidencia` - Registro de incidencias
- `indice` - Sistema de numeración automática
- `plantilla_informe` - Plantillas para generación de informes

#### 6. Ejecutar el Sistema

```bash
# Ejecutar la aplicación
python ejecutar_app.py
```

#### 7. Acceder al Sistema

1. Abre tu navegador web
2. Ve a la dirección: `http://localhost:5000`
3. Inicia sesión con las credenciales configuradas en el archivo `.env`

## 🔧 Solución de Problemas

### Error: "Import reportlab not found"

**Causa**: ReportLab no está instalado correctamente

**Solución**:
```bash
# Verificar entorno virtual activado
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Reinstalar ReportLab
pip uninstall reportlab
pip install reportlab==4.0.4

# Verificar instalación
python -c "import reportlab; print('ReportLab version:', reportlab.Version)"
```

### Error: "Import PIL not found"

**Causa**: Pillow no está instalado correctamente

**Solución**:
```bash
pip uninstall Pillow
pip install Pillow==11.3.0

# Verificar instalación
python -c "import PIL; print('Pillow version:', PIL.__version__)"
```

### Error: "Table 'erp_bacs.user' doesn't exist"

**Causa**: No se ejecutó la migración de la base de datos

**Solución**:
```bash
python migrar_db.py
```

### Error de conexión a MySQL

**Causa**: MySQL no está ejecutándose o credenciales incorrectas

**Solución**:
1. Verifica que MySQL esté ejecutándose
2. Verifica las credenciales en el archivo `.env`
3. Verifica que la base de datos `erp_bacs` exista

### Error: "image file is truncated" en firmas

**Causa**: Imagen de firma corrupta o incompleta

**Solución**: Este error ahora está manejado automáticamente por el sistema:
- El sistema intentará múltiples métodos de procesamiento
- Si todo falla, creará una imagen placeholder
- Los datos del firmante siempre se mostrarán

### Configuración de VS Code/PyCharm

#### Para VS Code:
1. Abre la paleta de comandos (`Ctrl+Shift+P`)
2. Escribe "Python: Select Interpreter"
3. Selecciona el intérprete del entorno virtual: `./venv/Scripts/python.exe`

#### Para PyCharm:
1. Ve a File → Settings → Project → Python Interpreter
2. Selecciona el intérprete del entorno virtual

## 📊 Características del Sistema

### Gestión de Usuarios
- ✅ Sistema completo de registro con validación
- ✅ Login seguro con hash de contraseñas
- ✅ Roles y permisos (Administrador, Técnico, Usuario)
- ✅ Gestión de perfiles

### Gestión de Clientes
- ✅ Registro completo de empresas cliente
- ✅ Gestión de múltiples sedes por cliente
- ✅ Información detallada de contactos
- ✅ Control de estado activo/inactivo

### Gestión de Incidencias
- ✅ Creación de incidencias con formulario completo
- ✅ Numeración automática única
- ✅ Asignación de técnicos
- ✅ Estados de seguimiento (Abierta, En Proceso, Cerrada)
- ✅ Sistema de adjuntos

### Gestión de Sistemas
- ✅ Catálogo de sistemas tecnológicos
- ✅ Categorización y organización
- ✅ Control de estado activo/inactivo

### Generación de Informes
- ✅ Informes estructurados en PDF
- ✅ Plantillas personalizables
- ✅ Exportación de datos
- ✅ **Sistema de firmas digitales** con canvas táctil
- ✅ **Datos del firmante** (nombre, documento, empresa, cargo)

### Formularios Dinámicos
- ✅ **Creación de formularios personalizados**
- ✅ **Campos de firma digital** con mouse y táctil
- ✅ **Campos de fotos múltiples**
- ✅ **Campos de texto, fechas, selección**
- ✅ **Generación automática de PDFs**
- ✅ **Datos del firmante incluidos en PDFs**

## 🛠️ Tecnologías Utilizadas

### Backend
- **Python 3.8+** - Lenguaje principal
- **Flask 2.3.3** - Framework web
- **SQLAlchemy 3.0.5** - ORM para base de datos
- **MySQL** - Base de datos relacional
- **ReportLab 4.0.4** - Generación de PDFs
- **Pillow 11.3.0** - Procesamiento de imágenes

### Frontend
- **HTML5 + CSS3 + JavaScript** - Interfaz de usuario
- **Canvas API** - Firmas digitales
- **Responsive Design** - Adaptable a móviles

### Seguridad
- **Flask-Login** - Autenticación
- **bcrypt** - Hash de contraseñas
- **Flask-WTF** - Protección CSRF
- **Validación de archivos** - Sanitización de uploads

## 📁 Estructura del Proyecto

```
erp_bacs/
├── app.py                     # Aplicación principal Flask
├── config.py                  # Configuración del sistema
├── ejecutar_app.py           # Script de ejecución
├── migrar_db.py              # Migración de base de datos
├── setup_completo.py         # Setup automático completo
├── requirements.txt          # Dependencias Python
├── env_example.txt           # Ejemplo de variables de entorno
├── static/                   # Archivos estáticos
│   └── css/
│       └── style.css         # Estilos principales
├── templates/                # Plantillas HTML
│   ├── base.html             # Plantilla base
│   ├── login.html            # Página de login
│   ├── dashboard.html        # Panel principal
│   ├── diligenciar_formulario.html  # Formularios con firmas
│   └── ...                   # Otras plantillas
├── uploads/                  # Archivos subidos
│   ├── logos/                # Logos de clientes
│   └── formularios/          # PDFs de formularios
└── venv/                     # Entorno virtual Python
```

## 🚀 Comandos Útiles

### Desarrollo
```bash
# Activar entorno virtual
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Ejecutar aplicación
python ejecutar_app.py

# Ejecutar migración
python migrar_db.py

# Setup completo
python setup_completo.py
```

### Mantenimiento
```bash
# Actualizar dependencias
pip install --upgrade -r requirements.txt

# Verificar dependencias
pip list

# Limpiar caché
pip cache purge
```

### Base de Datos
```bash
# Backup de base de datos
mysqldump -u usuario -p erp_bacs > backup_erp_bacs.sql

# Restaurar backup
mysql -u usuario -p erp_bacs < backup_erp_bacs.sql
```

## 📞 Soporte y Contacto

Para soporte técnico o consultas sobre el sistema, contacta al equipo de desarrollo de BACS.

---

**Desarrollado por**: Equipo de Desarrollo BACS  
**Versión**: 1.0  
**Última actualización**: Diciembre 2024