from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import csv
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from PIL import Image as PILImage
import io

from config import Config


app = Flask(__name__)
app.config.from_object(Config)

# Filtro personalizado para parsear JSON en plantillas
@app.template_filter('from_json')
def from_json(json_string):
    if not json_string:
        return {}
    try:
        return json.loads(json_string)
    except:
        return {}

# Inicializar extensiones
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'

# Crear directorio de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Crear directorio de files si no existe
os.makedirs('files', exist_ok=True)

# Ruta para servir archivos estáticos desde la carpeta files
@app.route('/files/<filename>')
def serve_file(filename):
    return send_file(f'files/{filename}')

# Modelos de la base de datos
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo_documento = db.Column(db.String(20), nullable=False)
    numero_documento = db.Column(db.String(20), unique=True, nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    rol = db.relationship('Rol', backref='usuarios')
    incidencias_creadas = db.relationship('Incidencia', foreign_keys='Incidencia.creado_por', backref='usuario_creador', overlaps="incidencias_creador")
    incidencias_asignadas = db.relationship('Incidencia', foreign_keys='Incidencia.tecnico_asignado', backref='usuario_tecnico', overlaps="incidencias_tecnico")

class Rol(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    
    def __init__(self, nombre, descripcion=""):
        self.nombre = nombre
        self.descripcion = descripcion

class Indice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prefijo = db.Column(db.String(10), nullable=False)
    numero_actual = db.Column(db.Integer, default=0)
    formato = db.Column(db.String(20), default="000000")  # Para el formato de numeración
    
    def generar_siguiente(self):
        self.numero_actual += 1
        return f"{self.prefijo}_{self.numero_actual:06d}"

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    tipo_documento = db.Column(db.String(20), nullable=False)
    numero_documento = db.Column(db.String(20), unique=True, nullable=False)
    correo = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    direccion = db.Column(db.Text)
    contacto_principal = db.Column(db.String(100))
    cargo_contacto = db.Column(db.String(100))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    sedes = db.relationship('Sede', backref='cliente', cascade='all, delete-orphan')
    incidencias = db.relationship('Incidencia', back_populates='cliente')

class Sede(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    direccion = db.Column(db.Text)
    telefono = db.Column(db.String(20))
    correo = db.Column(db.String(120))
    contacto_responsable = db.Column(db.String(100))
    cargo_responsable = db.Column(db.String(100))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    incidencias = db.relationship('Incidencia', back_populates='sede')

class Sistema(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    incidencias = db.relationship('Incidencia', back_populates='sistema')
    
    def __init__(self, nombre, descripcion=""):
        self.nombre = nombre
        self.descripcion = descripcion


class Incidencia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    indice = db.Column(db.String(20), unique=True, nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_cambio_estado = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='Abierta')
    tecnico_asignado = db.Column(db.Integer, db.ForeignKey('user.id'))
    creado_por = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    sistema_id = db.Column(db.Integer, db.ForeignKey('sistema.id'), nullable=False, default=1)
    adjuntos = db.Column(db.Text)  # JSON string con nombres de archivos
    titulos_imagenes = db.Column(db.Text)  # JSON string con títulos de imágenes
    configuracion_imagenes = db.Column(db.Text)  # JSON con configuración de imágenes y collages
    
    # Relaciones
    tecnico = db.relationship('User', foreign_keys=[tecnico_asignado], backref='incidencias_tecnico', overlaps="incidencias_asignadas,usuario_tecnico")
    creador = db.relationship('User', foreign_keys=[creado_por], backref='incidencias_creador', overlaps="incidencias_creadas,usuario_creador")
    cliente = db.relationship('Cliente', back_populates='incidencias')
    sede = db.relationship('Sede', back_populates='incidencias')
    sistema = db.relationship('Sistema', back_populates='incidencias')

# ==================== MODELOS DE FORMULARIOS DINÁMICOS ====================

class Formulario(db.Model):
    """Modelo para plantillas de formularios creadas por administradores"""
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    creado_por = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relaciones
    creador = db.relationship('User', backref='formularios_creados')
    campos = db.relationship('CampoFormulario', backref='formulario', cascade='all, delete-orphan', order_by='CampoFormulario.orden')
    respuestas = db.relationship('RespuestaFormulario', backref='formulario', cascade='all, delete-orphan')

class CampoFormulario(db.Model):
    """Modelo para los campos individuales de un formulario"""
    id = db.Column(db.Integer, primary_key=True)
    formulario_id = db.Column(db.Integer, db.ForeignKey('formulario.id'), nullable=False)
    tipo_campo = db.Column(db.String(50), nullable=False)  # texto, textarea, fecha, seleccion, seleccion_multiple, firma, foto, texto_informativo
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    obligatorio = db.Column(db.Boolean, default=False)
    orden = db.Column(db.Integer, default=0)
    configuracion = db.Column(db.Text)  # JSON con configuración específica del campo (opciones, validaciones, etc.)
    
    # Relaciones
    respuestas = db.relationship('RespuestaCampo', backref='campo', cascade='all, delete-orphan')

class RespuestaFormulario(db.Model):
    """Modelo para las respuestas completadas de un formulario"""
    id = db.Column(db.Integer, primary_key=True)
    formulario_id = db.Column(db.Integer, db.ForeignKey('formulario.id'), nullable=False)
    diligenciado_por = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    fecha_diligenciamiento = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='Completado')  # Completado, Borrador
    archivo_pdf = db.Column(db.String(500))  # Ruta del PDF generado
    
    # Relaciones
    usuario = db.relationship('User', backref='formularios_diligenciados')
    respuestas_campos = db.relationship('RespuestaCampo', backref='respuesta_formulario', cascade='all, delete-orphan')

class RespuestaCampo(db.Model):
    """Modelo para las respuestas individuales de cada campo"""
    id = db.Column(db.Integer, primary_key=True)
    respuesta_formulario_id = db.Column(db.Integer, db.ForeignKey('respuesta_formulario.id'), nullable=False)
    campo_id = db.Column(db.Integer, db.ForeignKey('campo_formulario.id'), nullable=False)
    valor_texto = db.Column(db.Text)
    valor_fecha = db.Column(db.DateTime)
    valor_archivo = db.Column(db.String(500))  # Para firmas, fotos, etc.
    valor_json = db.Column(db.Text)  # Para selecciones múltiples y otros datos complejos
    # Campos adicionales para firmas
    nombre_firmante = db.Column(db.String(100))
    documento_firmante = db.Column(db.String(20))
    telefono_firmante = db.Column(db.String(20))
    empresa_firmante = db.Column(db.String(100))
    cargo_firmante = db.Column(db.String(100))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Función helper para obtener incidencias según el rol del usuario
def obtener_incidencias_por_rol():
    """Retorna las incidencias filtradas según el rol del usuario actual"""
    if current_user.rol.nombre in ['Administrador', 'Coordinador']:
        # Admin y Coordinador ven todas las incidencias
        return Incidencia.query
    else:
        # Técnicos solo ven las incidencias asignadas a ellos
        return Incidencia.query.filter_by(tecnico_asignado=current_user.id)

# Función helper para obtener el logo con proporciones correctas
def obtener_logo_pdf(max_width=100, max_height=50):
    """Retorna el logo para PDF manteniendo la relación 1:1"""
    logo_path = 'files/logo.jpg'
    if os.path.exists(logo_path):
        try:
            # Obtener dimensiones reales de la imagen
            from PIL import Image as PILImage
            with PILImage.open(logo_path) as img:
                original_width, original_height = img.size
            
            # Calcular dimensiones manteniendo proporción 1:1
            if original_width >= original_height:
                # Imagen más ancha que alta
                width = min(max_width, original_width)
                height = int(width * original_height / original_width)
            else:
                # Imagen más alta que ancha
                height = min(max_height, original_height)
                width = int(height * original_width / original_height)
            
            # Crear imagen de ReportLab
            logo_img = Image(logo_path, width=width, height=height)
            return logo_img
        except Exception as e:
            print(f"Error cargando logo: {e}")
            return ''
    return ''

# Rutas principales
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']
        user = User.query.filter_by(correo=correo).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales incorrectas', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Obtener consulta base filtrada por rol
    incidencias_query = obtener_incidencias_por_rol()
    
    # Estadísticas para el dashboard
    total_incidencias = incidencias_query.count()
    incidencias_abiertas = incidencias_query.filter_by(estado='Abierta').count()
    incidencias_proceso = incidencias_query.filter_by(estado='En proceso').count()
    incidencias_cerradas = incidencias_query.filter_by(estado='Cerrada').count()
    
    # Incidencias recientes
    incidencias_recientes = incidencias_query.order_by(Incidencia.fecha_inicio.desc()).limit(5).all()
    
    stats = {
        'total': total_incidencias,
        'abiertas': incidencias_abiertas,
        'proceso': incidencias_proceso,
        'cerradas': incidencias_cerradas
    }
    
    return render_template('dashboard.html', stats=stats, incidencias_recientes=incidencias_recientes)

@app.route('/incidencias')
@login_required
def incidencias():
    page = request.args.get('page', 1, type=int)
    # Obtener consulta base filtrada por rol
    incidencias_query = obtener_incidencias_por_rol()
    incidencias = incidencias_query.order_by(Incidencia.fecha_inicio.desc()).paginate(
        page=page, per_page=10, error_out=False)
    return render_template('incidencias.html', incidencias=incidencias)

@app.route('/incidencias/nueva', methods=['GET', 'POST'])
@login_required
def nueva_incidencia():
    if request.method == 'POST':
        # Obtener el índice seleccionado
        indice_id = request.form.get('indice_id')
        if not indice_id:
            flash('Debe seleccionar un índice', 'error')
            return redirect(url_for('nueva_incidencia'))
        
        indice_obj = Indice.query.get(int(indice_id))
        if not indice_obj:
            flash('El índice seleccionado no existe', 'error')
            return redirect(url_for('nueva_incidencia'))
        
        nuevo_indice = indice_obj.generar_siguiente()
        
        # Crear nueva incidencia
        incidencia = Incidencia(
            indice=nuevo_indice,
            titulo=request.form['titulo'],
            descripcion=request.form['descripcion'],
            cliente_id=int(request.form['cliente_id']),
            sede_id=int(request.form['sede_id']),
            sistema_id=int(request.form['sistema_id']),
            creado_por=current_user.id
        )
        
        # Asignar técnico si es administrador o coordinador
        if current_user.rol.nombre in ['Administrador', 'Coordinador']:
            tecnico_id = request.form.get('tecnico_asignado')
            if tecnico_id:
                incidencia.tecnico_asignado = int(tecnico_id)
            # Si no se selecciona técnico, queda como None (sin asignar)
        
        # Manejar archivos adjuntos y configuración de imágenes
        archivos = request.files.getlist('adjuntos')
        titulos_imagenes = request.form.getlist('titulos_imagenes')
        
        nombres_archivos = []
        titulos_finales = []
        configuracion_imagenes = {
            'imagenes_individuales': [],
            'collages': []
        }
        
        # Procesar archivos
        for i, archivo in enumerate(archivos):
            if archivo and archivo.filename:
                filename = secure_filename(archivo.filename)
                archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                nombres_archivos.append(filename)
                
                # Obtener título correspondiente o usar nombre del archivo
                titulo = titulos_imagenes[i] if i < len(titulos_imagenes) and titulos_imagenes[i] else filename
                titulos_finales.append(titulo)
        
        # Procesar configuración de imágenes
        if nombres_archivos:
            # Procesar imágenes individuales
            for i, archivo in enumerate(nombres_archivos):
                modo_key = f'modo_{i}'
                modo = request.form.get(modo_key, 'individual')
                
                if modo == 'individual':
                    configuracion_imagenes['imagenes_individuales'].append({
                        'archivo': archivo,
                        'titulo': titulos_finales[i] if i < len(titulos_finales) else archivo
                    })
            
            # Procesar collages
            collage_keys = [key for key in request.form.keys() if key.startswith('titulo_collage_')]
            for key in collage_keys:
                collage_num = key.split('_')[2]
                titulo_collage = request.form.get(key, '')
                imagenes_collage = request.form.getlist(f'imagenes_collage_{collage_num}')
                
                if titulo_collage and imagenes_collage:
                    configuracion_imagenes['collages'].append({
                        'titulo': titulo_collage,
                        'imagenes': imagenes_collage
                    })
        
        if nombres_archivos:
            incidencia.adjuntos = ','.join(nombres_archivos)
            incidencia.titulos_imagenes = ','.join(titulos_finales)
            incidencia.configuracion_imagenes = json.dumps(configuracion_imagenes)
        
        db.session.add(incidencia)
        db.session.commit()
        
        flash('Incidencia creada exitosamente', 'success')
        return redirect(url_for('incidencias'))
    
    # Obtener clientes, sedes, sistemas e índices para los selects
    clientes = Cliente.query.filter_by(activo=True).all()
    sedes = Sede.query.filter_by(activo=True).all()
    sistemas = Sistema.query.filter_by(activo=True).all()
    tecnicos = User.query.join(Rol).filter(Rol.nombre == 'Técnico').all()
    indices = Indice.query.all()
    
    if not indices:
        flash('No hay índices configurados. Contacte al administrador para crear índices.', 'error')
        return redirect(url_for('incidencias'))
    
    return render_template('nueva_incidencia.html', clientes=clientes, sedes=sedes, sistemas=sistemas, tecnicos=tecnicos, indices=indices)

@app.route('/incidencias/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_incidencia(id):
    incidencia = Incidencia.query.get_or_404(id)
    
    # Verificar permisos
    if current_user.rol.nombre not in ['Administrador', 'Coordinador'] and incidencia.tecnico_asignado != current_user.id:
        flash('No tienes permisos para editar esta incidencia', 'error')
        return redirect(url_for('incidencias'))
    
    if request.method == 'POST':
        incidencia.titulo = request.form['titulo']
        incidencia.descripcion = request.form['descripcion']
        incidencia.cliente_id = int(request.form['cliente_id'])
        incidencia.sede_id = int(request.form['sede_id'])
        incidencia.sistema_id = int(request.form['sistema_id'])
        incidencia.estado = request.form['estado']
        
        # Actualizar fecha de cambio de estado si cambió
        if incidencia.estado != request.form.get('estado_anterior'):
            incidencia.fecha_cambio_estado = datetime.utcnow()
        
        # Asignar técnico si es administrador o coordinador
        if current_user.rol.nombre in ['Administrador', 'Coordinador']:
            tecnico_id = request.form.get('tecnico_asignado')
            if tecnico_id:
                incidencia.tecnico_asignado = int(tecnico_id)
            else:
                # Si no se selecciona técnico (opción "Sin asignar"), desasignar
                incidencia.tecnico_asignado = None
        
        # Manejar archivos adjuntos y títulos
        archivos = request.files.getlist('adjuntos')
        titulos_imagenes = request.form.getlist('titulos_imagenes')
        
        # Si se subieron nuevos archivos, reemplazar los existentes
        if archivos and any(archivo.filename for archivo in archivos):
            nombres_archivos = []
            titulos_finales = []
            
            for i, archivo in enumerate(archivos):
                if archivo and archivo.filename:
                    filename = secure_filename(archivo.filename)
                    archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    nombres_archivos.append(filename)
                    
                    # Obtener título correspondiente o usar nombre del archivo
                    titulo = titulos_imagenes[i] if i < len(titulos_imagenes) and titulos_imagenes[i] else filename
                    titulos_finales.append(titulo)
            
            if nombres_archivos:
                incidencia.adjuntos = ','.join(nombres_archivos)
                incidencia.titulos_imagenes = ','.join(titulos_finales)
        
        db.session.commit()
        flash('Incidencia actualizada exitosamente', 'success')
        return redirect(url_for('incidencias'))
    
    # Obtener técnicos, clientes, sedes y sistemas para los selects
    tecnicos = User.query.filter_by(rol_id=3).all()  # Rol técnico
    clientes = Cliente.query.filter_by(activo=True).all()
    sedes = Sede.query.filter_by(activo=True).all()
    sistemas = Sistema.query.filter_by(activo=True).all()
    
    return render_template('editar_incidencia.html', incidencia=incidencia, tecnicos=tecnicos, clientes=clientes, sedes=sedes, sistemas=sistemas)

@app.route('/usuarios')
@login_required
def usuarios():
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    usuarios = User.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_usuario():
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        usuario = User(
            nombre=request.form['nombre'],
            tipo_documento=request.form['tipo_documento'],
            numero_documento=request.form['numero_documento'],
            telefono=request.form['telefono'],
            correo=request.form['correo'],
            password_hash=generate_password_hash(request.form['password']),
            rol_id=int(request.form['rol_id'])
        )
        
        try:
            db.session.add(usuario)
            db.session.commit()
            flash('Usuario creado exitosamente', 'success')
            return redirect(url_for('usuarios'))
        except Exception as e:
            db.session.rollback()
            flash('Error al crear usuario: ' + str(e), 'error')
    
    roles = Rol.query.all()
    return render_template('nuevo_usuario.html', roles=roles)

@app.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    usuario = User.query.get_or_404(id)
    
    if request.method == 'POST':
        usuario.nombre = request.form['nombre']
        usuario.tipo_documento = request.form['tipo_documento']
        usuario.numero_documento = request.form['numero_documento']
        usuario.telefono = request.form['telefono']
        usuario.correo = request.form['correo']
        usuario.rol_id = int(request.form['rol_id'])
        
        # Solo actualizar contraseña si se proporciona una nueva
        if request.form.get('password'):
            usuario.password_hash = generate_password_hash(request.form['password'])
        
        try:
            db.session.commit()
            flash('Usuario actualizado exitosamente', 'success')
            return redirect(url_for('usuarios'))
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar usuario: ' + str(e), 'error')
    
    roles = Rol.query.all()
    return render_template('editar_usuario.html', usuario=usuario, roles=roles)

@app.route('/eliminar_usuario/<int:id>')
@login_required
def eliminar_usuario(id):
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    usuario = User.query.get_or_404(id)
    
    # No permitir eliminar al usuario actual
    if usuario.id == current_user.id:
        flash('No puedes eliminar tu propio usuario', 'error')
        return redirect(url_for('usuarios'))
    
    # Verificar si el usuario tiene incidencias asociadas
    incidencias_creadas = Incidencia.query.filter_by(creado_por=usuario.id).count()
    incidencias_asignadas = Incidencia.query.filter_by(tecnico_asignado=usuario.id).count()
    
    if incidencias_creadas > 0 or incidencias_asignadas > 0:
        flash(f'No se puede eliminar el usuario porque tiene {incidencias_creadas + incidencias_asignadas} incidencias asociadas', 'error')
        return redirect(url_for('usuarios'))
    
    try:
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuario eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar usuario: ' + str(e), 'error')
    
    return redirect(url_for('usuarios'))

@app.route('/clientes')
@login_required
def clientes():
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    clientes = Cliente.query.filter_by(activo=True).all()
    return render_template('clientes.html', clientes=clientes)

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_cliente():
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        cliente = Cliente(
            nombre=request.form['nombre'],
            tipo_documento=request.form['tipo_documento'],
            numero_documento=request.form['numero_documento'],
            correo=request.form['correo'],
            telefono=request.form['telefono'],
            direccion=request.form['direccion'],
            contacto_principal=request.form['contacto_principal'],
            cargo_contacto=request.form['cargo_contacto']
        )
        
        try:
            db.session.add(cliente)
            db.session.commit()
            flash('Cliente creado exitosamente', 'success')
            return redirect(url_for('clientes'))
        except Exception as e:
            db.session.rollback()
            flash('Error al crear cliente: ' + str(e), 'error')
    
    return render_template('nuevo_cliente.html')

@app.route('/clientes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    cliente = Cliente.query.get_or_404(id)
    
    if request.method == 'POST':
        cliente.nombre = request.form['nombre']
        cliente.tipo_documento = request.form['tipo_documento']
        cliente.numero_documento = request.form['numero_documento']
        cliente.correo = request.form['correo']
        cliente.telefono = request.form['telefono']
        cliente.direccion = request.form['direccion']
        cliente.contacto_principal = request.form['contacto_principal']
        cliente.cargo_contacto = request.form['cargo_contacto']
        
        try:
            db.session.commit()
            flash('Cliente actualizado exitosamente', 'success')
            return redirect(url_for('clientes'))
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar cliente: ' + str(e), 'error')
    
    return render_template('editar_cliente.html', cliente=cliente)

@app.route('/clientes/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_cliente(id):
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    cliente = Cliente.query.get_or_404(id)
    
    # Verificar si tiene incidencias asociadas
    if cliente.incidencias:
        flash('No se puede eliminar el cliente porque tiene incidencias asociadas', 'error')
        return redirect(url_for('clientes'))
    
    try:
        cliente.activo = False
        db.session.commit()
        flash('Cliente eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar cliente: ' + str(e), 'error')
    
    return redirect(url_for('clientes'))

@app.route('/clientes/<int:id>/sedes')
@login_required
def sedes_cliente(id):
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    cliente = Cliente.query.get_or_404(id)
    sedes = Sede.query.filter_by(cliente_id=id, activo=True).all()
    return render_template('sedes_cliente.html', cliente=cliente, sedes=sedes)

@app.route('/clientes/<int:id>/sedes/nueva', methods=['GET', 'POST'])
@login_required
def nueva_sede(id):
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    cliente = Cliente.query.get_or_404(id)
    
    if request.method == 'POST':
        sede = Sede(
            cliente_id=id,
            nombre=request.form['nombre'],
            direccion=request.form['direccion'],
            telefono=request.form['telefono'],
            correo=request.form['correo'],
            contacto_responsable=request.form['contacto_responsable'],
            cargo_responsable=request.form['cargo_responsable']
        )
        
        try:
            db.session.add(sede)
            db.session.commit()
            flash('Sede creada exitosamente', 'success')
            return redirect(url_for('sedes_cliente', id=id))
        except Exception as e:
            db.session.rollback()
            flash('Error al crear sede: ' + str(e), 'error')
    
    return render_template('nueva_sede.html', cliente=cliente)

@app.route('/sedes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_sede(id):
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    sede = Sede.query.get_or_404(id)
    
    if request.method == 'POST':
        sede.nombre = request.form['nombre']
        sede.direccion = request.form['direccion']
        sede.telefono = request.form['telefono']
        sede.correo = request.form['correo']
        sede.contacto_responsable = request.form['contacto_responsable']
        sede.cargo_responsable = request.form['cargo_responsable']
        
        try:
            db.session.commit()
            flash('Sede actualizada exitosamente', 'success')
            return redirect(url_for('sedes_cliente', id=sede.cliente_id))
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar sede: ' + str(e), 'error')
    
    return render_template('editar_sede.html', sede=sede)

@app.route('/sedes/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_sede(id):
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    sede = Sede.query.get_or_404(id)
    cliente_id = sede.cliente_id
    
    # Verificar si tiene incidencias asociadas
    if sede.incidencias:
        flash('No se puede eliminar la sede porque tiene incidencias asociadas', 'error')
        return redirect(url_for('sedes_cliente', id=cliente_id))
    
    try:
        sede.activo = False
        db.session.commit()
        flash('Sede eliminada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar sede: ' + str(e), 'error')
    
    return redirect(url_for('sedes_cliente', id=cliente_id))

@app.route('/informes')
@login_required
def informes():
    if current_user.rol.nombre not in ['Administrador', 'Coordinador']:
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    # Obtener incidencias filtradas por rol
    incidencias_query = obtener_incidencias_por_rol()
    incidencias = incidencias_query.all()
    
    # Datos para filtros
    clientes = Cliente.query.filter_by(activo=True).all()
    sedes = Sede.query.filter_by(activo=True).all()
    sistemas = Sistema.query.filter_by(activo=True).all()
    tecnicos = User.query.all()
    
    return render_template('informes.html', 
                         incidencias=incidencias, 
                         clientes=clientes,
                         sedes=sedes,
                         sistemas=sistemas,
                         tecnicos=tecnicos)

@app.route('/informes/estructurado', methods=['GET', 'POST'])
@login_required
def informe_estructurado():
    if current_user.rol.nombre not in ['Administrador', 'Coordinador']:
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Obtener datos del formulario
        cliente_id = request.form['cliente_id']
        incidencias_ids = request.form.getlist('incidencias')
        
        datos_informe = {
            'cliente': request.form['cliente'],
            'atencion': request.form['atencion'],
            'cargo': request.form['cargo'],
            'alcance': request.form['alcance'],
            'fecha': request.form['fecha'],
            'introduccion': request.form['introduccion'],
            'conclusiones': request.form.get('conclusiones', ''),
            'version': request.form.get('version', '1')
        }
        
        if not incidencias_ids:
            flash('Debe seleccionar al menos una incidencia', 'error')
            return redirect(url_for('informe_estructurado'))
        
        incidencias = Incidencia.query.filter(Incidencia.id.in_(incidencias_ids)).all()
        return generar_pdf_informe_html_format(incidencias, datos_informe)
    
    # Obtener clientes para el formulario
    clientes = Cliente.query.filter_by(activo=True).all()
    return render_template('informe_estructurado.html', clientes=clientes)

@app.route('/informes/descargar', methods=['POST'])
@login_required
def descargar_informe():
    if current_user.rol.nombre not in ['Administrador', 'Coordinador']:
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    formato = request.form['formato']
    incidencias_ids = request.form.getlist('incidencias')
    agrupacion = request.form.get('agrupacion', 'cliente')
    tipo_pdf = request.form.get('tipo_pdf', 'profesional')  # Nuevo parámetro para elegir tipo de PDF
    
    if not incidencias_ids:
        flash('Debe seleccionar al menos una incidencia', 'error')
        return redirect(url_for('informes'))
    
    # Validar que las incidencias seleccionadas estén dentro del rango permitido para el usuario
    incidencias_permitidas_query = obtener_incidencias_por_rol()
    incidencias_permitidas_ids = [inc.id for inc in incidencias_permitidas_query.all()]
    
    # Filtrar solo las incidencias que el usuario puede ver
    incidencias_ids_validas = [id for id in incidencias_ids if int(id) in incidencias_permitidas_ids]
    
    if not incidencias_ids_validas:
        flash('No tiene permisos para generar informes con las incidencias seleccionadas', 'error')
        return redirect(url_for('informes'))
    
    incidencias = Incidencia.query.filter(Incidencia.id.in_(incidencias_ids_validas)).all()
    
    if formato == 'csv':
        return generar_csv(incidencias)
    elif formato == 'pdf':
        # Usar el nuevo formato HTML con datos del formulario
        datos_informe = {
            'cliente': request.form.get('cliente', 'Cliente del Informe'),
            'atencion': request.form.get('atencion', 'Persona de Contacto'),
            'cargo': request.form.get('cargo', 'Cargo del Contacto'),
            'alcance': request.form.get('alcance', 'Alcance del Proyecto'),
            'fecha': datetime.now().strftime('%d/%m/%Y'),
            'introduccion': request.form.get('introduccion', 'Este informe presenta las actividades realizadas durante el período de mantenimiento y soporte técnico.'),
            'conclusiones': request.form.get('conclusiones', 'Se han completado exitosamente todas las actividades programadas.'),
            'version': '1'
        }
        return generar_pdf_informe_html_format(incidencias, datos_informe)
    
    return redirect(url_for('informes'))


@app.route('/sistemas')
@login_required
def sistemas():
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    sistemas = Sistema.query.filter_by(activo=True).all()
    return render_template('sistemas.html', sistemas=sistemas)

@app.route('/sistemas/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_sistema():
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        sistema = Sistema(
            nombre=request.form['nombre'],
            descripcion=request.form['descripcion']
        )
        
        try:
            db.session.add(sistema)
            db.session.commit()
            flash('Sistema creado exitosamente', 'success')
            return redirect(url_for('sistemas'))
        except Exception as e:
            db.session.rollback()
            flash('Error al crear sistema: ' + str(e), 'error')
    
    return render_template('nuevo_sistema.html')

@app.route('/sistemas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_sistema(id):
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    sistema = Sistema.query.get_or_404(id)
    
    if request.method == 'POST':
        sistema.nombre = request.form['nombre']
        sistema.descripcion = request.form['descripcion']
        
        try:
            db.session.commit()
            flash('Sistema actualizado exitosamente', 'success')
            return redirect(url_for('sistemas'))
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar sistema: ' + str(e), 'error')
    
    return render_template('editar_sistema.html', sistema=sistema)

@app.route('/sistemas/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_sistema(id):
    if current_user.rol.nombre != 'Administrador':
        return jsonify({'success': False, 'message': 'No tienes permisos para realizar esta acción'})
    
    sistema = Sistema.query.get_or_404(id)
    
    # Verificar si tiene incidencias asociadas
    if sistema.incidencias:
        return jsonify({'success': False, 'message': 'No se puede eliminar el sistema porque tiene incidencias asociadas'})
    
    try:
        sistema.activo = False
        db.session.commit()
        return jsonify({'success': True, 'message': 'Sistema eliminado exitosamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al eliminar sistema: {str(e)}'})

@app.route('/api/incidencias/cliente/<int:cliente_id>')
@login_required
def api_incidencias_cliente(cliente_id):
    """API para obtener incidencias de un cliente específico"""
    if current_user.rol.nombre not in ['Administrador', 'Coordinador']:
        return jsonify({'error': 'No tienes permisos para acceder a esta información'}), 403
    
    # Obtener incidencias filtradas por rol y cliente
    incidencias_query = obtener_incidencias_por_rol()
    incidencias = incidencias_query.filter_by(cliente_id=cliente_id).all()
    
    incidencias_data = []
    for incidencia in incidencias:
        incidencias_data.append({
            'id': incidencia.id,
            'indice': incidencia.indice,
            'titulo': incidencia.titulo,
            'descripcion': incidencia.descripcion,
            'estado': incidencia.estado,
            'fecha_inicio': incidencia.fecha_inicio.isoformat(),
            'sede_nombre': incidencia.sede.nombre if incidencia.sede else None,
            'sistema_nombre': incidencia.sistema.nombre if incidencia.sistema else None,
            'tecnico_nombre': incidencia.tecnico.nombre if incidencia.tecnico else None
        })
    
    return jsonify(incidencias_data)

def generar_csv(incidencias):
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Encabezados
    writer.writerow(['Índice', 'Título', 'Descripción', 'Cliente', 'Sede', 'Estado', 
                    'Fecha Inicio', 'Fecha Cambio Estado', 'Técnico Asignado', 'Creado Por'])
    
    # Datos
    for incidencia in incidencias:
        tecnico_nombre = incidencia.tecnico.nombre if incidencia.tecnico else 'Sin asignar'
        creador_nombre = incidencia.creador.nombre if incidencia.creador else 'N/A'
        
        writer.writerow([
            incidencia.indice,
            incidencia.titulo,
            incidencia.descripcion,
            incidencia.cliente.nombre if incidencia.cliente else 'N/A',
            incidencia.sede.nombre if incidencia.sede else 'N/A',
            incidencia.estado,
            incidencia.fecha_inicio.strftime('%Y-%m-%d %H:%M'),
            incidencia.fecha_cambio_estado.strftime('%Y-%m-%d %H:%M'),
            tecnico_nombre,
            creador_nombre
        ])
    
    output.seek(0)
    csv_content = output.getvalue()
    
    # Codificar con UTF-8 BOM para compatibilidad con Excel
    csv_bytes = csv_content.encode('utf-8-sig')
    
    return send_file(
        io.BytesIO(csv_bytes),
        mimetype='text/csv; charset=utf-8',
        as_attachment=True,
        download_name=f'informe_incidencias_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    )

def generar_pdf_profesional(incidencias, agrupacion='estado'):
    buffer = io.BytesIO()
    
    # Configuración de página A4
    from reportlab.lib.pagesizes import A4
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                          leftMargin=50, rightMargin=50,
                          topMargin=50, bottomMargin=50)
    
    styles = getSampleStyleSheet()
    story = []
    
    # Crear estilos personalizados más elegantes
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=20,
        alignment=1,  # Centrado
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica-Bold'
    )
    
    empresa_style = ParagraphStyle(
        'EmpresaStyle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=1,  # Centrado
        textColor=colors.HexColor('#7f8c8d'),
        fontName='Helvetica'
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=2,  # Derecha
        textColor=colors.HexColor('#34495e'),
        fontName='Helvetica'
    )
    
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=15,
        spaceBefore=25,
        textColor=colors.white,
        fontName='Helvetica-Bold',
        alignment=1,  # Centrado
        backColor=colors.HexColor('#3498db'),
        borderPadding=10,
        borderWidth=1,
        borderColor=colors.HexColor('#2980b9')
    )
    
    subsection_style = ParagraphStyle(
        'SubsectionStyle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica-Bold',
        leftIndent=0,
        backColor=colors.HexColor('#ecf0f1'),
        borderPadding=8,
        borderWidth=1,
        borderColor=colors.HexColor('#bdc3c7')
    )
    
    incidencia_style = ParagraphStyle(
        'IncidenciaStyle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica',
        leftIndent=0,
        textColor=colors.HexColor('#2c3e50')
    )
    
    caption_style = ParagraphStyle(
        'CaptionStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#7f8c8d'),
        fontName='Helvetica-Italic',
        alignment=1  # Centrado
    )
    
    # Crear encabezado profesional mejorado
    titulo = 'INFORME DE ACTIVIDADES'
    empresa_nombre = 'BUILDING AUTOMATION AND CONTROL SYSTEM'
    version = '1.0'
    fecha_actual = datetime.now().strftime('%d/%m/%Y')
    
    # Crear el encabezado con diseño mejorado
    header_data = []
    
    # Agregar logo si existe
    logo_cell = obtener_logo_pdf(max_width=100, max_height=50)
    
    # Diseño de encabezado más profesional
    header_data.append([logo_cell, titulo, f'Versión {version}<br/>Fecha: {fecha_actual}'])
    header_data.append(['', empresa_nombre, ''])
    
    header_table = Table(header_data, colWidths=[120, 200, 120])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),  # Logo a la izquierda
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),  # Título centrado
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),  # Info a la derecha
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (1, 0), (1, 0), 20),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, 0), (1, 0), colors.HexColor('#2c3e50')),
        ('FONTSIZE', (2, 0), (2, 0), 10),
        ('FONTNAME', (2, 0), (2, 0), 'Helvetica'),
        ('FONTSIZE', (1, 1), (1, 1), 12),
        ('FONTNAME', (1, 1), (1, 1), 'Helvetica'),
        ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor('#7f8c8d')),
        ('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 30))
    
    # Agrupar incidencias por estado
    grupos = {}
    for incidencia in incidencias:
        estado = incidencia.estado
        if estado not in grupos:
            grupos[estado] = []
        grupos[estado].append(incidencia)
    
    # Procesar cada grupo con diseño mejorado
    contador_imagen = 1
    contador_pagina = 1
    
    for grupo_nombre, grupo_incidencias in grupos.items():
        # Título de la sección principal con diseño mejorado
        section_title = Paragraph(f"ESTADO: {grupo_nombre.upper()}", section_style)
        story.append(section_title)
        
        # Procesar cada incidencia del grupo
        for i, incidencia in enumerate(grupo_incidencias, 1):
            # Título de la subsección (incidencia) con diseño mejorado
            subsection_title = Paragraph(f"{i}. {incidencia.titulo}", subsection_style)
            story.append(subsection_title)
            
            # Información básica de la incidencia con mejor formato
            info_text = f"""
            <b>Índice:</b> {incidencia.indice}<br/>
            <b>Cliente:</b> {incidencia.cliente.nombre if incidencia.cliente else 'N/A'}<br/>
            <b>Sede:</b> {incidencia.sede.nombre if incidencia.sede else 'N/A'}<br/>
            <b>Estado:</b> {incidencia.estado}<br/>
            <b>Fecha Inicio:</b> {incidencia.fecha_inicio.strftime('%d/%m/%Y %H:%M')}<br/>
            <b>Técnico Asignado:</b> {incidencia.tecnico.nombre if incidencia.tecnico else 'Sin asignar'}<br/>
            <b>Descripción:</b> {incidencia.descripcion}<br/>
            """
            
            incidencia_info = Paragraph(info_text, incidencia_style)
            story.append(incidencia_info)
            
            # Agregar imágenes adjuntas si existen con mejor formato
            if incidencia.adjuntos:
                archivos = incidencia.adjuntos.split(',')
                for archivo in archivos:
                    archivo_path = os.path.join(app.config['UPLOAD_FOLDER'], archivo.strip())
                    if os.path.exists(archivo_path):
                        try:
                            # Verificar si es una imagen
                            with PILImage.open(archivo_path) as img:
                                # Redimensionar imagen para mejor presentación
                                max_width = 500
                                max_height = 400
                                
                                if img.width > max_width or img.height > max_height:
                                    ratio = min(max_width/img.width, max_height/img.height)
                                    new_width = int(img.width * ratio)
                                    new_height = int(img.height * ratio)
                                else:
                                    new_width = img.width
                                    new_height = img.height
                                
                                # Guardar imagen temporalmente con máxima calidad y DPI original
                                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{archivo}')
                                img.save(temp_path, quality=100, optimize=False)
                                
                                # Agregar espacio antes de la imagen
                                story.append(Spacer(1, 10))
                                
                                # Crear leyenda mejorada
                                caption_text = f"Figura {contador_imagen}. {archivo.replace('_', ' ').replace('.jpg', '').replace('.png', '').replace('.jpeg', '').title()}"
                                caption = Paragraph(caption_text, caption_style)
                                story.append(caption)
                                
                                # Agregar imagen centrada con borde usando dimensiones más grandes para mejor resolución
                                pdf_image = Image(temp_path, width=new_width*2, height=new_height*2)
                                
                                # Crear tabla para centrar la imagen con borde
                                image_table = Table([[pdf_image]], colWidths=[img.width])
                                image_table.setStyle(TableStyle([
                                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                                    ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                                    ('BOX', (0, 0), (0, 0), 1, colors.HexColor('#bdc3c7')),
                                    ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f8f9fa')),
                                ]))
                                
                                story.append(image_table)
                                contador_imagen += 1
                                
                                # Eliminar archivo temporal
                                os.remove(temp_path)
                                
                        except Exception as e:
                            print(f"Error procesando imagen {archivo}: {e}")
                            continue
            
            story.append(Spacer(1, 20))
        
        story.append(Spacer(1, 30))
    
    # Agregar pie de página profesional
    footer_text = f"""
    <para align=center>
    <font name="Helvetica" size="8" color="#7f8c8d">
    Informe generado automáticamente por el Sistema ERP BACS<br/>
    Building Automation and Control System - Versión {version}<br/>
    Fecha de generación: {fecha_actual}
    </font>
    </para>
    """
    footer = Paragraph(footer_text, styles['Normal'])
    story.append(footer)
    
    # Construir el PDF
    doc.build(story)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'informe_profesional_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
    )

def generar_pdf_multipagina_profesional(incidencias, agrupacion='estado'):
    """
    Genera un PDF profesional con formato de páginas múltiples,
    similar al ejemplo HTML proporcionado por el usuario.
    """
    buffer = io.BytesIO()
    
    # Configuración de página A4
    from reportlab.lib.pagesizes import A4
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                          leftMargin=40, rightMargin=40,
                          topMargin=40, bottomMargin=40)
    
    styles = getSampleStyleSheet()
    story = []
    
    # Crear estilos personalizados para formato multipágina
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=28,
        spaceAfter=30,
        alignment=1,  # Centrado
        textColor=colors.HexColor('#1a1a1a'),
        fontName='Helvetica-Bold'
    )
    
    empresa_style = ParagraphStyle(
        'EmpresaStyle',
        parent=styles['Normal'],
        fontSize=14,
        alignment=1,  # Centrado
        textColor=colors.HexColor('#666666'),
        fontName='Helvetica'
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=11,
        alignment=2,  # Derecha
        textColor=colors.HexColor('#333333'),
        fontName='Helvetica'
    )
    
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        spaceBefore=30,
        textColor=colors.white,
        fontName='Helvetica-Bold',
        alignment=1,  # Centrado
        backColor=colors.HexColor('#2c3e50'),
        borderPadding=15,
        borderWidth=2,
        borderColor=colors.HexColor('#34495e')
    )
    
    incidencia_style = ParagraphStyle(
        'IncidenciaStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=15,
        spaceBefore=15,
        fontName='Helvetica',
        leftIndent=0,
        textColor=colors.HexColor('#2c3e50'),
        alignment=0  # Justificado
    )
    
    caption_style = ParagraphStyle(
        'CaptionStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        fontName='Helvetica-Italic',
        alignment=1  # Centrado
    )
    
    # Crear encabezado profesional para primera página
    titulo = 'INFORME DE ACTIVIDADES'
    empresa_nombre = 'BUILDING AUTOMATION AND CONTROL SYSTEM'
    version = '1.0'
    fecha_actual = datetime.now().strftime('%d/%m/%Y')
    
    # Encabezado principal
    header_data = []
    
    # Agregar logo si existe
    logo_cell = obtener_logo_pdf(max_width=120, max_height=60)
    
    header_data.append([logo_cell, titulo, f'Versión {version}<br/>Fecha: {fecha_actual}'])
    header_data.append(['', empresa_nombre, ''])
    
    header_table = Table(header_data, colWidths=[140, 220, 140])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (1, 0), (1, 0), 22),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, 0), (1, 0), colors.HexColor('#1a1a1a')),
        ('FONTSIZE', (2, 0), (2, 0), 11),
        ('FONTNAME', (2, 0), (2, 0), 'Helvetica'),
        ('FONTSIZE', (1, 1), (1, 1), 14),
        ('FONTNAME', (1, 1), (1, 1), 'Helvetica'),
        ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor('#666666')),
        ('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor('#bdc3c7')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 40))
    
    # Agrupar incidencias por estado
    grupos = {}
    for incidencia in incidencias:
        estado = incidencia.estado
        if estado not in grupos:
            grupos[estado] = []
        grupos[estado].append(incidencia)
    
    # Procesar cada grupo
    contador_imagen = 1
    
    for grupo_nombre, grupo_incidencias in grupos.items():
        # Título de la sección principal
        section_title = Paragraph(f"ESTADO: {grupo_nombre.upper()}", section_style)
        story.append(section_title)
        
        # Procesar cada incidencia del grupo
        for i, incidencia in enumerate(grupo_incidencias, 1):
            # Información de la incidencia
            info_text = f"""
            <b>Incidencia {i}:</b> {incidencia.titulo}<br/>
            <b>Índice:</b> {incidencia.indice}<br/>
            <b>Cliente:</b> {incidencia.cliente.nombre if incidencia.cliente else 'N/A'}<br/>
            <b>Sede:</b> {incidencia.sede.nombre if incidencia.sede else 'N/A'}<br/>
            <b>Estado:</b> {incidencia.estado}<br/>
            <b>Fecha Inicio:</b> {incidencia.fecha_inicio.strftime('%d/%m/%Y %H:%M')}<br/>
            <b>Técnico Asignado:</b> {incidencia.tecnico.nombre if incidencia.tecnico else 'Sin asignar'}<br/>
            <b>Descripción:</b> {incidencia.descripcion}<br/>
            """
            
            incidencia_info = Paragraph(info_text, incidencia_style)
            story.append(incidencia_info)
            
            # Agregar imágenes adjuntas si existen - UNA POR PÁGINA
            if incidencia.adjuntos:
                archivos = incidencia.adjuntos.split(',')
                for archivo in archivos:
                    archivo_path = os.path.join(app.config['UPLOAD_FOLDER'], archivo.strip())
                    if os.path.exists(archivo_path):
                        try:
                            # Verificar si es una imagen
                            with PILImage.open(archivo_path) as img:
                                # Redimensionar imagen para ocupar la mayor parte de la página
                                max_width = 600
                                max_height = 700
                                
                                if img.width > max_width or img.height > max_height:
                                    ratio = min(max_width/img.width, max_height/img.height)
                                    new_width = int(img.width * ratio)
                                    new_height = int(img.height * ratio)
                                    img = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
                                
                                # Guardar imagen temporalmente con máxima calidad y DPI muy alto
                                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{archivo}')
                                img.save(temp_path, quality=100, optimize=False, dpi=(1200, 1200))
                                
                                # Salto de página antes de cada imagen
                                story.append(Spacer(1, 50))
                                
                                # Crear leyenda centrada
                                caption_text = f"Imagen {contador_imagen}. {archivo.replace('_', ' ').replace('.jpg', '').replace('.png', '').replace('.jpeg', '').title()}"
                                caption = Paragraph(caption_text, caption_style)
                                story.append(caption)
                                
                                # Agregar imagen centrada ocupando la mayor parte de la página
                                pdf_image = Image(temp_path, width=img.width, height=img.height)
                                
                                # Crear tabla para centrar la imagen con marco elegante
                                image_table = Table([[pdf_image]], colWidths=[img.width])
                                image_table.setStyle(TableStyle([
                                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                                    ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                                    ('BOX', (0, 0), (0, 0), 2, colors.HexColor('#34495e')),
                                    ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#ffffff')),
                                    ('PADDING', (0, 0), (0, 0), 10),
                                ]))
                                
                                story.append(image_table)
                                story.append(Spacer(1, 30))
                                
                                # Información adicional de la imagen
                                img_info_text = f"""
                                <para align=center>
                                <font name="Helvetica" size="10" color="#666666">
                                <b>Incidencia:</b> {incidencia.titulo}<br/>
                                <b>Cliente:</b> {incidencia.cliente.nombre if incidencia.cliente else 'N/A'}<br/>
                                <b>Fecha:</b> {incidencia.fecha_inicio.strftime('%d/%m/%Y')}
                                </font>
                                </para>
                                """
                                img_info = Paragraph(img_info_text, styles['Normal'])
                                story.append(img_info)
                                
                                contador_imagen += 1
                                
                                # Eliminar archivo temporal
                                os.remove(temp_path)
                                
                        except Exception as e:
                            print(f"Error procesando imagen {archivo}: {e}")
                            continue
            
            story.append(Spacer(1, 30))
        
        story.append(Spacer(1, 40))
    
    # Agregar pie de página profesional
    footer_text = f"""
    <para align=center>
    <font name="Helvetica" size="9" color="#666666">
    Informe generado automáticamente por el Sistema ERP BACS<br/>
    Building Automation and Control System - Versión {version}<br/>
    Fecha de generación: {fecha_actual} | Total de imágenes: {contador_imagen - 1}
    </font>
    </para>
    """
    footer = Paragraph(footer_text, styles['Normal'])
    story.append(footer)
    
    # Construir el PDF
    doc.build(story)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'informe_multipagina_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
    )

