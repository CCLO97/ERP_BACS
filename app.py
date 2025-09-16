from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
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
                                    img = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
                                
                                # Guardar imagen temporalmente
                                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{archivo}')
                                img.save(temp_path)
                                
                                # Agregar espacio antes de la imagen
                                story.append(Spacer(1, 10))
                                
                                # Crear leyenda mejorada
                                caption_text = f"Figura {contador_imagen}. {archivo.replace('_', ' ').replace('.jpg', '').replace('.png', '').replace('.jpeg', '').title()}"
                                caption = Paragraph(caption_text, caption_style)
                                story.append(caption)
                                
                                # Agregar imagen centrada con borde
                                pdf_image = Image(temp_path, width=img.width, height=img.height)
                                
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
                                
                                # Guardar imagen temporalmente
                                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{archivo}')
                                img.save(temp_path)
                                
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
                            
                            # Guardar imagen temporalmente
                            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{archivo}')
                            img.save(temp_path)
                            
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

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
