# ERP BACS - Sistema de Gestión de Incidencias

## 📋 Descripción del Sistema

El ERP BACS es un sistema de gestión empresarial desarrollado específicamente para la empresa BACS (Building Automation and Control System SAS). Este sistema permite la gestión integral de incidencias técnicas, clientes, usuarios, sedes y sistemas, proporcionando una plataforma centralizada para el seguimiento y resolución de problemas técnicos.

## 🚀 Instalación y Configuración

### Requisitos Previos

Antes de instalar el sistema, asegúrate de tener instalado en tu computadora:

1. **Python 3.8 o superior** - Descárgalo desde [python.org](https://www.python.org/downloads/)
2. **MySQL Server** - Descárgalo desde [mysql.com](https://dev.mysql.com/downloads/mysql/)
3. **Git** (opcional) - Para clonar el repositorio desde [git-scm.com](https://git-scm.com/downloads)

### Paso a Paso para Poner en Funcionamiento

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
# Instalar todas las librerías necesarias
pip install -r requirements.txt
```

#### 3. Configurar la Base de Datos MySQL

1. Abre MySQL Workbench o tu cliente MySQL preferido
2. Crea una nueva base de datos llamada `erp_bacs`:
   ```sql
   CREATE DATABASE erp_bacs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

#### 4. Configurar Variables de Entorno

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

# Usuario inicial del sistema
INITIAL_USER_EMAIL=tu_email@empresa.com
INITIAL_USER_PASSWORD=tu_contraseña_segura
```

#### 5. Ejecutar el Sistema

```bash
# Ejecutar la aplicación
python ejecutar_app.py
```

#### 6. Acceder al Sistema

1. Abre tu navegador web
2. Ve a la dirección: `http://localhost:5000`
3. Inicia sesión con las credenciales configuradas en el archivo `.env`

## 📊 Análisis de Requerimientos del Sistema

### Requerimientos Funcionales

#### 1. Gestión de Usuarios
- **Registro de usuarios**: Sistema completo de registro con validación de datos
- **Autenticación**: Login seguro con hash de contraseñas
- **Roles y permisos**: Sistema de roles (Administrador, Técnico, Usuario)
- **Gestión de perfiles**: Edición de datos personales y profesionales

#### 2. Gestión de Clientes
- **Registro de clientes**: Información completa de empresas cliente
- **Gestión de sedes**: Cada cliente puede tener múltiples sedes
- **Datos de contacto**: Información detallada de contactos principales
- **Estado activo/inactivo**: Control de clientes activos en el sistema

#### 3. Gestión de Incidencias
- **Creación de incidencias**: Formulario completo con todos los datos necesarios
- **Numeración automática**: Sistema de índices para numeración única
- **Asignación de técnicos**: Asignación automática o manual de técnicos
- **Estados de incidencia**: Seguimiento del progreso (Abierta, En Proceso, Cerrada)
- **Adjuntos**: Subida de archivos relacionados con la incidencia

#### 4. Gestión de Sistemas
- **Catálogo de sistemas**: Registro de todos los sistemas tecnológicos
- **Categorización**: Organización por tipos de sistemas
- **Estado activo/inactivo**: Control de sistemas en uso

#### 5. Generación de Informes
- **Informes estructurados**: Generación de PDFs con datos de incidencias
- **Plantillas personalizables**: Sistema de plantillas para diferentes tipos de informes
- **Exportación**: Descarga de informes en formato PDF

### Requerimientos No Funcionales

#### 1. Seguridad
- **Autenticación obligatoria**: Todas las rutas protegidas requieren login
- **Hash de contraseñas**: Uso de bcrypt para seguridad de contraseñas
- **Validación de datos**: Validación tanto en frontend como backend
- **Sanitización de archivos**: Validación de tipos y tamaños de archivos

#### 2. Usabilidad
- **Interfaz intuitiva**: Diseño limpio y fácil de usar
- **Navegación clara**: Menú de navegación organizado por módulos
- **Responsive design**: Adaptable a diferentes tamaños de pantalla
- **Mensajes informativos**: Feedback claro al usuario sobre acciones realizadas

#### 3. Rendimiento
- **Carga rápida**: Optimización de consultas a base de datos
- **Paginación**: Manejo eficiente de grandes volúmenes de datos
- **Caché de archivos**: Servicio optimizado de archivos estáticos

#### 4. Escalabilidad
- **Arquitectura modular**: Separación clara de responsabilidades
- **Base de datos relacional**: Estructura normalizada para crecimiento
- **API REST**: Preparado para futuras integraciones

### Variables del Sistema

#### Variables de Configuración
- `SECRET_KEY`: Clave secreta para sesiones seguras
- `SQLALCHEMY_DATABASE_URI`: Cadena de conexión a MySQL
- `UPLOAD_FOLDER`: Directorio para archivos subidos
- `MAX_CONTENT_LENGTH`: Límite de tamaño de archivos (16MB)

#### Variables de Entorno
- `DB_HOST`: Servidor de base de datos
- `DB_USER`: Usuario de base de datos
- `DB_PASSWORD`: Contraseña de base de datos
- `DB_NAME`: Nombre de la base de datos
- `INITIAL_USER_EMAIL`: Email del usuario administrador inicial
- `INITIAL_USER_PASSWORD`: Contraseña del usuario administrador inicial

### Permisos y Roles

#### Rol Administrador
- Acceso completo a todas las funcionalidades
- Gestión de usuarios, roles y permisos
- Configuración del sistema
- Acceso a todos los informes y estadísticas

#### Rol Técnico
- Gestión de incidencias asignadas
- Actualización de estados de incidencias
- Acceso a información de clientes y sistemas
- Generación de informes técnicos

#### Rol Usuario
- Creación de nuevas incidencias
- Consulta de incidencias propias
- Acceso limitado a información de clientes

### Módulos del Sistema

#### 1. Módulo de Autenticación
- Login/logout de usuarios
- Gestión de sesiones
- Protección de rutas

#### 2. Módulo de Gestión de Usuarios
- CRUD completo de usuarios
- Asignación de roles
- Gestión de perfiles

#### 3. Módulo de Gestión de Clientes
- CRUD de clientes
- Gestión de sedes por cliente
- Información de contacto

#### 4. Módulo de Gestión de Incidencias
- Creación y edición de incidencias
- Asignación de técnicos
- Seguimiento de estados
- Gestión de adjuntos

#### 5. Módulo de Gestión de Sistemas
- Catálogo de sistemas tecnológicos
- Categorización y organización

#### 6. Módulo de Informes
- Generación de PDFs
- Plantillas personalizables
- Exportación de datos

## 🛠️ Metodología y Tecnologías Utilizadas

### Lenguaje de Programación: Python

**¿Por qué Python?**
- **Compatibilidad empresarial**: La empresa cliente (BACS) tiene múltiples desarrollos existentes en Python que desea integrar en esta plataforma a futuro
- **Simplicidad**: Sintaxis clara y fácil de mantener
- **Ecosistema robusto**: Amplia gama de librerías disponibles
- **Escalabilidad**: Ideal para aplicaciones empresariales
- **Comunidad activa**: Gran soporte y documentación

### Framework Web: Flask

**¿Por qué Flask?**
- **Flexibilidad**: Framework minimalista que permite personalización total
- **Rápido desarrollo**: Ideal para prototipos y aplicaciones medianas
- **Extensibilidad**: Fácil integración con otras librerías
- **Documentación excelente**: Curva de aprendizaje suave
- **Comunidad activa**: Gran cantidad de extensiones disponibles

### Base de Datos: MySQL

**¿Por qué MySQL?**
- **Confiabilidad**: Base de datos probada en entornos empresariales
- **Rendimiento**: Excelente para aplicaciones web
- **Escalabilidad**: Soporta grandes volúmenes de datos
- **Compatibilidad**: Amplio soporte en hosting y servidores
- **Herramientas**: Excelentes herramientas de administración

### ORM: SQLAlchemy

**¿Por qué SQLAlchemy?**
- **Abstracción**: Permite trabajar con objetos Python en lugar de SQL directo
- **Portabilidad**: Fácil migración entre diferentes bases de datos
- **Relaciones**: Manejo automático de relaciones entre tablas
- **Migraciones**: Sistema robusto de migraciones de esquema
- **Performance**: Optimización automática de consultas

### Autenticación: Flask-Login

**¿Por qué Flask-Login?**
- **Simplicidad**: Manejo fácil de sesiones de usuario
- **Seguridad**: Protección automática de rutas
- **Flexibilidad**: Personalizable según necesidades
- **Integración**: Perfecta integración con Flask

### Formularios: Flask-WTF + WTForms

**¿Por qué Flask-WTF + WTForms?**
- **Validación**: Validación automática de formularios
- **Seguridad**: Protección CSRF integrada
- **Templates**: Integración perfecta con Jinja2
- **Flexibilidad**: Campos personalizables y validadores

### Generación de PDFs: ReportLab

**¿Por qué ReportLab?**
- **Profesional**: Generación de PDFs de alta calidad
- **Flexibilidad**: Control total sobre diseño y contenido
- **Imágenes**: Soporte completo para imágenes y gráficos
- **Tablas**: Generación avanzada de tablas y datos estructurados

### Procesamiento de Imágenes: Pillow (PIL)

**¿Por qué Pillow?**
- **Versatilidad**: Soporte para múltiples formatos de imagen
- **Optimización**: Redimensionamiento y compresión de imágenes
- **Integración**: Perfecta integración con ReportLab
- **Estabilidad**: Librería madura y confiable

### Seguridad: Werkzeug + bcrypt

**¿Por qué Werkzeug + bcrypt?**
- **Hash seguro**: Algoritmo bcrypt para contraseñas
- **Utilidades**: Funciones de seguridad integradas
- **Validación**: Validación de archivos y datos
- **Estándar**: Librerías estándar en el ecosistema Flask

### Frontend: HTML5 + CSS3 + JavaScript

**¿Por qué tecnologías web estándar?**
- **Compatibilidad**: Funciona en todos los navegadores modernos
- **Mantenimiento**: Fácil de mantener y actualizar
- **Performance**: Carga rápida y responsiva
- **Accesibilidad**: Cumple estándares web

### Template Engine: Jinja2

**¿Por qué Jinja2?**
- **Integración**: Motor de templates oficial de Flask
- **Flexibilidad**: Sintaxis potente y expresiva
- **Herencia**: Sistema de herencia de templates
- **Filtros**: Amplia gama de filtros disponibles

### Gestión de Dependencias: pip + requirements.txt

**¿Por qué pip + requirements.txt?**
- **Simplicidad**: Gestión simple de dependencias
- **Reproducibilidad**: Versiones exactas para entornos consistentes
- **Estándar**: Herramienta estándar de Python
- **Virtualenv**: Compatible con entornos virtuales

### Estructura del Proyecto

```
erp_bacs/
├── app.py                 # Aplicación principal Flask
├── config.py              # Configuración del sistema
├── ejecutar_app.py        # Script de ejecución
├── requirements.txt       # Dependencias Python
├── env_example.txt        # Ejemplo de variables de entorno
├── static/                # Archivos estáticos (CSS, JS, imágenes)
│   └── css/
│       └── style.css      # Estilos principales
├── templates/             # Plantillas HTML
│   ├── base.html          # Plantilla base
│   ├── login.html         # Página de login
│   ├── dashboard.html     # Panel principal
│   ├── usuarios.html      # Gestión de usuarios
│   ├── clientes.html      # Gestión de clientes
│   ├── incidencias.html   # Gestión de incidencias
│   └── ...                # Otras plantillas
├── uploads/               # Archivos subidos por usuarios
│   └── logos/             # Logos de clientes
├── files/                 # Archivos del sistema
│   └── logo.jpg           # Logo principal
└── venv/                  # Entorno virtual Python
```

### Patrones de Diseño Utilizados

#### 1. Modelo-Vista-Controlador (MVC)
- **Modelos**: Clases SQLAlchemy para representar datos
- **Vistas**: Templates HTML con Jinja2
- **Controladores**: Rutas Flask que manejan la lógica

#### 2. Factory Pattern
- Configuración centralizada en `config.py`
- Inicialización de extensiones Flask

#### 3. Repository Pattern
- Acceso a datos encapsulado en modelos SQLAlchemy
- Separación entre lógica de negocio y acceso a datos

#### 4. Decorator Pattern
- `@login_required` para protección de rutas
- `@app.route` para definición de endpoints

### Metodología de Desarrollo

#### 1. Desarrollo Iterativo
- Prototipado rápido con Flask
- Iteraciones basadas en feedback del cliente
- Desarrollo incremental de funcionalidades

#### 2. Desarrollo Orientado a Objetos
- Modelos de datos como clases Python
- Encapsulación de lógica de negocio
- Herencia y polimorfismo donde corresponde

#### 3. Principios SOLID
- **Single Responsibility**: Cada clase tiene una responsabilidad específica
- **Open/Closed**: Extensible sin modificar código existente
- **Liskov Substitution**: Interfaces consistentes
- **Interface Segregation**: Interfaces específicas
- **Dependency Inversion**: Dependencias de abstracciones

#### 4. Clean Code
- Nombres descriptivos para variables y funciones
- Funciones pequeñas y específicas
- Comentarios donde es necesario
- Código autodocumentado

### Consideraciones de Seguridad

#### 1. Autenticación y Autorización
- Hash seguro de contraseñas con bcrypt
- Sesiones seguras con Flask-Login
- Protección CSRF en formularios

#### 2. Validación de Datos
- Validación en frontend (JavaScript)
- Validación en backend (Python/WTForms)
- Sanitización de entradas de usuario

#### 3. Gestión de Archivos
- Validación de tipos de archivo
- Límites de tamaño
- Nombres de archivo seguros

#### 4. Base de Datos
- Consultas parametrizadas (SQLAlchemy ORM)
- Validación de datos a nivel de modelo
- Índices para optimización

### Escalabilidad y Mantenimiento

#### 1. Arquitectura Modular
- Separación clara de responsabilidades
- Fácil adición de nuevas funcionalidades
- Reutilización de código

#### 2. Base de Datos Normalizada
- Estructura relacional optimizada
- Índices para consultas frecuentes
- Migraciones para cambios de esquema

#### 3. Código Documentado
- Comentarios en funciones críticas
- Docstrings en clases principales
- README completo para nuevos desarrolladores

#### 4. Testing y Debugging
- Modo debug de Flask para desarrollo
- Logging integrado para monitoreo
- Manejo de errores con try/catch

## 📞 Soporte y Contacto

Para soporte técnico o consultas sobre el sistema, contacta al equipo de desarrollo de BACS.

---

**Desarrollado por**: Equipo de Desarrollo BACS  
**Versión**: 1.0  
**Última actualización**: Diciembre 2024