def generar_pdf_informe_estructurado(incidencias, datos_informe):
    """
    Genera un PDF con formato estructurado similar al HTML proporcionado.
    Datos del informe: cliente, atencion, cargo, alcance, fecha, introduccion
    """
    buffer = io.BytesIO()
    
    # Configuración de página A4
    from reportlab.lib.pagesizes import A4
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                          leftMargin=40, rightMargin=40,
                          topMargin=40, bottomMargin=40)
    
    styles = getSampleStyleSheet()
    story = []
    
    # Crear estilos personalizados basados en el HTML proporcionado
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Title'],
        fontSize=22,
        spaceAfter=15,
        alignment=1,  # Centrado
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=8,
        fontName='Helvetica',
        lineHeight=1.6
    )
    
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    caption_style = ParagraphStyle(
        'CaptionStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        fontName='Helvetica-Italic',
        alignment=1  # Centrado
    )
    
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#666666'),
        alignment=1,  # Centrado
        fontName='Helvetica'
    )
    
    # Crear encabezado con logo (similar al HTML)
    header_data = []
    logo_cell = obtener_logo_pdf(max_width=80, max_height=40)
    
    header_data.append([logo_cell, 'INFORME DE ACTIVIDADES', f'Versión {datos_informe.get("version", "1")}'])
    
    header_table = Table(header_data, colWidths=[100, 200, 100])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (1, 0), (1, 0), 18),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (2, 0), (2, 0), 10),
        ('FONTNAME', (2, 0), (2, 0), 'Helvetica'),
        ('LINEBELOW', (0, 0), (-1, -1), 2, colors.black),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 20))
    
    # Información del cliente (similar al HTML)
    info_text = f"""
    <b>Cliente:</b> {datos_informe.get('cliente', 'N/A')}<br/>
    <b>Atención:</b> {datos_informe.get('atencion', 'N/A')}<br/>
    <b>Cargo:</b> {datos_informe.get('cargo', 'N/A')}<br/>
    <b>Alcance del Proyecto:</b> {datos_informe.get('alcance', 'N/A')}<br/>
    <b>Fecha:</b> {datos_informe.get('fecha', datetime.now().strftime('%d/%m/%Y'))}
    """
    
    info_paragraph = Paragraph(info_text, info_style)
    story.append(info_paragraph)
    story.append(Spacer(1, 20))
    
    # Introducción
    if datos_informe.get('introduccion'):
        intro_title = Paragraph("Introducción", section_style)
        story.append(intro_title)
        
        intro_text = Paragraph(datos_informe['introduccion'], info_style)
        story.append(intro_text)
        story.append(Spacer(1, 20))
    
    # Actividades realizadas (formato similar al HTML)
    actividades_title = Paragraph("1. Actividades Realizadas", section_style)
    story.append(actividades_title)
    
    contador_imagen = 1
    
    # Procesar cada incidencia como una actividad
    for i, incidencia in enumerate(incidencias, 1):
        # Descripción de la actividad
        actividad_text = f"Descripción de las actividades ejecutadas: {incidencia.descripcion}"
        actividad_paragraph = Paragraph(actividad_text, info_style)
        story.append(actividad_paragraph)
        
        # Agregar imágenes si existen (formato similar al HTML)
        if incidencia.adjuntos:
            archivos = incidencia.adjuntos.split(',')
            titulos = incidencia.titulos_imagenes.split(',') if incidencia.titulos_imagenes else []
            
            for j, archivo in enumerate(archivos):
                archivo_path = os.path.join(app.config['UPLOAD_FOLDER'], archivo.strip())
                if os.path.exists(archivo_path):
                    try:
                        # Verificar si es una imagen
                        with PILImage.open(archivo_path) as img:
                            # Redimensionar imagen para el formato HTML (max-width: 600px)
                            max_width = 600
                            max_height = 400
                            
                            if img.width > max_width or img.height > max_height:
                                ratio = min(max_width/img.width, max_height/img.height)
                                new_width = int(img.width * ratio)
                                new_height = int(img.height * ratio)
                                img = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
                            
                            # Guardar imagen temporalmente con máxima calidad y DPI muy alto
                            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{archivo}')
                            img.save(temp_path, quality=100, optimize=False, dpi=(1200, 1200))
                            
                            # Agregar espacio antes de la imagen
                            story.append(Spacer(1, 15))
                            
                            # Crear leyenda (similar al HTML: "Imagen X. Descripción")
                            titulo_imagen = titulos[j].strip() if j < len(titulos) and titulos[j].strip() else archivo.replace('_', ' ').replace('.jpg', '').replace('.png', '').replace('.jpeg', '').title()
                            caption_text = f"Imagen {contador_imagen}. {titulo_imagen}"
                            caption = Paragraph(caption_text, caption_style)
                            story.append(caption)
                            
                            # Agregar imagen centrada con borde (similar al HTML)
                            pdf_image = Image(temp_path, width=img.width, height=img.height)
                            
                            # Crear tabla para centrar la imagen con borde
                            image_table = Table([[pdf_image]], colWidths=[img.width])
                            image_table.setStyle(TableStyle([
                                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                                ('BOX', (0, 0), (0, 0), 1, colors.HexColor('#ccc')),
                                ('PADDING', (0, 0), (0, 0), 5),
                            ]))
                            
                            story.append(image_table)
                            contador_imagen += 1
                            
                            # Eliminar archivo temporal
                            os.remove(temp_path)
                            
                    except Exception as e:
                        print(f"Error procesando imagen {archivo}: {e}")
                        continue
        
        story.append(Spacer(1, 20))
    
    # Conclusiones
    if datos_informe.get('conclusiones'):
        conclusiones_title = Paragraph("Conclusiones", section_style)
        story.append(conclusiones_title)
        
        conclusiones_text = Paragraph(datos_informe['conclusiones'], info_style)
        story.append(conclusiones_text)
    
    # Pie de página (similar al HTML)
    story.append(Spacer(1, 50))
    footer_text = "Informe generado automáticamente - Plataforma de Incidencias"
    footer = Paragraph(footer_text, footer_style)
    story.append(footer)
    
    # Construir el PDF
    doc.build(story)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'informe_estructurado_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
    )

def crear_collage_imagenes(imagenes_paths, titulo_collage):
    """
    Crear un collage de imágenes manteniendo la relación de aspecto
    El collage resultante será cuadrado (1:1) combinando todas las imágenes
    """
    try:
        from PIL import Image as PILImage
        
        # Abrir todas las imágenes
        imagenes = []
        for path in imagenes_paths:
            if os.path.exists(path):
                img = PILImage.open(path)
                imagenes.append(img)
        
        if not imagenes:
            return None
        
        # Calcular el tamaño del collage (cuadrado)
        num_imagenes = len(imagenes)
        
        # Determinar la disposición (2x2, 3x3, etc.)
        if num_imagenes <= 4:
            cols = 2
            rows = 2
        elif num_imagenes <= 9:
            cols = 3
            rows = 3
        else:
            cols = 4
            rows = 4
        
        # Tamaño máximo del collage (6cm = 170 puntos en ReportLab)
        max_size = 170
        
        # Calcular tamaño de cada celda
        cell_size = max_size // max(cols, rows)
        
        # Crear imagen del collage
        collage_width = cell_size * cols
        collage_height = cell_size * rows
        collage = PILImage.new('RGB', (collage_width, collage_height), 'white')
        
        # Colocar imágenes en el collage
        for i, img in enumerate(imagenes[:cols*rows]):
            row = i // cols
            col = i % cols
            
            # Redimensionar imagen manteniendo relación de aspecto
            img_resized = img.copy()
            img_resized.thumbnail((cell_size, cell_size), PILImage.Resampling.LANCZOS)
            
            # Centrar la imagen en la celda
            x_offset = col * cell_size + (cell_size - img_resized.width) // 2
            y_offset = row * cell_size + (cell_size - img_resized.height) // 2
            
            collage.paste(img_resized, (x_offset, y_offset))
        
        # Guardar collage temporalmente
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'collage_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        collage.save(temp_path)
        
        return temp_path
        
    except Exception as e:
        print(f"Error creando collage: {e}")
        return None

def calcular_tamaño_imagen(img_width, img_height, max_size_cm=6):
    """
    Calcular el tamaño de imagen manteniendo la relación de aspecto
    max_size_cm: tamaño máximo en centímetros (6cm = 170 puntos en ReportLab)
    """
    max_size_points = max_size_cm * 28.35  # Convertir cm a puntos
    
    # Determinar si es cuadrada, horizontal o vertical
    aspect_ratio = img_width / img_height
    
    if abs(aspect_ratio - 1.0) < 0.1:  # Cuadrada (1:1)
        # Máximo 6cm por lado
        if img_width > max_size_points:
            scale = max_size_points / img_width
            return int(img_width * scale), int(img_height * scale)
        return img_width, img_height
    
    elif aspect_ratio > 1.0:  # Horizontal
        # Máximo 6cm de ancho, 3cm de alto
        max_width = max_size_points
        max_height = max_size_points / 2
        
        if img_width > max_width:
            scale = max_width / img_width
            return int(img_width * scale), int(img_height * scale)
        elif img_height > max_height:
            scale = max_height / img_height
            return int(img_width * scale), int(img_height * scale)
        return img_width, img_height
    
    else:  # Vertical
        # Máximo 6cm de alto, 3cm de ancho
        max_width = max_size_points / 2
        max_height = max_size_points
        
        if img_height > max_height:
            scale = max_height / img_height
            return int(img_width * scale), int(img_height * scale)
        elif img_width > max_width:
            scale = max_width / img_width
            return int(img_width * scale), int(img_height * scale)
        return img_width, img_height

def generar_pdf_informe_html_format(incidencias, datos_informe):
    """
    Genera un PDF con el formato exacto del HTML proporcionado por el usuario.
    Formato: Encabezado con logo, información del cliente, introducción, 
    actividades realizadas con imágenes, y conclusiones.
    """
    buffer = io.BytesIO()
    
    # Configuración de página A4 con márgenes similares al HTML (40px = ~1.4cm)
    from reportlab.lib.pagesizes import A4
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                          leftMargin=40, rightMargin=40,
                          topMargin=40, bottomMargin=40)
    
    styles = getSampleStyleSheet()
    story = []
    
    # Estilos personalizados que replican el CSS del HTML
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Title'],
        fontSize=22,
        spaceAfter=10,
        alignment=1,  # Centrado
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=5,
        fontName='Helvetica',
        lineHeight=1.6
    )
    
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=30,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    activity_title_style = ParagraphStyle(
        'ActivityTitleStyle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=8,
        spaceBefore=15,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    caption_style = ParagraphStyle(
        'CaptionStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        fontName='Helvetica',
        alignment=1,  # Centrado
        spaceAfter=15
    )
    
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#666666'),
        alignment=1,  # Centrado
        fontName='Helvetica',
        spaceBefore=50
    )
    
    # === ENCABEZADO === (replica el <header> del HTML)
    header_data = []
    logo_cell = obtener_logo_pdf(max_width=80, max_height=40)
    
    # Estructura del encabezado: Logo | Título | Versión
    header_data.append([logo_cell, 'INFORME DE ACTIVIDADES', f'Versión {datos_informe.get("version", "1")}'])
    
    header_table = Table(header_data, colWidths=[100, 200, 100])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),      # Logo a la izquierda
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),   # Título centrado
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),    # Versión a la derecha
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (1, 0), (1, 0), 18),       # font-size: 22px
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (2, 0), (2, 0), 10),
        ('FONTNAME', (2, 0), (2, 0), 'Helvetica'),
        ('LINEBELOW', (0, 0), (-1, -1), 2, colors.black),  # border-bottom: 2px solid #000
        ('PADDING', (0, 0), (-1, -1), 15),     # padding-bottom: 15px
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 20))  # margin-bottom: 20px
    
    # === INFORMACIÓN DEL CLIENTE === (replica la clase .info del HTML)
    info_text = f"""
    <b>Cliente:</b> {datos_informe.get('cliente', 'Nombre del Cliente')}<br/>
    <b>Atención:</b> {datos_informe.get('atencion', 'Persona de contacto')}<br/>
    <b>Cargo:</b> {datos_informe.get('cargo', 'Cargo del contacto')}<br/>
    <b>Alcance del Proyecto:</b> {datos_informe.get('alcance', 'Descripción corta')}<br/>
    <b>Fecha:</b> {datos_informe.get('fecha', datetime.now().strftime('%d/%m/%Y'))}
    """
    
    info_paragraph = Paragraph(info_text, info_style)
    story.append(info_paragraph)
    story.append(Spacer(1, 20))  # margin-bottom: 20px
    
    # === INTRODUCCIÓN === (replica la sección Introducción del HTML)
    if datos_informe.get('introduccion'):
        intro_title = Paragraph("Introducción", section_style)
        story.append(intro_title)
        
        intro_text = Paragraph(datos_informe['introduccion'], info_style)
        story.append(intro_text)
        story.append(Spacer(1, 20))
    
    # === ACTIVIDADES REALIZADAS === (replica la sección 1. Actividades Realizadas del HTML)
    actividades_title = Paragraph("1. Actividades Realizadas", section_style)
    story.append(actividades_title)
    
    contador_imagen = 1
    
    # Procesar cada incidencia como una actividad
    for i, incidencia in enumerate(incidencias, 1):
        # Título de la actividad con enumeración
        actividad_titulo = f"{i}. {incidencia.titulo}"
        actividad_title_paragraph = Paragraph(actividad_titulo, activity_title_style)
        story.append(actividad_title_paragraph)
        
        # Información adicional de la actividad
        info_actividad = f"<b>Índice:</b> {incidencia.indice} | <b>Cliente:</b> {incidencia.cliente.nombre if incidencia.cliente else 'N/A'} | <b>Sede:</b> {incidencia.sede.nombre if incidencia.sede else 'N/A'}"
        info_paragraph = Paragraph(info_actividad, info_style)
        story.append(info_paragraph)
        
        # Descripción de la actividad
        actividad_text = f"<b>Descripción:</b> {incidencia.descripcion}"
        actividad_paragraph = Paragraph(actividad_text, info_style)
        story.append(actividad_paragraph)
        
        # Espacio antes de las imágenes
        story.append(Spacer(1, 10))
        
        # Agregar imágenes si existen
        if incidencia.adjuntos:
            # Cargar configuración de imágenes
            configuracion = {}
            if incidencia.configuracion_imagenes:
                try:
                    configuracion = json.loads(incidencia.configuracion_imagenes)
                except:
                    configuracion = {'imagenes_individuales': [], 'collages': []}
            
            # Procesar imágenes individuales
            for img_config in configuracion.get('imagenes_individuales', []):
                archivo = img_config['archivo']
                titulo = img_config['titulo']
                archivo_path = os.path.join(app.config['UPLOAD_FOLDER'], archivo)
                
                if os.path.exists(archivo_path):
                    try:
                        with PILImage.open(archivo_path) as img:
                            # Calcular tamaño optimizado según relación de aspecto
                            new_width, new_height = calcular_tamaño_imagen(img.width, img.height)
                            
                            # Guardar imagen temporalmente
                            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{archivo}')
                            img_resized = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
                            img_resized.save(temp_path)
                            
                            # Agregar espacio antes de la imagen
                            story.append(Spacer(1, 15))
                            
                            # Agregar imagen centrada con borde
                            pdf_image = Image(temp_path, width=new_width, height=new_height)
                            
                            # Crear tabla para centrar la imagen
                            image_table = Table([[pdf_image]], colWidths=[new_width])
                            image_table.setStyle(TableStyle([
                                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                                ('BOX', (0, 0), (0, 0), 1, colors.HexColor('#ccc')),
                                ('PADDING', (0, 0), (0, 0), 5),
                            ]))
                            
                            story.append(image_table)
                            
                            # Crear leyenda debajo de la imagen
                            caption_text = f"Imagen {contador_imagen}. {titulo}"
                            caption = Paragraph(caption_text, caption_style)
                            story.append(caption)
                            contador_imagen += 1
                            
                    except Exception as e:
                        print(f"Error procesando imagen individual {archivo}: {e}")
                        continue
            
            # Procesar collages
            for collage_config in configuracion.get('collages', []):
                titulo_collage = collage_config['titulo']
                imagenes_collage = collage_config['imagenes']
                imagenes_paths = []
                
                for archivo_collage in imagenes_collage:
                    archivo_path = os.path.join(app.config['UPLOAD_FOLDER'], archivo_collage.strip())
                    if os.path.exists(archivo_path):
                        imagenes_paths.append(archivo_path)
                
                if imagenes_paths:
                    collage_path = crear_collage_imagenes(imagenes_paths, titulo_collage)
                    if collage_path:
                        try:
                            with PILImage.open(collage_path) as img:
                                # Calcular tamaño optimizado
                                new_width, new_height = calcular_tamaño_imagen(img.width, img.height)
                                
                                # Guardar imagen temporalmente
                                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_collage_{contador_imagen}.png')
                                img_resized = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
                                img_resized.save(temp_path)
                                
                                # Agregar espacio antes de la imagen
                                story.append(Spacer(1, 15))
                                
                                # Agregar imagen centrada con borde
                                pdf_image = Image(temp_path, width=new_width, height=new_height)
                                
                                # Crear tabla para centrar la imagen
                                image_table = Table([[pdf_image]], colWidths=[new_width])
                                image_table.setStyle(TableStyle([
                                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                                    ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                                    ('BOX', (0, 0), (0, 0), 1, colors.HexColor('#ccc')),
                                    ('PADDING', (0, 0), (0, 0), 5),
                                ]))
                                
                                story.append(image_table)
                                
                                # Crear leyenda para el collage debajo de la imagen
                                caption_text = f"Imagen {contador_imagen}. {titulo_collage}"
                                caption = Paragraph(caption_text, caption_style)
                                story.append(caption)
                                contador_imagen += 1
                                
                        except Exception as e:
                            print(f"Error procesando collage: {e}")
                            continue
        
        story.append(Spacer(1, 20))  # Espacio después de cada actividad
    
    # === CONCLUSIONES === (replica la sección Conclusiones del HTML)
    if datos_informe.get('conclusiones'):
        conclusiones_title = Paragraph("Conclusiones", section_style)
        story.append(conclusiones_title)
        
        conclusiones_text = Paragraph(datos_informe['conclusiones'], info_style)
        story.append(conclusiones_text)
    
    # === PIE DE PÁGINA === (replica el <footer> del HTML)
    footer_text = f"Informe generado automáticamente - Plataforma de Incidencias | Total de imágenes: {contador_imagen - 1}"
    footer = Paragraph(footer_text, footer_style)
    story.append(footer)
    
    # Construir el PDF
    doc.build(story)
    buffer.seek(0)
    
    # Limpiar archivos temporales después de construir el PDF
    temp_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.startswith('temp_') or f.startswith('collage_')]
    for temp_file in temp_files:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], temp_file))
        except:
            pass  # Ignorar errores al eliminar archivos temporales
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'informe_html_format_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
    )

def generar_pdf(incidencias):
    return generar_pdf_profesional(incidencias)

# Función para inicializar la base de datos
def init_db():
    """Función simplificada para inicializar la base de datos"""
    with app.app_context():
        try:
            print("🔧 Inicializando base de datos...")
            
            # Solo crear las tablas básicas
            db.create_all()
            print("✅ Tablas creadas correctamente")
            
        except Exception as e:
            print(f"Error inicializando base de datos: {e}")
            db.session.rollback()

# ==================== GESTIÓN DE ÍNDICES ====================

@app.route('/indices')
@login_required
def indices():
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    indices = Indice.query.all()
    return render_template('indices.html', indices=indices)

@app.route('/nuevo_indice', methods=['GET', 'POST'])
@login_required
def nuevo_indice():
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        prefijo = request.form['prefijo'].upper().strip()
        numero_inicial = int(request.form.get('numero_inicial', 0))
        
        # Verificar que el prefijo no exista
        if Indice.query.filter_by(prefijo=prefijo).first():
            flash('Ya existe un índice con ese prefijo', 'error')
            return redirect(url_for('indices'))
        
        # Crear nuevo índice
        indice = Indice(
            prefijo=prefijo,
            numero_actual=numero_inicial,
            formato='000000'
        )
        
        db.session.add(indice)
        db.session.commit()
        
        flash('Índice creado exitosamente', 'success')
        return redirect(url_for('indices'))
    
    return render_template('nuevo_indice.html')

@app.route('/editar_indice/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_indice(id):
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    indice = Indice.query.get_or_404(id)
    
    if request.method == 'POST':
        prefijo = request.form['prefijo'].upper().strip()
        numero_actual = int(request.form['numero_actual'])
        
        # Verificar que el prefijo no exista en otro índice
        existing = Indice.query.filter(Indice.prefijo == prefijo, Indice.id != id).first()
        if existing:
            flash('Ya existe un índice con ese prefijo', 'error')
            return redirect(url_for('indices'))
        
        indice.prefijo = prefijo
        indice.numero_actual = numero_actual
        
        db.session.commit()
        flash('Índice actualizado exitosamente', 'success')
        return redirect(url_for('indices'))
    
    return render_template('editar_indice.html', indice=indice)

@app.route('/eliminar_indice/<int:id>')
@login_required
def eliminar_indice(id):
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    indice = Indice.query.get_or_404(id)
    
    # Verificar si hay incidencias usando este índice
    incidencias_con_indice = Incidencia.query.filter(Incidencia.indice.like(f"{indice.prefijo}_%")).count()
    if incidencias_con_indice > 0:
        flash(f'No se puede eliminar el índice porque hay {incidencias_con_indice} incidencias que lo usan', 'error')
        return redirect(url_for('indices'))
    
    db.session.delete(indice)
    db.session.commit()
    
    flash('Índice eliminado exitosamente', 'success')
    return redirect(url_for('indices'))

# ==================== GESTIÓN DE ROLES ====================

@app.route('/roles')
@login_required
def roles():
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    roles = Rol.query.all()
    
    # Agregar información de usuarios por rol
    for rol in roles:
        rol.usuarios_count = User.query.filter_by(rol_id=rol.id).count()
        rol.usuarios = User.query.filter_by(rol_id=rol.id).all()
    
    return render_template('roles.html', roles=roles)

@app.route('/nuevo_rol', methods=['GET', 'POST'])
@login_required
def nuevo_rol():
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        descripcion = request.form['descripcion'].strip()
        
        # Verificar que el nombre no exista
        if Rol.query.filter_by(nombre=nombre).first():
            flash('Ya existe un rol con ese nombre', 'error')
            return redirect(url_for('roles'))
        
        # Crear nuevo rol
        rol = Rol(nombre=nombre, descripcion=descripcion)
        
        db.session.add(rol)
        db.session.commit()
        
        flash('Rol creado exitosamente', 'success')
        return redirect(url_for('roles'))
    
    return render_template('nuevo_rol.html')

@app.route('/editar_rol/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_rol(id):
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    rol = Rol.query.get_or_404(id)
    
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        descripcion = request.form['descripcion'].strip()
        
        # Verificar que el nombre no exista en otro rol
        existing = Rol.query.filter(Rol.nombre == nombre, Rol.id != id).first()
        if existing:
            flash('Ya existe un rol con ese nombre', 'error')
            return redirect(url_for('roles'))
        
        rol.nombre = nombre
        rol.descripcion = descripcion
        
        db.session.commit()
        flash('Rol actualizado exitosamente', 'success')
        return redirect(url_for('roles'))
    
    # Agregar información de usuarios por rol
    rol.usuarios_count = User.query.filter_by(rol_id=rol.id).count()
    rol.usuarios = User.query.filter_by(rol_id=rol.id).all()
    
    return render_template('editar_rol.html', rol=rol)

@app.route('/eliminar_rol/<int:id>')
@login_required
def eliminar_rol(id):
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('dashboard'))
    
    rol = Rol.query.get_or_404(id)
    
    # Verificar si hay usuarios con este rol
    usuarios_con_rol = User.query.filter_by(rol_id=rol.id).count()
    if usuarios_con_rol > 0:
        flash(f'No se puede eliminar el rol porque hay {usuarios_con_rol} usuarios que lo usan', 'error')
        return redirect(url_for('roles'))
    
    try:
        db.session.delete(rol)
        db.session.commit()
        flash('Rol eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar rol: ' + str(e), 'error')
    
    return redirect(url_for('roles'))

# ==================== GESTIÓN DE FORMULARIOS DINÁMICOS ====================

@app.route('/formularios')
@login_required
def formularios():
    """Vista principal de formularios - diferente según el rol del usuario"""
    if current_user.rol.nombre == 'Administrador':
        # Los administradores ven todos los formularios y pueden gestionarlos
        formularios = Formulario.query.filter_by(activo=True).order_by(Formulario.fecha_creacion.desc()).all()
        return render_template('formularios_admin.html', formularios=formularios)
    else:
        # Los técnicos y coordinadores ven solo los formularios disponibles para diligenciar
        formularios = Formulario.query.filter_by(activo=True).order_by(Formulario.nombre).all()
        return render_template('formularios_usuario.html', formularios=formularios)

@app.route('/formularios/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_formulario():
    """Crear nuevo formulario - solo administradores"""
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('formularios'))
    
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        descripcion = request.form.get('descripcion', '').strip()
        
        # Verificar que el nombre no esté vacío
        if not nombre:
            flash('El nombre del formulario es obligatorio', 'error')
            return redirect(url_for('nuevo_formulario'))
        
        # Crear nuevo formulario
        formulario = Formulario(
            nombre=nombre,
            descripcion=descripcion,
            creado_por=current_user.id
        )
        
        try:
            db.session.add(formulario)
            db.session.commit()
            flash('Formulario creado exitosamente', 'success')
            return redirect(url_for('editar_formulario', id=formulario.id))
        except Exception as e:
            db.session.rollback()
            flash('Error al crear formulario: ' + str(e), 'error')
    
    return render_template('nuevo_formulario.html')

@app.route('/formularios/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_formulario(id):
    """Editar formulario y sus campos - solo administradores"""
    if current_user.rol.nombre != 'Administrador':
        flash('No tienes permisos para acceder a esta sección', 'error')
        return redirect(url_for('formularios'))
    
    formulario = Formulario.query.get_or_404(id)
    
    if request.method == 'POST':
        formulario.nombre = request.form['nombre'].strip()
        formulario.descripcion = request.form.get('descripcion', '').strip()
        formulario.activo = 'activo' in request.form
        
        try:
            db.session.commit()
            flash('Formulario actualizado exitosamente', 'success')
            return redirect(url_for('editar_formulario', id=id))
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar formulario: ' + str(e), 'error')
    
    return render_template('editar_formulario.html', formulario=formulario)

@app.route('/formularios/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_formulario(id):
    """Eliminar formulario - solo administradores"""
    if current_user.rol.nombre != 'Administrador':
        return jsonify({'success': False, 'message': 'No tienes permisos para realizar esta acción'})
    
    formulario = Formulario.query.get_or_404(id)
    
    # Verificar si tiene respuestas asociadas
    respuestas_count = RespuestaFormulario.query.filter_by(formulario_id=id).count()
    if respuestas_count > 0:
        return jsonify({'success': False, 'message': f'No se puede eliminar el formulario porque tiene {respuestas_count} respuestas asociadas'})
    
    try:
        formulario.activo = False
        db.session.commit()
        return jsonify({'success': True, 'message': 'Formulario eliminado exitosamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al eliminar formulario: {str(e)}'})

@app.route('/formularios/<int:id>/diligenciar', methods=['GET', 'POST'])
@login_required
def diligenciar_formulario(id):
    """Diligenciar un formulario - técnicos y coordinadores"""
    formulario = Formulario.query.get_or_404(id)
    
    if not formulario.activo:
        flash('Este formulario no está disponible', 'error')
        return redirect(url_for('formularios'))
    
    if request.method == 'POST':
        # Crear respuesta del formulario
        respuesta_formulario = RespuestaFormulario(
            formulario_id=id,
            diligenciado_por=current_user.id,
            estado='Completado'
        )
        
        try:
            print(f"DEBUG: Iniciando guardado del formulario {id}")
            db.session.add(respuesta_formulario)
            db.session.flush()  # Para obtener el ID
            print(f"DEBUG: RespuestaFormulario creada con ID: {respuesta_formulario.id}")
            
            # Procesar respuestas de cada campo
            campos_procesados = 0
            for campo in formulario.campos:
                respuesta_campo = RespuestaCampo(
                    respuesta_formulario_id=respuesta_formulario.id,
                    campo_id=campo.id
                )
                
                # Procesar según el tipo de campo
                if campo.tipo_campo == 'texto':
                    respuesta_campo.valor_texto = request.form.get(f'campo_{campo.id}', '')
                elif campo.tipo_campo == 'textarea':
                    respuesta_campo.valor_texto = request.form.get(f'campo_{campo.id}', '')
                elif campo.tipo_campo == 'fecha':
                    fecha_str = request.form.get(f'campo_{campo.id}', '')
                    if fecha_str:
                        respuesta_campo.valor_fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
                elif campo.tipo_campo in ['seleccion', 'seleccion_multiple']:
                    respuesta_campo.valor_texto = request.form.get(f'campo_{campo.id}', '')
                elif campo.tipo_campo == 'firma':
                    # Procesar firma con información del firmante
                    firma_data = request.form.get(f'campo_{campo.id}', '')
                    if firma_data:
                        try:
                            # Guardar PNG EXACTAMENTE como en FirmasHTML y almacenar SOLO la ruta
                            import base64
                            from io import BytesIO
                            from PIL import Image as PILImage

                            # Separar prefijo data URL
                            if ',' in firma_data:
                                _, encoded = firma_data.split(',', 1)
                            else:
                                encoded = firma_data

                            image_bytes = base64.b64decode(encoded)

                            # Preparar carpetas: uploads/formularios/firmas
                            formularios_root = os.path.join(app.config['UPLOAD_FOLDER'], 'formularios')
                            firmas_dir = os.path.join(formularios_root, 'firmas')
                            os.makedirs(firmas_dir, exist_ok=True)

                            # Nombre de archivo
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            png_filename = f'firma_{campo.id}_{respuesta_formulario.id}_{timestamp}.png'
                            png_path = os.path.join(firmas_dir, png_filename)

                            # Decodificar y guardar como PNG con fondo blanco
                            img = PILImage.open(BytesIO(image_bytes)).convert('RGBA')
                            bg = PILImage.new("RGB", img.size, (255, 255, 255))
                            bg.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                            bg.save(png_path, format='PNG')

                            print(f"DEBUG: Firma PNG guardada (POST) en: {png_path}")

                            # Guardar SOLO la ruta relativa en la DB
                            respuesta_campo.valor_archivo = os.path.join('formularios', 'firmas', png_filename)
                        except Exception as e:
                            print(f"ERROR: No se pudo guardar la firma PNG: {e}")
                            # Como fallback guarda el base64 para no perder datos
                            respuesta_campo.valor_archivo = firma_data

                        # Guardar información adicional del firmante
                        respuesta_campo.nombre_firmante = request.form.get(f'nombre_{campo.id}', '')
                        respuesta_campo.documento_firmante = request.form.get(f'documento_{campo.id}', '')
                        respuesta_campo.telefono_firmante = request.form.get(f'telefono_{campo.id}', '')
                        respuesta_campo.empresa_firmante = request.form.get(f'empresa_{campo.id}', '')
                        respuesta_campo.cargo_firmante = request.form.get(f'cargo_{campo.id}', '')
                elif campo.tipo_campo == 'foto':
                    # Procesar fotos múltiples con renombrado automático
                    archivos = request.files.getlist(f'campo_{campo.id}')
                    print(f"DEBUG: Campo {campo.id} - Recibidos {len(archivos)} archivos")
                    
                    nombres_archivos = []
                    for i, archivo in enumerate(archivos):
                        print(f"DEBUG: Archivo {i+1}: {archivo.filename if archivo.filename else 'Sin nombre'}")
                        if archivo and archivo.filename:
                            # Generar nombre único con ID y timestamp
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            file_extension = os.path.splitext(archivo.filename)[1].lower()
                            if not file_extension:
                                file_extension = '.jpg'  # Default para imágenes sin extensión
                            
                            # Crear estructura de carpetas organizada para fotos
                            formulario_nombre = secure_filename("formularios")
                            imagenes_dir = os.path.join(app.config['UPLOAD_FOLDER'], formulario_nombre, 'imagenes')
                            os.makedirs(imagenes_dir, exist_ok=True)
                            
                            # Crear nombre único: foto_campoID_respuestaID_timestamp.ext
                            unique_filename = f'foto_{campo.id}_{respuesta_formulario.id}_{timestamp}_{i+1}{file_extension}'
                            filepath = os.path.join(imagenes_dir, unique_filename)
                            
                            print(f"DEBUG: Guardando como: {unique_filename}")
                            archivo.save(filepath)
                            nombres_archivos.append(unique_filename)
                            print(f"DEBUG: Archivo guardado exitosamente: {unique_filename}")
                    
                    if nombres_archivos:
                        respuesta_campo.valor_archivo = ','.join(nombres_archivos)
                        print(f"DEBUG: Valor archivo guardado: {respuesta_campo.valor_archivo}")
                    else:
                        print(f"DEBUG: No se guardaron archivos para el campo {campo.id}")
                elif campo.tipo_campo == 'texto_informativo':
                    # Los campos informativos no tienen respuesta
                    continue
                
                db.session.add(respuesta_campo)
                campos_procesados += 1
                print(f"DEBUG: Campo {campo.id} ({campo.titulo}) procesado exitosamente")
            
            print(f"DEBUG: Total de campos procesados: {campos_procesados}")
            db.session.commit()
            print(f"DEBUG: Formulario guardado exitosamente en la base de datos")
            
            # Generar PDF automáticamente - USANDO LA FUNCIÓN ORIGINAL QUE FUNCIONABA
            print(f"DEBUG: Iniciando generación de PDF para respuesta {respuesta_formulario.id}")
            
            pdf_path = generar_pdf_formulario(respuesta_formulario)
            
            if pdf_path:
                respuesta_formulario.archivo_pdf = pdf_path
                db.session.commit()
                print(f"DEBUG: PDF generado exitosamente: {pdf_path}")
                
                # Redirigir a página de descarga
                flash('Formulario diligenciado y PDF generado exitosamente', 'success')
                return redirect(url_for('descargar_formulario_pdf', id=respuesta_formulario.id))
            else:
                print("DEBUG: Error al generar PDF")
                flash('Formulario diligenciado exitosamente, pero hubo un error al generar el PDF', 'warning')
                return redirect(url_for('formularios'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error al diligenciar formulario: ' + str(e), 'error')
    
    return render_template('diligenciar_formulario.html', formulario=formulario)

@app.route('/formularios/<int:id>/descargar-pdf')
@login_required
def descargar_formulario_pdf(id):
    """Descargar PDF del formulario diligenciado - compatible con móviles"""
    respuesta_formulario = RespuestaFormulario.query.get_or_404(id)
    
    # Verificar permisos
    if current_user.rol.nombre not in ['Administrador', 'Coordinador'] and respuesta_formulario.diligenciado_por != current_user.id:
        flash('No tienes permisos para acceder a este formulario', 'error')
        return redirect(url_for('formularios'))
    
    if not respuesta_formulario.archivo_pdf:
        flash('No se encontró el archivo PDF', 'error')
        return redirect(url_for('formularios'))
    
    # Buscar el archivo en la estructura: uploads/formularios/nombredelformulario/nombredeldocumento.pdf
    formulario_nombre = secure_filename(respuesta_formulario.formulario.nombre)
    pdf_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'formularios', formulario_nombre, respuesta_formulario.archivo_pdf)
    
    if not os.path.exists(pdf_filepath):
        flash('El archivo PDF no existe', 'error')
        return redirect(url_for('formularios'))
    
    # Mostrar página de descarga para todos los dispositivos (para poder redirigir)
    return render_template('descargar_pdf_mobile.html', 
                         pdf_url=url_for('descargar_formulario_pdf_file', id=id),
                         formulario_nombre=respuesta_formulario.formulario.nombre,
                         fecha=respuesta_formulario.fecha_diligenciamiento.strftime('%d/%m/%Y %H:%M'))

@app.route('/formularios/<int:id>/pdf-file')
@login_required
def descargar_formulario_pdf_file(id):
    """Servir el archivo PDF directamente"""
    respuesta_formulario = RespuestaFormulario.query.get_or_404(id)
    
    # Verificar permisos
    if current_user.rol.nombre not in ['Administrador', 'Coordinador'] and respuesta_formulario.diligenciado_por != current_user.id:
        abort(403)
    
    if not respuesta_formulario.archivo_pdf:
        abort(404)
    
    # Buscar el archivo en la estructura: uploads/formularios/nombredelformulario/nombredeldocumento.pdf
    formulario_nombre = secure_filename(respuesta_formulario.formulario.nombre)
    pdf_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'formularios', formulario_nombre, respuesta_formulario.archivo_pdf)
    
    if not os.path.exists(pdf_filepath):
        abort(404)
    
    # NO eliminar archivos de firma - mantener para inspección
    print(f"DEBUG: Archivos de firma mantenidos en uploads/formularios/firmas/ para inspección")
    
    return send_file(
        pdf_filepath,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=respuesta_formulario.archivo_pdf
    )

@app.route('/api/formularios/<int:id>/campos', methods=['POST'])
@login_required
def agregar_campo_formulario(id):
    """Agregar campo a un formulario - solo administradores"""
    if current_user.rol.nombre != 'Administrador':
        return jsonify({'success': False, 'message': 'No tienes permisos para realizar esta acción'})
    
    formulario = Formulario.query.get_or_404(id)
    
    data = request.get_json()
    tipo_campo = data.get('tipo_campo')
    titulo = data.get('titulo', '').strip()
    descripcion = data.get('descripcion', '').strip()
    obligatorio = data.get('obligatorio', False)
    configuracion = data.get('configuracion', {})
    
    if not titulo:
        return jsonify({'success': False, 'message': 'El título del campo es obligatorio'})
    
    # Obtener el siguiente orden
    ultimo_campo = CampoFormulario.query.filter_by(formulario_id=id).order_by(CampoFormulario.orden.desc()).first()
    siguiente_orden = (ultimo_campo.orden + 1) if ultimo_campo else 1
    
    # Crear nuevo campo
    campo = CampoFormulario(
        formulario_id=id,
        tipo_campo=tipo_campo,
        titulo=titulo,
        descripcion=descripcion,
        obligatorio=obligatorio,
        orden=siguiente_orden,
        configuracion=json.dumps(configuracion) if configuracion else None
    )
    
    try:
        db.session.add(campo)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Campo agregado exitosamente', 'campo_id': campo.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al agregar campo: {str(e)}'})

@app.route('/api/formularios/campos/<int:id>', methods=['PUT', 'DELETE'])
@login_required
def gestionar_campo_formulario(id):
    """Actualizar o eliminar campo de formulario - solo administradores"""
    if current_user.rol.nombre != 'Administrador':
        return jsonify({'success': False, 'message': 'No tienes permisos para realizar esta acción'})
    
    campo = CampoFormulario.query.get_or_404(id)
    
    if request.method == 'PUT':
        # Actualizar campo
        data = request.get_json()
        campo.titulo = data.get('titulo', campo.titulo).strip()
        campo.descripcion = data.get('descripcion', campo.descripcion).strip()
        campo.obligatorio = data.get('obligatorio', campo.obligatorio)
        campo.orden = data.get('orden', campo.orden)
        
        configuracion = data.get('configuracion')
        if configuracion is not None:
            campo.configuracion = json.dumps(configuracion) if configuracion else None
        
        try:
            db.session.commit()
            return jsonify({'success': True, 'message': 'Campo actualizado exitosamente'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Error al actualizar campo: {str(e)}'})
    
    elif request.method == 'DELETE':
        # Eliminar campo
        try:
            db.session.delete(campo)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Campo eliminado exitosamente'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Error al eliminar campo: {str(e)}'})

def generar_pdf_simple(respuesta_formulario):
    """Generar PDF del formulario diligenciado - VERSIÓN SIMPLIFICADA"""
    try:
        print(f"DEBUG: Generando PDF simple para formulario {respuesta_formulario.formulario.nombre}")
        
        buffer = io.BytesIO()
        
        from reportlab.lib.pagesizes import A4
        # Márgenes APA Colombia (aprox.): 2.54 cm = 72 * 1 inch = ~72 puntos
        apa_margin = 72  # 1 inch
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=apa_margin,
            rightMargin=apa_margin,
            topMargin=apa_margin,
            bottomMargin=apa_margin,
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        # Registrar Calibri si está disponible; fallback a Helvetica
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os
            calibri_paths = [
                r"C:\\Windows\\Fonts\\calibri.ttf",
                r"C:\\Windows\\Fonts\\Calibri.ttf",
            ]
            for p in calibri_paths:
                if os.path.exists(p):
                    pdfmetrics.registerFont(TTFont('Calibri', p))
                    break
            registered_fonts = set()
            try:
                registered_fonts = set(pdfmetrics.getRegisteredFontNames())
            except Exception:
                pass
            use_calibri = 'Calibri' in registered_fonts
        except Exception:
            use_calibri = False

        # Estilos simples
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=18,
            spaceAfter=20,
            alignment=1,
            textColor=colors.HexColor('#2c3e50'),
            fontName='Helvetica-Bold'
        )
        
        field_style = ParagraphStyle(
            'FieldStyle',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=10,
            spaceBefore=5,
            fontName=('Calibri' if use_calibri else 'Helvetica'),
            textColor=colors.HexColor('#2c3e50')
        )
        
        value_style = ParagraphStyle(
            'ValueStyle',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=15,
            fontName=('Calibri' if use_calibri else 'Helvetica'),
            textColor=colors.HexColor('#34495e'),
            leftIndent=20
        )
        
        # Encabezado con logo (igual que en incidencias)
        header_data = []
        logo_cell = obtener_logo_pdf(max_width=80, max_height=40)
        
        # Fecha de creación del formulario (estable)
        from datetime import datetime
        fecha_creacion = datetime.now().strftime("%d/%m/%Y")
        
        header_data.append([logo_cell, respuesta_formulario.formulario.nombre, f'Fecha: {fecha_creacion}'])
        
        header_table = Table(header_data, colWidths=[100, 220, 80])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (1, 0), (1, 0), 16),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (2, 0), (2, 0), 10),
            ('FONTNAME', (2, 0), (2, 0), 'Helvetica'),
            ('LINEBELOW', (0, 0), (-1, -1), 2, colors.black),
        ]))
        
        story.append(header_table)
        story.append(Spacer(1, 12))
        # Descripción del formulario (si existe)
        try:
            from xml.sax.saxutils import escape
            desc = getattr(respuesta_formulario.formulario, 'descripcion', '') or ''
            if isinstance(desc, str) and desc.strip():
                desc_html = escape(desc).replace('\n', '<br/>')
                from reportlab.lib.styles import ParagraphStyle
                desc_style = ParagraphStyle(
                    name='DescStyle',
                    parent=styles['Normal'],
                    fontName='Helvetica',
                    fontSize=10,
                    leading=13,
                    textColor=colors.HexColor('#34495e'),
                    spaceAfter=10,
                )
                story.append(Paragraph(f"<b>Descripción:</b> {desc_html}", desc_style))
                story.append(Spacer(1, 12))
            else:
                story.append(Spacer(1, 8))
        except Exception as e:
            print(f"DEBUG: No se pudo renderizar descripción: {e}")
            story.append(Spacer(1, 8))
        
        # Información del diligenciador
        info_text = f"""
        <b>Diligenciado por:</b> {respuesta_formulario.usuario.nombre}<br/>
        <b>Rol:</b> {respuesta_formulario.usuario.rol.nombre}<br/>
        <b>Fecha de diligenciamiento:</b> {respuesta_formulario.fecha_diligenciamiento.strftime('%d/%m/%Y %H:%M')}
        """
        
        story.append(Paragraph(info_text, field_style))
        story.append(Spacer(1, 20))
        
        # Campos del formulario - SIMPLIFICADO
        for campo in respuesta_formulario.formulario.campos:
            # Buscar la respuesta para este campo
            respuesta_campo = next((rc for rc in respuesta_formulario.respuestas_campos if rc.campo_id == campo.id), None)
            
            if not respuesta_campo:
                continue
            
            # Título del campo
            titulo_text = f"<b>{campo.titulo}</b>"
            if campo.obligatorio:
                titulo_text += " <i>(Obligatorio)</i>"
            
            story.append(Paragraph(titulo_text, field_style))
            
            # Valor del campo - SIMPLIFICADO
            valor = ""
            if campo.tipo_campo in ['texto', 'textarea', 'seleccion', 'seleccion_multiple']:
                valor = respuesta_campo.valor_texto or "Sin respuesta"
            elif campo.tipo_campo == 'fecha':
                valor = respuesta_campo.valor_fecha.strftime('%d/%m/%Y') if respuesta_campo.valor_fecha else "Sin fecha"
            elif campo.tipo_campo == 'firma':
                if respuesta_campo.valor_archivo:
                    # Información del firmante
                    info_firmante = []
                    if hasattr(respuesta_campo, 'nombre_firmante') and respuesta_campo.nombre_firmante:
                        info_firmante.append(f"<b>Nombre:</b> {respuesta_campo.nombre_firmante}")
                    if hasattr(respuesta_campo, 'documento_firmante') and respuesta_campo.documento_firmante:
                        info_firmante.append(f"<b>Documento:</b> {respuesta_campo.documento_firmante}")
                    if hasattr(respuesta_campo, 'telefono_firmante') and respuesta_campo.telefono_firmante:
                        info_firmante.append(f"<b>Teléfono:</b> {respuesta_campo.telefono_firmante}")
                    if hasattr(respuesta_campo, 'empresa_firmante') and respuesta_campo.empresa_firmante:
                        info_firmante.append(f"<b>Empresa:</b> {respuesta_campo.empresa_firmante}")
                    if hasattr(respuesta_campo, 'cargo_firmante') and respuesta_campo.cargo_firmante:
                        info_firmante.append(f"<b>Cargo:</b> {respuesta_campo.cargo_firmante}")
                    
                    valor = "<br/>".join(info_firmante) if info_firmante else "Firma digital registrada"
                    
                    # Agregar la imagen de la firma (SIMPLIFICADO COMO INCIDENCIAS)
                    try:
                        import base64
                        print(f"DEBUG SIMPLE: Procesando firma para campo {campo.id}")
                        print(f"DEBUG SIMPLE: Valor archivo length: {len(respuesta_campo.valor_archivo) if respuesta_campo.valor_archivo else 0}")
                        
                        if respuesta_campo.valor_archivo.startswith('data:image'):
                            firma_data = respuesta_campo.valor_archivo.split(',')[1]
                            print(f"DEBUG SIMPLE: Firma en formato data:image detectada")
                        else:
                            firma_data = respuesta_campo.valor_archivo
                            print(f"DEBUG SIMPLE: Firma en formato base64 directo")
                        
                        # Limpiar y agregar padding
                        firma_data = firma_data.strip()
                        missing_padding = len(firma_data) % 4
                        if missing_padding:
                            firma_data += '=' * (4 - missing_padding)
                        
                        try:
                            print(f"DEBUG SIMPLE: Intentando decodificar base64...")
                            firma_bytes = base64.b64decode(firma_data)
                            print(f"DEBUG SIMPLE: Base64 decodificado exitosamente, tamaño: {len(firma_bytes)} bytes")
                            
                            # Validar que el archivo no esté vacío
                            if len(firma_bytes) == 0:
                                raise ValueError("Archivo de firma vacío")
                                
                            # Validar que tenga el header de imagen PNG
                            if not firma_bytes.startswith(b'\x89PNG'):
                                print(f"DEBUG SIMPLE: Advertencia - El archivo no parece ser PNG válido")
                                
                        except Exception as decode_error:
                            print(f"ERROR SIMPLE: Error decodificando base64: {decode_error}")
                            error_text = f"<b>Error:</b> Datos de firma inválidos o corruptos"
                            error_paragraph = Paragraph(error_text, value_style)
                            story.append(error_paragraph)
                            continue
                        
                        # Crear imagen temporal
                        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_firma_{campo.id}.png')
                        with open(temp_path, 'wb') as f:
                            f.write(firma_bytes)
                        
                        print(f"DEBUG SIMPLE: Archivo temporal creado: {temp_path}")
                        
                        # Procesar imagen EXACTAMENTE como en incidencias
                        try:
                            with PILImage.open(temp_path) as img:
                                print(f"DEBUG SIMPLE: Imagen abierta exitosamente - Dimensiones: {img.width}x{img.height}")
                                # Verificar que la imagen se puede cargar completamente
                                img.verify()
                                print(f"DEBUG SIMPLE: Imagen verificada exitosamente")
                                
                                # Reabrir la imagen después de verify() (verify() cierra el archivo)
                                img = PILImage.open(temp_path)
                                
                            # Calcular dimensiones para visualización (sin redimensionar la imagen)
                            max_width_cm = 3  # cm
                            max_height_cm = 2  # cm
                            max_width_points = max_width_cm * 28.35  # convertir cm a puntos
                            max_height_points = max_height_cm * 28.35
                            
                            if img.width > max_width_points or img.height > max_height_points:
                                ratio = min(max_width_points/img.width, max_height_points/img.height)
                                new_width = int(img.width * ratio)
                                new_height = int(img.height * ratio)
                            else:
                                new_width = img.width
                                new_height = img.height
                            
                            # Guardar imagen temporalmente con máxima calidad y DPI original
                            img.save(temp_path, quality=100, optimize=False)
                            
                            # Agregar espacio antes de la imagen
                            story.append(Spacer(1, 10))
                            
                            # Crear leyenda mejorada
                            caption_text = f"Firma Digital - {campo.titulo}"
                            caption = Paragraph(caption_text, value_style)
                            story.append(caption)
                            
                            # Agregar imagen centrada con borde usando dimensiones más grandes para mejor resolución
                            pdf_image = Image(temp_path, width=new_width*2, height=new_height*2)
                            
                            # Crear tabla para centrar la imagen con borde
                            image_table = Table([[pdf_image]], colWidths=[new_width*2])
                            image_table.setStyle(TableStyle([
                                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                                ('BOX', (0, 0), (0, 0), 1, colors.HexColor('#bdc3c7')),
                                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f8f9fa')),
                            ]))
                            
                            story.append(image_table)
                            
                            # NO eliminar archivo temporal aquí - se eliminará después de generar el PDF
                            
                        except PILImage.UnidentifiedImageError as img_error:
                            print(f"ERROR SIMPLE: Imagen no identificada para firma {campo.id}: {img_error}")
                            error_text = f"<b>Error:</b> Imagen de firma no válida o corrupta"
                            error_paragraph = Paragraph(error_text, value_style)
                            story.append(error_paragraph)
                            continue
                        except Exception as img_error:
                            print(f"ERROR SIMPLE: Error verificando imagen de firma {campo.id}: {img_error}")
                            error_text = f"<b>Error:</b> Imagen de firma corrupta o incompleta"
                            error_paragraph = Paragraph(error_text, value_style)
                            story.append(error_paragraph)
                            continue
                            
                    except Exception as e:
                        print(f"Error procesando firma {campo.id}: {e}")
                        continue
                else:
                    valor = "Sin firma"
            elif campo.tipo_campo == 'foto':
                if respuesta_campo.valor_archivo:
                    fotos_list = respuesta_campo.valor_archivo.split(',')
                    valor = f"{len(fotos_list)} foto(s) adjunta(s)"
                    
                    # Agregar las fotos (igual que en incidencias)
                    contador_imagen = 1
                    for foto_filename in fotos_list:
                        foto_filename = foto_filename.strip()
                        # Buscar foto en la nueva ubicación organizada
                        formulario_nombre = secure_filename("formularios")
                        imagenes_dir = os.path.join(app.config['UPLOAD_FOLDER'], formulario_nombre, 'imagenes')
                        foto_path = os.path.join(imagenes_dir, foto_filename)
                        
                        if os.path.exists(foto_path):
                            try:
                                with PILImage.open(foto_path) as img:
                                    # Calcular dimensiones para visualización (sin redimensionar la imagen)
                                    max_width = 500
                                    max_height = 400
                                    
                                    if img.width > max_width or img.height > max_height:
                                        ratio = min(max_width/img.width, max_height/img.height)
                                        new_width = int(img.width * ratio)
                                        new_height = int(img.height * ratio)
                                    else:
                                        new_width = img.width
                                        new_height = img.height
                                    
                                    # Guardar imagen temporalmente con máxima calidad y DPI original
                                    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{foto_filename}')
                                    img.save(temp_path, quality=100, optimize=False)
                                    
                                    # Agregar al PDF
                                    story.append(Spacer(1, 10))
                                    caption_text = f"Figura {contador_imagen}. {foto_filename.replace('_', ' ').replace('.jpg', '').replace('.png', '').replace('.jpeg', '').title()}"
                                    caption = Paragraph(caption_text, value_style)
                                    story.append(caption)
                                    
                                    pdf_image = Image(temp_path, width=new_width*2, height=new_height*2)
                                    image_table = Table([[pdf_image]], colWidths=[new_width*2])
                                    image_table.setStyle(TableStyle([
                                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                                        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                                        ('BOX', (0, 0), (0, 0), 1, colors.HexColor('#bdc3c7')),
                                        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f8f9fa')),
                                    ]))
                                    
                                    story.append(image_table)
                                    contador_imagen += 1
                                    os.remove(temp_path)
                                    
                            except Exception as e:
                                print(f"Error procesando imagen {foto_filename}: {e}")
                                continue
                        else:
                            print(f"Archivo no encontrado: {foto_path}")
                            continue
                else:
                    valor = "Sin fotos"
            
            story.append(Paragraph(valor, value_style))
        
        # Pie de página
        story.append(Spacer(1, 30))
        footer_text = """
        <para align=center>
        <font name="Helvetica" size="9" color="#666666">
        Formulario generado automáticamente por el Sistema ERP BACS<br/>
        Building Automation and Control System
        </font>
        </para>
        """
        story.append(Paragraph(footer_text, styles['Normal']))
        
        # Construir el PDF
        doc.build(story)
        buffer.seek(0)
        
        # Guardar archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'formulario_{respuesta_formulario.formulario.nombre}_{respuesta_formulario.id}_{timestamp}.pdf'
        filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        print(f"DEBUG: Guardando PDF simple en: {filepath}")
        with open(filepath, 'wb') as f:
            f.write(buffer.getvalue())
        
        print(f"DEBUG: PDF simple generado exitosamente: {filename}")
        return filename
        
    except Exception as e:
        print(f"DEBUG: Error generando PDF simple: {e}")
        import traceback
        traceback.print_exc()
        return None


def procesar_firma_con_metodos_alternativos(firma_bytes, temp_path):
    """Intentar procesar firma con métodos alternativos para imágenes truncadas"""
    try:
        # Método 1: Usar PIL con configuración para imágenes truncadas
        from PIL import ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        
        img = PILImage.open(io.BytesIO(firma_bytes))
        img.save(temp_path, format='PNG', quality=100, optimize=False)
        return img, temp_path
        
    except Exception as e:
        print(f"DEBUG: Método PIL con LOAD_TRUNCATED_IMAGES falló: {e}")
        
        try:
            # Método 2: Intentar reconstruir la imagen manualmente
            # Buscar el final de la imagen PNG
            if firma_bytes.startswith(b'\x89PNG'):
                # PNG termina con IEND
                end_marker = b'IEND\xaeB`\x82'
                end_pos = firma_bytes.rfind(end_marker)
                if end_pos != -1:
                    # Reconstruir PNG completo
                    reconstructed = firma_bytes[:end_pos + len(end_marker)]
                    img = PILImage.open(io.BytesIO(reconstructed))
                    img.save(temp_path, format='PNG', quality=100, optimize=False)
                    return img, temp_path
                else:
                    # Si no encuentra el marcador de fin, intentar truncar en un punto razonable
                    print(f"DEBUG: No se encontró marcador de fin PNG, intentando truncar...")
                    # Buscar el último chunk válido
                    pos = 8  # Saltar header PNG
                    while pos < len(firma_bytes) - 8:
                        if pos + 8 > len(firma_bytes):
                            break
                        chunk_length = int.from_bytes(firma_bytes[pos:pos+4], 'big')
                        chunk_type = firma_bytes[pos+4:pos+8]
                        if chunk_type == b'IEND':
                            reconstructed = firma_bytes[:pos+8+4]  # Incluir CRC
                            img = PILImage.open(io.BytesIO(reconstructed))
                            img.save(temp_path, format='PNG', quality=100, optimize=False)
                            return img, temp_path
                        pos += 8 + chunk_length + 4  # Saltar al siguiente chunk
            
            # Si no es PNG, intentar con JPEG
            elif firma_bytes.startswith(b'\xff\xd8\xff'):
                # JPEG termina con FFD9
                end_marker = b'\xff\xd9'
                end_pos = firma_bytes.rfind(end_marker)
                if end_pos != -1:
                    reconstructed = firma_bytes[:end_pos + len(end_marker)]
                    img = PILImage.open(io.BytesIO(reconstructed))
                    img.save(temp_path, format='PNG', quality=100, optimize=False)
                    return img, temp_path
                    
        except Exception as e2:
            print(f"DEBUG: Método de reconstrucción falló: {e2}")
        
        # Método 3: Crear imagen placeholder si todo falla
        try:
            print(f"DEBUG: Creando imagen placeholder...")
            placeholder = PILImage.new('RGB', (400, 200), color='white')
            
            # Agregar texto indicando que es una firma
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(placeholder)
            
            # Intentar usar una fuente, si no está disponible usar la por defecto
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            text = "FIRMA DIGITAL"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (400 - text_width) // 2
            y = (200 - text_height) // 2
            
            draw.text((x, y), text, fill='black', font=font)
            draw.rectangle([10, 10, 390, 190], outline='gray', width=2)
            
            placeholder.save(temp_path, format='PNG', quality=100, optimize=False)
            return placeholder, temp_path
            
        except Exception as e3:
            print(f"DEBUG: Método placeholder falló: {e3}")
            raise e3


def generar_pdf_formulario(respuesta_formulario):
    """Generar PDF del formulario diligenciado - Formato simple como el ejemplo deseado"""
    try:
        print(f"DEBUG: Iniciando generación de PDF para formulario {respuesta_formulario.formulario.nombre}")
        buffer = io.BytesIO()
        
        from reportlab.lib.pagesizes import A4
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              leftMargin=40, rightMargin=40,
                              topMargin=40, bottomMargin=40)
        
        styles = getSampleStyleSheet()
        story = []
        
        # Registrar Calibri si está disponible; de lo contrario, usar Helvetica
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os
            # Intentos comunes de ruta para Windows
            calibri_paths = [
                r"C:\\Windows\\Fonts\\calibri.ttf",
                r"C:\\Windows\\Fonts\\Calibri.ttf",
            ]
            for p in calibri_paths:
                if os.path.exists(p):
                    pdfmetrics.registerFont(TTFont('Calibri', p))
                    break
        except Exception as font_err:
            print(f"DEBUG: No se pudo registrar Calibri, usando Helvetica. Detalle: {font_err}")

        # Estilos personalizados
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=18,
            spaceAfter=20,
            alignment=1,
            textColor=colors.HexColor('#2c3e50'),
            fontName='Helvetica-Bold'
        )
        
        field_style = ParagraphStyle(
            'FieldStyle',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=10,
            spaceBefore=5,
            fontName='Calibri' if 'Calibri' in locals() or 'Calibri' in globals() else 'Helvetica',
            textColor=colors.HexColor('#2c3e50')
        )
        
        value_style = ParagraphStyle(
            'ValueStyle',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=15,
            fontName='Calibri' if 'Calibri' in locals() or 'Calibri' in globals() else 'Helvetica',
            textColor=colors.HexColor('#34495e'),
            leftIndent=20
        )
        
        # ========================================
        # ENCABEZADO DEL PDF (tabla 3 celdas: logo | título | versión/fecha)
        # ========================================
        header_data = []
        logo_cell = obtener_logo_pdf(max_width=70, max_height=35)
        
        # Fecha de creación del formulario (estable)
        from datetime import datetime
        fecha_creacion = datetime.now().strftime("%d/%m/%Y")  # editable manualmente luego si deseas
        version_text = "Versión: 1"

        # Celdas como Paragraph para controlar alineaciones
        titulo_para = Paragraph(f"<para align=center><b>{respuesta_formulario.formulario.nombre}</b></para>", styles['Title'])
        derecha_para = Paragraph(f"<para align=right>{version_text}<br/>Fecha: {fecha_creacion}</para>", styles['Normal'])

        header_data.append([logo_cell, titulo_para, derecha_para])
        
        # Anchos más generosos para el título centrado
        header_table = Table(header_data, colWidths=[80, 360, 130])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),      # Logo a la izquierda
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),    # Título centrado
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),     # Fecha a la derecha
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (1, 0), (1, 0), 16),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (2, 0), (2, 0), 10),
            ('FONTNAME', (2, 0), (2, 0), 'Helvetica'),
            ('LINEBELOW', (0, 0), (-1, -1), 2, colors.black),
        ]))
        # ========================================
        # FIN ENCABEZADO
        # ========================================
        
        story.append(header_table)
        story.append(Spacer(1, 12))
        # Descripción del formulario (simple)
        try:
            from xml.sax.saxutils import escape
            desc = getattr(respuesta_formulario.formulario, 'descripcion', '') or ''
            if isinstance(desc, str) and desc.strip():
                desc_html = escape(desc).replace('\n', '<br/>')
                story.append(Paragraph(f"<b>Descripción:</b> {desc_html}", value_style))
                story.append(Spacer(1, 14))
            else:
                story.append(Spacer(1, 8))
        except Exception:
            story.append(Spacer(1, 8))
        
        # Información del diligenciador
        info_text = f"""
        <b>Diligenciado por:</b> {respuesta_formulario.usuario.nombre}<br/>
        <b>Fecha de diligenciamiento:</b> {respuesta_formulario.fecha_diligenciamiento.strftime('%d/%m/%Y %H:%M')}
        """
        
        info_paragraph = Paragraph(info_text, field_style)
        story.append(info_paragraph)
        story.append(Spacer(1, 20))
        
        # Campos del formulario
        print(f"DEBUG: Procesando {len(respuesta_formulario.formulario.campos)} campos del formulario")
        for campo in respuesta_formulario.formulario.campos:
            print(f"DEBUG: Procesando campo {campo.id} - {campo.titulo} - Tipo: {campo.tipo_campo}")
            
            # Buscar la respuesta para este campo
            respuesta_campo = next((rc for rc in respuesta_formulario.respuestas_campos if rc.campo_id == campo.id), None)
            
            if not respuesta_campo:
                print(f"DEBUG: No se encontró respuesta para el campo {campo.id}")
                continue
            
            print(f"DEBUG: Respuesta encontrada para campo {campo.id}")
            if campo.tipo_campo in ['foto', 'firma']:
                print(f"DEBUG: Valor archivo: {respuesta_campo.valor_archivo[:100] if respuesta_campo.valor_archivo else 'None'}...")
            
            # Título del campo
            titulo_text = f"<b>{campo.titulo}</b>"
            if campo.obligatorio:
                titulo_text += " <i>(Obligatorio)</i>"
            
            titulo_paragraph = Paragraph(titulo_text, field_style)
            story.append(titulo_paragraph)
            
            # Valor del campo
            valor = ""
            if campo.tipo_campo in ['texto', 'textarea', 'seleccion', 'seleccion_multiple']:
                valor = respuesta_campo.valor_texto or "Sin respuesta"
            elif campo.tipo_campo == 'fecha':
                valor = respuesta_campo.valor_fecha.strftime('%d/%m/%Y') if respuesta_campo.valor_fecha else "Sin fecha"
            elif campo.tipo_campo == 'firma':
                print(f"DEBUG: Procesando campo de firma {campo.id} - {campo.titulo}")
                
                # Información del firmante (verificar si los campos existen)
                info_firmante = []
                try:
                    print(f"DEBUG: Verificando datos del firmante para campo {campo.id}")
                    print(f"DEBUG: nombre_firmante: {getattr(respuesta_campo, 'nombre_firmante', 'None')}")
                    print(f"DEBUG: documento_firmante: {getattr(respuesta_campo, 'documento_firmante', 'None')}")
                    print(f"DEBUG: empresa_firmante: {getattr(respuesta_campo, 'empresa_firmante', 'None')}")
                    print(f"DEBUG: cargo_firmante: {getattr(respuesta_campo, 'cargo_firmante', 'None')}")
                    
                    if hasattr(respuesta_campo, 'nombre_firmante') and respuesta_campo.nombre_firmante:
                        info_firmante.append(f"<b>Nombre:</b> {respuesta_campo.nombre_firmante}")
                    if hasattr(respuesta_campo, 'documento_firmante') and respuesta_campo.documento_firmante:
                        info_firmante.append(f"<b>Documento:</b> {respuesta_campo.documento_firmante}")
                    if hasattr(respuesta_campo, 'telefono_firmante') and respuesta_campo.telefono_firmante:
                        info_firmante.append(f"<b>Teléfono:</b> {respuesta_campo.telefono_firmante}")
                    if hasattr(respuesta_campo, 'empresa_firmante') and respuesta_campo.empresa_firmante:
                        info_firmante.append(f"<b>Empresa:</b> {respuesta_campo.empresa_firmante}")
                    if hasattr(respuesta_campo, 'cargo_firmante') and respuesta_campo.cargo_firmante:
                        info_firmante.append(f"<b>Cargo:</b> {respuesta_campo.cargo_firmante}")
                        
                    print(f"DEBUG: Info firmante encontrada: {len(info_firmante)} campos")
                except AttributeError as e:
                    print(f"DEBUG: Error accediendo a datos del firmante: {e}")
                    pass
                
                valor = "<br/>".join(info_firmante) if info_firmante else "Firma digital"
                
                # Procesar imagen de la firma
                if respuesta_campo.valor_archivo:
                    try:
                        # Construir información del firmante (en filas)
                        lineas_info = []
                        if respuesta_campo.nombre_firmante:
                            lineas_info.append(f"<b>Nombre:</b> {respuesta_campo.nombre_firmante}")
                        if respuesta_campo.documento_firmante:
                            lineas_info.append(f"<b>Documento:</b> {respuesta_campo.documento_firmante}")
                        if respuesta_campo.empresa_firmante:
                            lineas_info.append(f"<b>Empresa:</b> {respuesta_campo.empresa_firmante}")
                        if respuesta_campo.cargo_firmante:
                            lineas_info.append(f"<b>Cargo:</b> {respuesta_campo.cargo_firmante}")
                        if respuesta_campo.telefono_firmante:
                            lineas_info.append(f"<b>Teléfono:</b> {respuesta_campo.telefono_firmante}")

                        info_para = Paragraph("<br/>".join(lineas_info) if lineas_info else "Sin datos del firmante", value_style)

                        # Determinar ruta de la firma PNG
                        posible_path = os.path.join(app.config['UPLOAD_FOLDER'], respuesta_campo.valor_archivo) if not os.path.isabs(respuesta_campo.valor_archivo) else respuesta_campo.valor_archivo
                        png_path = None
                        if os.path.exists(posible_path):
                            png_path = posible_path
                            print(f"DEBUG: Firma para tabla (ruta existente): {png_path}")
                        else:
                            # Fallback: si viniera base64, decodificar y guardar
                            import base64
                            from io import BytesIO
                            if ',' in respuesta_campo.valor_archivo:
                                _, encoded = respuesta_campo.valor_archivo.split(',', 1)
                            else:
                                encoded = respuesta_campo.valor_archivo
                            image_bytes = base64.b64decode(encoded)
                            img = PILImage.open(BytesIO(image_bytes)).convert('RGBA')
                            bg = PILImage.new("RGB", img.size, (255, 255, 255))
                            bg.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                            firmas_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'formularios', 'firmas')
                            os.makedirs(firmas_dir, exist_ok=True)
                            from datetime import datetime
                            png_path = os.path.join(firmas_dir, f'firma_{campo.id}_{respuesta_formulario.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                            bg.save(png_path, format='PNG')
                            print(f"DEBUG: Firma guardada en fallback para tabla: {png_path}")

                        # Crear imagen escalada de firma
                        from reportlab.lib.pagesizes import A4
                        img_tmp = PILImage.open(png_path)
                        img_w, img_h = img_tmp.size
                        page_w, _ = A4
                        max_width = min(page_w * 0.4, 300)
                        scale = max_width / img_w
                        draw_w = img_w * scale
                        draw_h = img_h * scale
                        firma_image = Image(png_path, width=draw_w, height=draw_h)

                        # Crear tabla 2 columnas: info (izq) | firma (der)
                        tabla = Table([[info_para, firma_image]], colWidths=[page_w - max_width - 60, max_width])
                        tabla.setStyle(TableStyle([
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                            ('LEFTPADDING', (0, 0), (-1, -1), 6),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                            ('TOPPADDING', (0, 0), (-1, -1), 6),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#2c3e50')),
                        ]))
                        story.append(tabla)
                        story.append(Spacer(1, 12))

                        valor = ""
                        
                    except Exception as firma_error:
                        print(f"ERROR: Error procesando firma: {firma_error}")
                        error_text = f"<b>Firma Digital:</b> Error procesando imagen ({str(firma_error)[:50]}...)"
                        error_paragraph = Paragraph(error_text, value_style)
                        story.append(error_paragraph)
                        valor = "Error en firma"
                else:
                    valor = "Sin firma"
            elif campo.tipo_campo == 'foto':
                if respuesta_campo.valor_archivo:
                    fotos_list = respuesta_campo.valor_archivo.split(',')
                    valor = f"{len(fotos_list)} foto(s) adjunta(s)"
                    
                    # Agregar título "Registro Fotográfico" solo una vez
                    story.append(Spacer(1, 15))
                    titulo_fotos = Paragraph("<b>Registro Fotográfico</b>", field_style)
                    story.append(titulo_fotos)
                    story.append(Spacer(1, 10))
                    
                    # Procesar fotos con redimensionamiento inteligente
                    for foto_filename in fotos_list:
                        foto_filename = foto_filename.strip()
                        # Buscar foto en la nueva ubicación organizada
                        formulario_nombre = secure_filename("formularios")
                        imagenes_dir = os.path.join(app.config['UPLOAD_FOLDER'], formulario_nombre, 'imagenes')
                        foto_path = os.path.join(imagenes_dir, foto_filename)
                        
                        if os.path.exists(foto_path):
                            try:
                                # Verificar si es una imagen
                                with PILImage.open(foto_path) as img:
                                    # Redimensionar según orientación (6cm = ~170 puntos para mejor resolución)
                                    max_width_cm = 6  # cm
                                    max_height_cm = 6  # cm
                                    max_width_points = max_width_cm * 28.35  # convertir cm a puntos
                                    max_height_points = max_height_cm * 28.35
                                    
                                    # Determinar orientación y aplicar reglas
                                    aspect_ratio = img.width / img.height
                                    
                                    if aspect_ratio > 1.1:  # Horizontal (más ancho que alto)
                                        # Limitar altura a 4cm
                                        if img.height > max_height_points:
                                            ratio = max_height_points / img.height
                                            new_width = int(img.width * ratio)
                                            new_height = int(img.height * ratio)
                                        else:
                                            new_width = img.width
                                            new_height = img.height
                                    elif aspect_ratio < 0.9:  # Vertical (más alto que ancho)
                                        # Limitar ancho a 4cm
                                        if img.width > max_width_points:
                                            ratio = max_width_points / img.width
                                            new_width = int(img.width * ratio)
                                            new_height = int(img.height * ratio)
                                        else:
                                            new_width = img.width
                                            new_height = img.height
                                    else:  # Cuadrada (1:1)
                                        # Limitar a 5x5cm
                                        max_size_cm = 5
                                        max_size_points = max_size_cm * 28.35
                                        if img.width > max_size_points or img.height > max_size_points:
                                            ratio = min(max_size_points/img.width, max_size_points/img.height)
                                            new_width = int(img.width * ratio)
                                            new_height = int(img.height * ratio)
                                        else:
                                            new_width = img.width
                                            new_height = img.height
                                    
                                    # NO redimensionar la imagen - mantener resolución original
                                    # Solo ajustar el tamaño de visualización en el PDF
                                    
                                    # Buscar imagen en la nueva ubicación organizada
                                    formulario_nombre = secure_filename("formularios")
                                    imagenes_dir = os.path.join(app.config['UPLOAD_FOLDER'], formulario_nombre, 'imagenes')
                                    original_path = os.path.join(imagenes_dir, foto_filename)
                                    
                                    # Guardar imagen temporalmente con máxima calidad y DPI original
                                    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{foto_filename}')
                                    img.save(temp_path, quality=100, optimize=False)
                                    
                                    # Agregar imagen centrada con borde usando dimensiones calculadas
                                    pdf_image = Image(temp_path, width=new_width, height=new_height)
                                    
                                    # Crear tabla para centrar la imagen con borde
                                    image_table = Table([[pdf_image]], colWidths=[new_width])
                                    image_table.setStyle(TableStyle([
                                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                                        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                                        ('BOX', (0, 0), (0, 0), 1, colors.HexColor('#bdc3c7')),
                                        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f8f9fa')),
                                    ]))
                                    
                                    story.append(image_table)
                                    story.append(Spacer(1, 10))  # Espacio entre fotos
                                    
                                    # NO eliminar archivo temporal aquí - se eliminará después de generar el PDF
                                    
                            except Exception as e:
                                print(f"Error procesando imagen {foto_filename}: {e}")
                                continue
                else:
                    valor = ""
            
            valor_paragraph = Paragraph(valor, value_style)
            story.append(valor_paragraph)
        
        # Pie de página
        story.append(Spacer(1, 30))
        footer_text = f"""
        <para align=center>
        <font name="Helvetica" size="9" color="#666666">
        Formulario generado automáticamente por el Sistema ERP BACS<br/>
        Building Automation and Control System
        </font>
        </para>
        """
        footer = Paragraph(footer_text, styles['Normal'])
        story.append(footer)
        
        # Construir el PDF
        doc.build(story)
        buffer.seek(0)
        
        # Guardar archivo en la estructura solicitada: uploads/formularios/nombredelformulario/nombredeldocumento.pdf
        formulario_nombre = secure_filename(respuesta_formulario.formulario.nombre)
        documento_nombre = f'documento_{respuesta_formulario.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        # Crear directorio si no existe
        formulario_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'formularios', formulario_nombre)
        os.makedirs(formulario_dir, exist_ok=True)
        
        filepath = os.path.join(formulario_dir, documento_nombre)
        
        print(f"DEBUG: Guardando PDF en: {filepath}")
        with open(filepath, 'wb') as f:
            f.write(buffer.getvalue())
        
        print(f"DEBUG: PDF generado exitosamente: {documento_nombre}")
        
        # Limpiar archivos temporales después de generar el PDF
        try:
            import glob
            # Patrones de archivos temporales que generamos (EXCEPTO firma_* que se limpia después)
            patterns = ['temp_*', 'firma_respaldo_*']
            for pattern in patterns:
                temp_files = glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], pattern))
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        print(f"DEBUG: Archivo temporal eliminado: {temp_file}")
        except Exception as cleanup_error:
            print(f"DEBUG: Error limpiando archivos temporales: {cleanup_error}")
        
        # NO eliminar archivos de firma - mantener para inspección
        print(f"DEBUG: Archivos de firma mantenidos en uploads/formularios/firmas/ para inspección")
        
        return documento_nombre
        
    except Exception as e:
        print(f"Error generando PDF del formulario: {e}")
        import traceback
        traceback.print_exc()
        
        
        return None

def procesar_firma_imagen(firma_data, campo, story, value_style):
    """Procesar firma como imagen y agregarla al PDF - Solución simple y robusta"""
    temp_path = None
    try:
        import base64
        import datetime
        import io
        from PIL import Image as PILImage
        from reportlab.platypus import Image
        from reportlab.lib.utils import ImageReader
        
        print(f"DEBUG: Procesando imagen de firma para campo {campo.id}")
        print(f"DEBUG: Longitud de datos base64: {len(firma_data)}")
        
        # Configurar PIL para manejar imágenes truncadas
        from PIL import ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        
        # Extraer datos base64
        if ',' in firma_data:
            base64_data = firma_data.split(',')[1]
            print(f"DEBUG: Datos base64 extraídos, longitud: {len(base64_data)}")
        else:
            base64_data = firma_data
            print(f"DEBUG: Usando datos base64 directos")
        
        # Limpiar y agregar padding si es necesario
        base64_data = base64_data.strip()
        missing_padding = len(base64_data) % 4
        if missing_padding:
            base64_data += '=' * (4 - missing_padding)
            print(f"DEBUG: Padding agregado, nueva longitud: {len(base64_data)}")
        
        # Decodificar base64
        try:
            firma_bytes = base64.b64decode(base64_data, validate=True)
            print(f"DEBUG: Base64 decodificado exitosamente, tamaño: {len(firma_bytes)} bytes")
        except Exception as e:
            print(f"DEBUG: Error en decodificación con validación: {e}")
            firma_bytes = base64.b64decode(base64_data, validate=False)
            print(f"DEBUG: Base64 decodificado sin validación, tamaño: {len(firma_bytes)} bytes")
        
        # Crear archivo temporal único
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        temp_filename = f'temp_firma_{campo.id}_{timestamp}.png'
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        
        # Guardar imagen temporal
        with open(temp_path, 'wb') as f:
            f.write(firma_bytes)
        
        # Verificar que el archivo se creó
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            raise ValueError("No se pudo crear el archivo temporal")
        
        print(f"DEBUG: Archivo temporal creado: {temp_path}, tamaño: {os.path.getsize(temp_path)} bytes")
        
        # PROCESAMIENTO SIMPLE Y ROBUSTO
        try:
            img = PILImage.open(temp_path)
            print(f"DEBUG: Imagen original - Modo: {img.mode}, Dimensiones: {img.width}x{img.height}")
            
            # Convertir a RGB si es necesario
            if img.mode == 'RGBA':
                print(f"DEBUG: Convirtiendo RGBA a RGB con fondo blanco")
                background = PILImage.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != 'RGB':
                print(f"DEBUG: Convirtiendo de {img.mode} a RGB")
                img = img.convert('RGB')
            
            # PROCESAMIENTO INTELIGENTE: Detectar automáticamente el mejor método
            print(f"DEBUG: Analizando imagen para determinar el mejor procesamiento")
            
            # Convertir a escala de grises para análisis
            gray_img = img.convert('L')
            
            # Analizar el histograma para entender la imagen
            histogram = gray_img.histogram()
            total_pixels = sum(histogram)
            
            # Contar píxeles oscuros (0-50) y claros (200-255)
            dark_pixels = sum(histogram[0:51])
            light_pixels = sum(histogram[200:256])
            
            dark_percentage = (dark_pixels / total_pixels) * 100
            light_percentage = (light_pixels / total_pixels) * 100
            
            print(f"DEBUG: Análisis - Oscuros: {dark_percentage:.1f}%, Claros: {light_percentage:.1f}%")
            
            # Decidir el mejor método basado en el análisis
            if dark_percentage > 5:  # Hay suficiente contenido oscuro (firma negra)
                print(f"DEBUG: Firma negra detectada, usando imagen original")
                img_resized = img  # Usar imagen original
            elif light_percentage > 80:  # Imagen muy clara (firma blanca/gris)
                print(f"DEBUG: Firma clara detectada, invirtiendo colores")
                img_resized = PILImage.eval(img, lambda x: 255 - x)  # Invertir
            else:  # Caso intermedio
                print(f"DEBUG: Caso intermedio, aplicando contraste")
                # Aumentar contraste
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(img)
                img_resized = enhancer.enhance(2.0)
            
            # Dimensiones para ReportLab
            target_width = img_resized.width
            target_height = img_resized.height
            
            # Guardar imagen procesada
            img_resized.save(temp_path, format='PNG', quality=100, optimize=False)
            print(f"DEBUG: Imagen procesada guardada - Dimensiones: {target_width}x{target_height}")
            
            # Verificar que el archivo se guardó correctamente
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise ValueError("No se pudo guardar la imagen procesada")
            
            print(f"DEBUG: Archivo guardado verificado - Tamaño: {os.path.getsize(temp_path)} bytes")
            
            # Agregar al PDF
            story.append(Spacer(1, 10))
            
            # Agregar leyenda para la firma
            firma_leyenda = Paragraph("<b>Firma Digital:</b>", value_style)
            story.append(firma_leyenda)
            story.append(Spacer(1, 5))
            
            # Usar dimensiones fijas para mejor compatibilidad con ReportLab
            display_width = target_width
            display_height = target_height
            
            # Crear imagen para ReportLab de manera directa
            try:
                # Verificar que el archivo existe y tiene contenido
                if not os.path.exists(temp_path):
                    raise ValueError("Archivo temporal no existe")
                
                file_size = os.path.getsize(temp_path)
                if file_size == 0:
                    raise ValueError("Archivo temporal está vacío")
                
                print(f"DEBUG: Archivo verificado - Tamaño: {file_size} bytes")
                
                # Crear imagen para ReportLab usando dimensiones originales
                # Limitar el tamaño máximo para que quepa en el PDF
                max_width = 500
                max_height = 300
                
                if target_width > max_width or target_height > max_height:
                    # Calcular proporción para mantener aspecto
                    ratio = min(max_width/target_width, max_height/target_height)
                    display_width = int(target_width * ratio)
                    display_height = int(target_height * ratio)
                    print(f"DEBUG: Redimensionando para PDF: {display_width}x{display_height}")
                else:
                    display_width = target_width
                    display_height = target_height
                    print(f"DEBUG: Usando dimensiones originales para PDF: {display_width}x{display_height}")
                
                pdf_image = Image(temp_path, width=display_width, height=display_height)
                print(f"DEBUG: Imagen ReportLab creada - {display_width}x{display_height}")
                
                # Agregar imagen con borde para mejor visibilidad
                story.append(Spacer(1, 5))
                
                # Crear tabla para centrar la imagen con borde
                image_table = Table([[pdf_image]], colWidths=[display_width])
                image_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                    ('BOX', (0, 0), (0, 0), 2, colors.HexColor('#2c3e50')),
                    ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#ffffff')),
                    ('PADDING', (0, 0), (0, 0), 10),
                ]))
                
                story.append(image_table)
                print(f"DEBUG: Imagen agregada al PDF con borde exitosamente")
                
            except Exception as rl_error:
                print(f"ERROR: Error creando imagen ReportLab: {rl_error}")
                import traceback
                traceback.print_exc()
                
                # Método de respaldo: crear imagen simple más grande
                try:
                    print(f"DEBUG: Creando imagen de respaldo")
                    simple_img = PILImage.new('RGB', (400, 200), (255, 255, 255))
                    from PIL import ImageDraw
                    draw = ImageDraw.Draw(simple_img)
                    
                    # Dibujar un rectángulo más grande
                    draw.rectangle([20, 20, 380, 180], outline=(0, 0, 0), width=3)
                    
                    # Agregar texto más grande
                    draw.text((50, 50), "FIRMA DIGITAL", fill=(0, 0, 0))
                    draw.text((50, 80), "Procesamiento de respaldo", fill=(100, 100, 100))
                    
                    simple_path = os.path.join(app.config['UPLOAD_FOLDER'], f'simple_firma_{campo.id}.png')
                    simple_img.save(simple_path, format='PNG')
                    
                    # Crear imagen con borde
                    pdf_image = Image(simple_path, width=400, height=200)
                    image_table = Table([[pdf_image]], colWidths=[400])
                    image_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                        ('BOX', (0, 0), (0, 0), 2, colors.HexColor('#2c3e50')),
                        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#ffffff')),
                        ('PADDING', (0, 0), (0, 0), 10),
                    ]))
                    
                    story.append(image_table)
                    print(f"DEBUG: Imagen de respaldo agregada")
                    
                except Exception as backup_error:
                    print(f"ERROR: Error con imagen de respaldo: {backup_error}")
                    # Último recurso: texto
                    error_text = f"<b>Firma Digital:</b> Error procesando imagen"
                    error_paragraph = Paragraph(error_text, value_style)
                    story.append(error_paragraph)
            
        except Exception as img_error:
            print(f"ERROR: Error procesando imagen: {img_error}")
            import traceback
            traceback.print_exc()
            # Agregar mensaje de error
            error_text = f"<b>Firma Digital:</b> Error procesando imagen"
            error_paragraph = Paragraph(error_text, value_style)
            story.append(error_paragraph)
        
    except Exception as e:
        print(f"ERROR: Error general procesando firma: {e}")
        import traceback
        traceback.print_exc()
        # Agregar mensaje de error
        error_text = f"<b>Firma Digital:</b> Error procesando firma"
        error_paragraph = Paragraph(error_text, value_style)
        story.append(error_paragraph)
    
    finally:
        # NO eliminar el archivo temporal aquí - ReportLab aún lo necesita
        # El archivo se eliminará automáticamente por la limpieza general al final
        pass


def clean_base64(b64_str):
    """Limpia la cadena Base64 removiendo prefijos y padding incorrecto."""
    import re
    
    # 1. Quitar prefijo
    if ',' in b64_str:
        header, data = b64_str.split(',', 1)
        print(f"DEBUG: Prefijo removido: {header}")
    else:
        data = b64_str
    
    # 2. Remover caracteres que no son válidos
    # Sólo dejar A-Z a-z, 0-9, +, /, = (si estás usando base64 estándar)
    data = re.sub(r'[^A-Za-z0-9+/=]', '', data)
    
    # 3. Corregir padding si falta
    missing_padding = len(data) % 4
    if missing_padding != 0:
        data += '=' * (4 - missing_padding)
        print(f"DEBUG: Padding agregado: {4 - missing_padding} caracteres")
    
    print(f"DEBUG: Base64 limpio - Longitud: {len(data)}")
    return data

def procesar_firma_simple(firma_data, campo, story, value_style):
    """Procesar firma de manera simple y robusta - SOLO CAMBIO: umbral más permisivo"""
    temp_path = None
    try:
        import base64
        import datetime
        import io
        import re
        from PIL import Image as PILImage
        from PIL import ImageFile
        from reportlab.platypus import Image
        from reportlab.lib.utils import ImageReader
        
        # Configurar PIL para manejar imágenes truncadas
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        
        print(f"DEBUG: Procesando firma simple para campo {campo.id}")
        print(f"DEBUG: Longitud datos recibidos: {len(firma_data)}")
        print(f"DEBUG: Primeros 100 caracteres: {firma_data[:100]}")
        
        # Verificar que la cadena no esté vacía
        if not firma_data or len(firma_data) < 30:
            raise ValueError("Firma base64 demasiado corta o vacía")
        
        # Crear archivo temporal único
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temp_filename = f"firma_simple_{campo.id}_{timestamp}.png"
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        
        # Limpiar y decodificar base64
        try:
            # Limpiar la cadena base64
            cleaned_base64 = clean_base64(firma_data)
            
            # Decodificar base64
            image_data = base64.b64decode(cleaned_base64)
            print(f"DEBUG: Base64 decodificado - Tamaño: {len(image_data)} bytes")
            
        except Exception as decode_error:
            print(f"ERROR: Error decodificando base64: {decode_error}")
            raise ValueError(f"Error decodificando base64: {decode_error}")
        
        # Procesar imagen con PIL
        try:
            # Abrir imagen
            image = PILImage.open(io.BytesIO(image_data))
            print(f"DEBUG: Imagen PIL abierta - Modo: {image.mode}, Dimensiones: {image.width}x{image.height}")
            
            # Convertir a RGB si es necesario
            if image.mode in ('RGBA', 'LA'):
                print(f"DEBUG: Convirtiendo {image.mode} a RGB con fondo blanco")
                fondo = PILImage.new('RGB', image.size, (255, 255, 255))
                alpha = image.split()[-1]
                fondo.paste(image, mask=alpha)
                image = fondo
            else:
                image = image.convert('RGB')
            
            # Verificar que la imagen tiene contenido (no solo fondo blanco)
            # Convertir a escala de grises para análisis
            gray_img = image.convert('L')
            histogram = gray_img.histogram()
            
            # Contar píxeles no blancos (valor < 250) - MÁS PERMISIVO
            non_white_pixels = sum(histogram[:250])
            total_pixels = sum(histogram)
            non_white_percentage = (non_white_pixels / total_pixels) * 100
            
            print(f"DEBUG: Análisis imagen - Píxeles no blancos: {non_white_percentage:.1f}%")
            
            # CAMBIO ÚNICO: Ser más permisivo - solo considerar vacía si tiene menos del 0.1% de contenido
            if non_white_percentage < 0.1:  # Cambiado de 1.0% a 0.1%
                print(f"DEBUG: Imagen parece estar vacía, creando imagen de respaldo")
                # Crear imagen de respaldo
                image = PILImage.new('RGB', (400, 200), (255, 255, 255))
                from PIL import ImageDraw, ImageFont
                
                try:
                    draw = ImageDraw.Draw(image)
                    # Dibujar un rectángulo simple
                    draw.rectangle([50, 50, 350, 150], outline=(0, 0, 0), width=2)
                    
                    # Agregar texto
                    try:
                        font = ImageFont.load_default()
                        text = "FIRMA DIGITAL"
                        bbox = draw.textbbox((0, 0), text, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                        x = (400 - text_width) // 2
                        y = (200 - text_height) // 2
                        draw.text((x, y), text, fill=(0, 0, 0), font=font)
                    except:
                        pass
                except Exception as draw_error:
                    print(f"DEBUG: Error creando imagen de respaldo: {draw_error}")
            else:
                print(f"DEBUG: Imagen tiene contenido válido, procediendo con la imagen original")
            
            # Guardar imagen procesada
            image.save(temp_path, format='PNG', quality=100)
            print(f"DEBUG: Imagen guardada - Dimensiones: {image.width}x{image.height}")
            
        except Exception as pil_error:
            print(f"ERROR: Error procesando imagen con PIL: {pil_error}")
            raise ValueError(f"Error procesando imagen: {pil_error}")
        
        # Crear imagen para ReportLab
        try:
            # Usar directamente la ruta del archivo
            pdf_image = Image(temp_path, width=300, height=150)
            print(f"DEBUG: Imagen ReportLab creada exitosamente")
            
        except Exception as e:
            print(f"ERROR: Error creando imagen ReportLab: {e}")
            raise ValueError("No se pudo crear imagen para PDF")
        
        # Agregar imagen al PDF
        try:
            # Crear tabla para la firma
            firma_data_table = Table([
                ['Firma Digital:', pdf_image]
            ], colWidths=[120, 300])
            
            # Estilo para la tabla de firma
            firma_style = TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (0, 0), 10),
                ('TEXTCOLOR', (0, 0), (0, 0), '#2c3e50'),
                ('BACKGROUND', (0, 0), (-1, -1), '#ffffff'),
                ('GRID', (0, 0), (-1, -1), 1, '#2c3e50'),
                ('PADDING', (0, 0), (-1, -1), 8),
            ])
            
            firma_data_table.setStyle(firma_style)
            story.append(firma_data_table)
            story.append(Spacer(1, 12))
            
            print(f"DEBUG: Firma agregada al PDF exitosamente")
            
        except Exception as e:
            print(f"ERROR: Error agregando firma al PDF: {e}")
            # Agregar texto de error como respaldo
            error_text = f"Error procesando imagen de firma: {e}"
            story.append(Paragraph(f"<b>Firma Digital:</b> {error_text}", value_style))
            story.append(Spacer(1, 12))
        
        return temp_path
        
    except Exception as e:
        print(f"ERROR: Error general procesando firma: {e}")
        # Agregar texto de error como respaldo
        error_text = f"Error procesando imagen de firma: {e}"
        story.append(Paragraph(f"<b>Firma Digital:</b> {error_text}", value_style))
        story.append(Spacer(1, 12))
        return None
    finally:
        # NO eliminar el archivo temporal aquí - ReportLab aún lo necesita
        pass

def procesar_firma_png(firma_data, campo, story, value_style):
    """Procesar firma como imagen PNG - CÓDIGO EXACTO DE FirmasHTML"""
    try:
        image_bytes = b""
        print(f"DEBUG: === INICIANDO procesar_firma_png para campo {campo.id} ===")
        print(f"DEBUG: Datos de firma recibidos: {len(firma_data)} caracteres")
        
        import base64
        from datetime import datetime
        from PIL import Image as PILImage
        from io import BytesIO
        from reportlab.platypus import Image, Spacer, Paragraph
        
        # Si firma_data es una ruta (cuando la guardamos en POST), úsala directamente
        posible_path = os.path.join(app.config['UPLOAD_FOLDER'], firma_data) if not os.path.isabs(firma_data) else firma_data
        if os.path.exists(posible_path):
            print(f"DEBUG: Usando archivo de firma existente: {posible_path}")
            png_path = posible_path
            img = PILImage.open(png_path)
            bg = img.convert('RGB')
        else:
            # Separar el prefijo data:url si existe (EXACTO como FirmasHTML)
            if ',' in firma_data:
                _, encoded = firma_data.split(',', 1)
            else:
                encoded = firma_data

            print(f"DEBUG: Base64 extraído, longitud: {len(encoded)}")

            # Decodificar base64 (EXACTO como FirmasHTML - SIN LIMPIEZA)
            try:
                image_bytes = base64.b64decode(encoded)
                print(f"DEBUG: Base64 decodificado exitosamente, tamaño: {len(image_bytes)} bytes")
            except Exception as e:
                print(f"ERROR: Base64 decode failed: {e}")
                print(f"DEBUG: Base64 problemático: {encoded[:100]}...")
                raise e

            # Guardar temporalmente la imagen PNG (EXACTO como FirmasHTML)
            img = PILImage.open(BytesIO(image_bytes)).convert('RGBA')
            bg = PILImage.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)

            # Crear estructura de carpetas organizada
            firmas_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'formularios', 'firmas')
            os.makedirs(firmas_dir, exist_ok=True)
            png_filename = f'firma_{campo.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            png_path = os.path.join(firmas_dir, png_filename)
            bg.save(png_path, format='PNG')
            print(f"DEBUG: Imagen PNG guardada en: {png_path}")
        
        # En este punto tenemos bg (imagen PIL en RGB) y png_path (ruta del PNG)
        
        # Verificar archivo
        if os.path.exists(png_path):
            file_size = os.path.getsize(png_path)
            print(f"DEBUG: ✅ Archivo PNG creado exitosamente - Tamaño: {file_size} bytes")
        else:
            print(f"DEBUG: ❌ ERROR: Archivo PNG NO se creó")
            raise Exception("No se pudo crear el archivo PNG de la firma")
        
        # Escalar la firma (EXACTO como FirmasHTML)
        img_w, img_h = bg.size
        from reportlab.lib.pagesizes import A4
        page_w, page_h = A4
        max_width = min(page_w * 0.4, 300)
        scale = max_width / img_w
        draw_w = img_w * scale
        draw_h = img_h * scale
        
        print(f"DEBUG: Imagen original: {img_w}x{img_h}, Escalada: {draw_w}x{draw_h}")
        
        # Crear imagen para PDF (EXACTO como FirmasHTML)
        pdf_image = Image(png_path, width=draw_w, height=draw_h)
        story.append(pdf_image)
        story.append(Spacer(1, 10))
        
        print(f"DEBUG: ✅ Firma PNG agregada al PDF exitosamente")
            
    except Exception as e:
        print(f"ERROR: Error en procesar_firma_png: {e}")
        # En caso de error, agregar texto de error
        error_text = f"<b>Firma Digital:</b> Error procesando imagen ({str(e)[:50]}...)"
        error_paragraph = Paragraph(error_text, value_style)
        story.append(error_paragraph)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
