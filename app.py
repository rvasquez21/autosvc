from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from functools import wraps
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SelectField, TextAreaField, DateTimeField, IntegerField, SubmitField, FloatField, DateField
from wtforms.validators import DataRequired, Length, Email, NumberRange
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
import pandas as pd
import os
from sqlalchemy import or_, and_

# Función helper para reemplazar datetime.utcnow() (deprecado)
def utcnow():
    """Retorna la fecha y hora actual en UTC (reemplazo de datetime.utcnow())"""
    return datetime.now(timezone.utc)

app = Flask(__name__)
app.config.from_object("config.Config")

# Configuración para archivos
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xls', 'xlsx', 'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Crear directorios necesarios si no existen
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'insurance_orders'), exist_ok=True)
    os.makedirs('instance', exist_ok=True)
except Exception as e:
    print(f"Warning: No se pudieron crear algunos directorios: {e}")

# Configurar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'info'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ---------- Models ----------
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default="TECNICO")  # ADMIN, TECNICO, ASESOR, JEFE_TALLER, SUPERVISOR
    full_name = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    plate = db.Column(db.String(15), nullable=False)
    vin = db.Column(db.String(30))
    chasis = db.Column(db.String(30))  # Nuevo campo
    brand = db.Column(db.String(50))   # Nuevo campo - marca
    modelo = db.Column(db.String(50))   # Modelo del vehículo
    customer_name = db.Column(db.String(120), nullable=False)
    advisor = db.Column(db.String(120))  # Para compatibilidad con datos existentes
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=True)
    technician = db.Column(db.String(120))  # Para compatibilidad con datos existentes
    technician_id = db.Column(db.Integer, db.ForeignKey('technicians.id'), nullable=True)
    technician_assigned_at = db.Column(db.DateTime, nullable=True)  # Fecha de asignación al técnico
    service_type = db.Column(db.String(50), default="Mantenimiento")
    status = db.Column(db.String(30), default="RECEPCION")
    symptom = db.Column(db.Text)
    priority = db.Column(db.String(10), default="NORMAL")  # URGENTE | NORMAL | BAJA
    promised_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    
    # Relaciones
    status_history = db.relationship('StatusHistory', backref='order', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('OrderComment', backref='order', lazy=True, cascade='all, delete-orphan')

    def days_in_shop(self):
        return (utcnow().date() - self.created_at.date()).days

class StatusHistory(db.Model):
    __tablename__ = "status_history"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    old_status = db.Column(db.String(30))
    new_status = db.Column(db.String(30), nullable=False)
    changed_by = db.Column(db.String(120))  # Usuario que hizo el cambio
    change_reason = db.Column(db.Text)      # Razón del cambio
    created_at = db.Column(db.DateTime, default=utcnow)

class OrderComment(db.Model):
    __tablename__ = "order_comments"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(120))      # Autor del comentario
    comment_type = db.Column(db.String(20), default="GENERAL")  # GENERAL, INTERNAL, CUSTOMER
    created_at = db.Column(db.DateTime, default=utcnow)

class Technician(db.Model):
    __tablename__ = "technicians"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # Código del técnico (ej: TJ001)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    specialty = db.Column(db.String(100))  # Especialidad (Motor, Frenos, etc.)
    hourly_rate = db.Column(db.Float, default=0.0)  # Tarifa por hora
    is_active = db.Column(db.Boolean, default=True)
    hire_date = db.Column(db.DateTime, default=utcnow)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    
    # Relaciones
    hours_records = db.relationship('TechnicianHours', backref='technician', lazy=True, foreign_keys='TechnicianHours.technician_id')
    assigned_orders = db.relationship('Order', backref='assigned_technician', lazy=True, foreign_keys='Order.technician_id')
    
    def __repr__(self):
        return f'<Technician {self.code}: {self.full_name}>'

class Advisor(db.Model):
    __tablename__ = "advisors"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # Código del asesor (ej: AS001)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    department = db.Column(db.String(100))  # Departamento (Ventas, Servicio, etc.)
    commission_rate = db.Column(db.Float, default=0.0)  # Tasa de comisión
    is_active = db.Column(db.Boolean, default=True)
    hire_date = db.Column(db.DateTime, default=utcnow)
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Enlace con usuario del sistema
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    
    # Relaciones
    assigned_orders = db.relationship('Order', backref='assigned_advisor', lazy=True, foreign_keys='Order.advisor_id')
    user = db.relationship('User', backref=db.backref('advisor_profile', uselist=False))
    
    def __repr__(self):
        return f'<Advisor {self.code}: {self.full_name}>'

class TechnicianHours(db.Model):
    __tablename__ = "technician_hours"
    id = db.Column(db.Integer, primary_key=True)
    technician_id = db.Column(db.Integer, db.ForeignKey('technicians.id'), nullable=True)
    technician_name = db.Column(db.String(120), nullable=False)  # Para compatibilidad con datos existentes
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    date_worked = db.Column(db.DateTime, nullable=False)
    hours_worked = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)
    created_by = db.Column(db.String(120))  # Usuario que registró las horas

class Status(db.Model):
    __tablename__ = "status"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # Nombre del estatus
    display_name = db.Column(db.String(100), nullable=False)  # Nombre para mostrar
    color = db.Column(db.String(7), default="#6c757d")  # Color hexadecimal
    description = db.Column(db.Text)  # Descripción del estatus
    is_active = db.Column(db.Boolean, default=True)  # Si el estatus está activo
    sort_order = db.Column(db.Integer, default=0)  # Orden de visualización
    is_final = db.Column(db.Boolean, default=False)  # Si es un estatus final (ej: ENTREGADO)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    
    # Relaciones - No hay foreign key directo, se relaciona por el campo status (string)
    
    def __repr__(self):
        return f'<Status {self.name}: {self.display_name}>'

class PaintShopInfo(db.Model):
    __tablename__ = "paint_shop_info"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    shop_name = db.Column(db.String(200), nullable=False)  # Nombre del taller
    send_date = db.Column(db.DateTime, nullable=False)  # Fecha de envío
    delivery_date = db.Column(db.DateTime, nullable=True)  # Fecha de entrega
    insurance_order_copy = db.Column(db.String(500), nullable=True)  # Ruta del archivo de copia de orden de seguro
    notes = db.Column(db.Text)  # Notas adicionales
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    
    # Relaciones
    order = db.relationship('Order', backref=db.backref('paint_shop_info', uselist=False))
    
    def __repr__(self):
        return f'<PaintShopInfo {self.shop_name} para orden {self.order_id}>'

class Repuesto(db.Model):
    __tablename__ = "repuestos"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    numero_parte = db.Column(db.String(100), nullable=False)  # Número de parte
    descripcion = db.Column(db.String(500), nullable=False)  # Descripción
    cantidad = db.Column(db.Integer, nullable=False, default=1)  # Cantidad
    estatus = db.Column(db.String(20), nullable=False, default='PENDIENTE')  # PENDIENTE, PEDIDO, FACTURADO, EN_TRANSITO
    numero_pedido = db.Column(db.String(100))  # Número de pedido
    fecha_pedido = db.Column(db.Date)  # Fecha de pedido
    fecha_facturacion = db.Column(db.Date)  # Fecha de facturación
    costo_unitario = db.Column(db.Float)  # Costo unitario
    costo_total = db.Column(db.Float)  # Costo total
    proveedor = db.Column(db.String(200))  # Proveedor
    notas = db.Column(db.Text)  # Notas adicionales
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    
    # Relación con Order
    order = db.relationship('Order', backref=db.backref('repuestos', lazy=True))
    
    def __repr__(self):
        return f'<Repuesto {self.numero_parte}: {self.descripcion}>'

class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Usuario que recibe la notificación
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)  # Orden relacionada
    title = db.Column(db.String(200), nullable=False)  # Título de la notificación
    message = db.Column(db.Text, nullable=False)  # Mensaje de la notificación
    notification_type = db.Column(db.String(50), default="INFO")  # INFO, WARNING, SUCCESS, ORDER_CHANGE, COMMENT
    is_read = db.Column(db.Boolean, default=False)  # Si la notificación ha sido leída
    created_by = db.Column(db.String(120))  # Usuario que creó la notificación
    created_at = db.Column(db.DateTime, default=utcnow)
    
    # Relaciones
    user = db.relationship('User', backref=db.backref('notifications', lazy=True))
    order = db.relationship('Order', backref=db.backref('notifications', lazy=True))
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'

class AdvisorContact(db.Model):
    __tablename__ = "advisor_contacts"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=False)
    contact_date = db.Column(db.DateTime, default=utcnow)  # Fecha del último contacto
    contact_type = db.Column(db.String(50), default="CALL")  # CALL, EMAIL, VISIT, MESSAGE
    notes = db.Column(db.Text)  # Notas sobre el contacto
    next_reminder_date = db.Column(db.DateTime)  # Próxima fecha de recordatorio (24 horas después)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    
    # Relaciones
    order = db.relationship('Order', backref=db.backref('advisor_contacts', lazy=True))
    advisor = db.relationship('Advisor', backref=db.backref('contacts', lazy=True))
    
    def __repr__(self):
        return f'<AdvisorContact {self.id}: Orden {self.order_id} - Asesor {self.advisor_id}>'

# ---------- Helper Functions para Notificaciones y Roles ----------
def create_notification(user_id, order_id, title, message, notification_type="INFO", created_by=None):
    """Crear una notificación para un usuario"""
    notification = Notification(
        user_id=user_id,
        order_id=order_id,
        title=title,
        message=message,
        notification_type=notification_type,
        created_by=created_by or (current_user.full_name if current_user.is_authenticated else "Sistema")
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def notify_advisor_on_order_change(order, change_description, changed_by):
    """Notificar al asesor cuando se hace un cambio en su orden"""
    if not order.advisor_id:
        return
    
    advisor = Advisor.query.get(order.advisor_id)
    if not advisor:
        return
    
    # Usar el enlace directo user_id si existe, sino buscar por email o nombre
    user = None
    if advisor.user_id:
        user = User.query.get(advisor.user_id)
    else:
        # Fallback: buscar por email o nombre
        user = User.query.filter(
            (User.email == advisor.email) | (User.full_name == advisor.full_name)
        ).first()
    
    if user:
        title = f"Cambio en Orden {order.order_number}"
        message = f"Se ha realizado un cambio en la orden {order.order_number} del cliente {order.customer_name}. {change_description}"
        create_notification(
            user_id=user.id,
            order_id=order.id,
            title=title,
            message=message,
            notification_type="ORDER_CHANGE",
            created_by=changed_by
        )

def notify_advisor_on_comment(order, comment_text, comment_author):
    """Notificar al asesor cuando se agrega un comentario a su orden"""
    if not order.advisor_id:
        return
    
    advisor = Advisor.query.get(order.advisor_id)
    if not advisor:
        return
    
    # Usar el enlace directo user_id si existe, sino buscar por email o nombre
    user = None
    if advisor.user_id:
        user = User.query.get(advisor.user_id)
    else:
        # Fallback: buscar por email o nombre
        user = User.query.filter(
            (User.email == advisor.email) | (User.full_name == advisor.full_name)
        ).first()
    
    if user:
        title = f"Nuevo Comentario en Orden {order.order_number}"
        message = f"Se ha agregado un comentario en la orden {order.order_number} del cliente {order.customer_name} por {comment_author}."
        create_notification(
            user_id=user.id,
            order_id=order.id,
            title=title,
            message=message,
            notification_type="COMMENT",
            created_by=comment_author
        )

def notify_managers_on_advisor_comment(order, comment_text, advisor_name):
    """Notificar a administradores, jefes de taller y supervisores cuando un asesor agrega un comentario"""
    # Obtener todos los usuarios con roles de administración
    managers = User.query.filter(
        User.role.in_(['ADMIN', 'JEFE_TALLER', 'SUPERVISOR']),
        User.is_active == True
    ).all()
    
    for manager in managers:
        title = f"Comentario de Asesor en Orden {order.order_number}"
        message = f"El asesor {advisor_name} ha agregado un comentario en la orden {order.order_number} del cliente {order.customer_name}."
        create_notification(
            user_id=manager.id,
            order_id=order.id,
            title=title,
            message=message,
            notification_type="COMMENT",
            created_by=advisor_name
        )

def is_admin_or_manager(user):
    """Verificar si el usuario es admin, jefe de taller o supervisor"""
    if not user or not user.is_authenticated:
        return False
    return user.role in ['ADMIN', 'JEFE_TALLER', 'SUPERVISOR']

def get_orders_for_user(user):
    """Obtener órdenes filtradas según el rol del usuario"""
    if not user or not user.is_authenticated:
        return Order.query.filter_by(id=0)  # Retornar query vacía
    
    if is_admin_or_manager(user):
        # Admin, Jefe de Taller y Supervisor ven todas las órdenes
        return Order.query
    
    elif user.role == 'ASESOR':
        # Asesores ven solo sus órdenes
        # Buscar asesor por user_id (enlace directo) o por email/nombre (fallback)
        advisor = None
        if user.id:
            advisor = Advisor.query.filter_by(user_id=user.id).first()
        
        if not advisor:
            # Fallback: buscar por email o nombre
            advisor = Advisor.query.filter(
                (Advisor.email == user.email) | (Advisor.full_name == user.full_name)
            ).first()
        
        if advisor:
            return Order.query.filter_by(advisor_id=advisor.id)
        else:
            # Si no hay asesor asociado, no ver órdenes
            return Order.query.filter_by(id=0)
    
    elif user.role == 'TECNICO':
        # Técnicos ven solo órdenes asignadas a ellos
        technician = Technician.query.filter(
            (Technician.full_name == user.full_name)
        ).first()
        
        if technician:
            return Order.query.filter_by(technician_id=technician.id)
        else:
            return Order.query.filter_by(id=0)
    
    # Por defecto, no ver órdenes
    return Order.query.filter_by(id=0)

def check_contact_reminders():
    """Verificar recordatorios de contacto para asesores"""
    from datetime import datetime, timedelta
    
    # Obtener todas las órdenes que no están entregadas
    orders = Order.query.filter(Order.status != 'ENTREGADO').all()
    
    reminders_created = 0
    for order in orders:
        if not order.advisor_id:
            continue
        
        advisor = Advisor.query.get(order.advisor_id)
        if not advisor:
            continue
        
        # Buscar el último contacto registrado
        last_contact = AdvisorContact.query.filter_by(
            order_id=order.id,
            advisor_id=order.advisor_id
        ).order_by(AdvisorContact.contact_date.desc()).first()
        
        now = utcnow()
        
        if last_contact:
            # Verificar si han pasado 24 horas desde el último contacto
            time_since_contact = now - last_contact.contact_date
            if time_since_contact >= timedelta(hours=24):
                # Verificar si ya hay un recordatorio pendiente
                if not last_contact.next_reminder_date or last_contact.next_reminder_date <= now:
                    # Crear notificación de recordatorio
                    # Usar el enlace directo user_id si existe, sino buscar por email o nombre
                    user = None
                    if advisor.user_id:
                        user = User.query.get(advisor.user_id)
                    else:
                        # Fallback: buscar por email o nombre
                        user = User.query.filter(
                            (User.email == advisor.email) | (User.full_name == advisor.full_name)
                        ).first()
                    
                    if user:
                        title = f"Recordatorio: Contactar Cliente - Orden {order.order_number}"
                        message = f"Han pasado más de 24 horas desde el último contacto con el cliente {order.customer_name} de la orden {order.order_number}. Por favor, contacta al cliente y agrega un comentario sobre la conversación."
                        create_notification(
                            user_id=user.id,
                            order_id=order.id,
                            title=title,
                            message=message,
                            notification_type="WARNING",
                            created_by="Sistema"
                        )
                        
                        # Actualizar fecha de próximo recordatorio (24 horas después)
                        last_contact.next_reminder_date = now + timedelta(hours=24)
                        db.session.commit()
                        reminders_created += 1
        else:
            # Si nunca ha habido contacto, crear recordatorio después de 24 horas de creada la orden
            time_since_creation = now - order.created_at
            if time_since_creation >= timedelta(hours=24):
                # Crear registro de contacto inicial
                contact = AdvisorContact(
                    order_id=order.id,
                    advisor_id=order.advisor_id,
                    contact_date=order.created_at,
                    contact_type="INITIAL",
                    notes="Registro inicial - sin contacto aún",
                    next_reminder_date=now + timedelta(hours=24)
                )
                db.session.add(contact)
                
                # Crear notificación
                # Usar el enlace directo user_id si existe, sino buscar por email o nombre
                user = None
                if advisor.user_id:
                    user = User.query.get(advisor.user_id)
                else:
                    # Fallback: buscar por email o nombre
                    user = User.query.filter(
                        (User.email == advisor.email) | (User.full_name == advisor.full_name)
                    ).first()
                
                if user:
                    title = f"Recordatorio: Contactar Cliente - Orden {order.order_number}"
                    message = f"La orden {order.order_number} del cliente {order.customer_name} lleva más de 24 horas sin contacto. Por favor, contacta al cliente y agrega un comentario."
                    create_notification(
                        user_id=user.id,
                        order_id=order.id,
                        title=title,
                        message=message,
                        notification_type="WARNING",
                        created_by="Sistema"
                    )
                    reminders_created += 1
    
    db.session.commit()
    return reminders_created

# STATUS_CHOICES ahora se obtiene dinámicamente de la BD
def get_status_choices():
    """Obtener opciones de estatus desde la base de datos"""
    try:
        statuses = Status.query.filter_by(is_active=True).order_by(Status.sort_order, Status.name).all()
        return [(status.name, status.display_name) for status in statuses]
    except:
        # Fallback a estatus por defecto si hay problemas con la BD
        return [
            ("RECEPCION", "Recepción"),
            ("DIAGNOSTICO", "Diagnóstico"),
            ("PRESUPUESTO", "Presupuesto"),
            ("APROBACION", "Aprobación"),
            ("EN_REPARACION", "En Reparación"),
            ("ESPERA_REPUESTOS", "Espera Repuestos"),
            ("LAVADO", "Lavado"),
            ("CONTROL_CALIDAD", "Control de Calidad"),
            ("FACTURACION", "Facturación"),
            ("ENTREGADO", "Entregado"),
        ]

def get_status_colors():
    """Obtener colores de estado desde la base de datos"""
    try:
        statuses = Status.query.filter_by(is_active=True).order_by(Status.sort_order, Status.name).all()
        return {status.name: status.color for status in statuses}
    except:
        # Fallback a colores por defecto si hay problemas con la BD
        return {
            "RECEPCION": "#6c757d",
            "DIAGNOSTICO": "#0dcaf0",
            "PRESUPUESTO": "#fd7e14",
            "APROBACION": "#ffc107",
            "EN_REPARACION": "#198754",
            "ESPERA_REPUESTO": "#6f42c1",
            "LAVADO": "#0d6efd",
            "CONTROL_CALIDAD": "#20c997",
            "FACTURACION": "#dc3545",
            "ENTREGADO": "#198754",
        }

def get_status_list():
    """Obtener lista de nombres de estatus para validaciones"""
    try:
        statuses = Status.query.filter_by(is_active=True).all()
        return [status.name for status in statuses]
    except:
        return ["RECEPCION", "DIAGNOSTICO", "PRESUPUESTO", "APROBACION", "EN_REPARACION", "ESPERA_REPUESTOS", "LAVADO", "CONTROL_CALIDAD", "FACTURACION", "ENTREGADO"]

# Conversión robusta de valores a booleano para SelectField
def to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    # Manejar números
    if isinstance(value, (int, float)):
        return bool(value)
    # Manejar strings como 'True', 'true', '1', 'on', 'yes'
    if isinstance(value, str):
        v = value.strip().lower()
        return v in ("true", "1", "yes", "on", "t")
    return False

def to_int_or_none(value):
    """Convierte un valor a int o retorna None si está vacío o no es válido"""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        v = value.strip()
        if not v or v == '' or v.lower() == 'none':
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

# ---------- Forms ----------
class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

class RegisterForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Nombre Completo', validators=[DataRequired(), Length(min=2, max=120)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    role = SelectField('Rol', choices=[
        ('TECNICO', 'Técnico'), 
        ('ASESOR', 'Asesor'), 
        ('ADMIN', 'Administrador'),
        ('JEFE_TALLER', 'Jefe de Taller'),
        ('SUPERVISOR', 'Supervisor')
    ])
    submit = SubmitField('Registrar')

class UserForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Nombre Completo', validators=[DataRequired(), Length(min=2, max=120)])
    password = PasswordField('Contraseña', validators=[Length(min=6, message='La contraseña debe tener al menos 6 caracteres')])
    role = SelectField('Rol', choices=[
        ('TECNICO', 'Técnico'), 
        ('ASESOR', 'Asesor'), 
        ('ADMIN', 'Administrador'),
        ('JEFE_TALLER', 'Jefe de Taller'),
        ('SUPERVISOR', 'Supervisor')
    ], validators=[DataRequired()])
    is_active = SelectField('Estado', choices=[(True, 'Activo'), (False, 'Inactivo')], coerce=bool, default=True)
    submit = SubmitField('Guardar')

class TechnicianHoursForm(FlaskForm):
    technician_name = StringField('Técnico', validators=[DataRequired()])
    order_id = SelectField('Orden (opcional)', coerce=int, choices=[])
    date_worked = DateTimeField('Fecha de Trabajo', validators=[DataRequired()], default=utcnow)
    hours_worked = IntegerField('Horas Trabajadas', validators=[DataRequired()])
    description = TextAreaField('Descripción del Trabajo')
    submit = SubmitField('Registrar Horas')

class ExcelUploadForm(FlaskForm):
    file = FileField('Archivo Excel de Comisiones', 
                    validators=[DataRequired(), 
                              FileAllowed(['xls', 'xlsx'], 'Solo archivos Excel (.xls, .xlsx)')])
    submit = SubmitField('Cargar Archivo')

class OrdersUploadForm(FlaskForm):
    file = FileField('Archivo Excel de Órdenes', 
                    validators=[DataRequired(), 
                              FileAllowed(['xls', 'xlsx'], 'Solo archivos Excel (.xls, .xlsx)')])
    submit = SubmitField('Cargar Órdenes')

class TechnicianForm(FlaskForm):
    code = StringField('Código del Técnico', validators=[DataRequired(), Length(min=2, max=20)])
    full_name = StringField('Nombre Completo', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[Email()])
    phone = StringField('Teléfono')
    specialty = SelectField('Especialidad', choices=[
        ('', 'Seleccionar especialidad'),
        ('MOTOR', 'Motor'),
        ('FRENOS', 'Frenos'),
        ('SUSPENSION', 'Suspensión'),
        ('ELECTRICO', 'Eléctrico'),
        ('CLIMATIZACION', 'Climatización'),
        ('TRANSMISION', 'Transmisión'),
        ('GENERAL', 'General'),
        ('OTRO', 'Otro')
    ])
    hourly_rate = IntegerField('Tarifa por Hora', default=0)
    is_active = SelectField('Estado', choices=[(True, 'Activo'), (False, 'Inactivo')], default=True, coerce=to_bool)
    hire_date = DateTimeField('Fecha de Contratación', default=utcnow)
    notes = TextAreaField('Notas')
    submit = SubmitField('Guardar Técnico')

class AdvisorForm(FlaskForm):
    code = StringField('Código del Asesor', validators=[DataRequired(), Length(min=2, max=20)])
    full_name = StringField('Nombre Completo', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[Email()])
    phone = StringField('Teléfono')
    department = SelectField('Departamento', choices=[
        ('', 'Seleccionar departamento'),
        ('VENTAS', 'Ventas'),
        ('SERVICIO', 'Servicio'),
        ('ATENCION_CLIENTE', 'Atención al Cliente'),
        ('GARANTIA', 'Garantía'),
        ('ADMINISTRACION', 'Administración'),
        ('OTRO', 'Otro')
    ])
    commission_rate = FloatField('Tasa de Comisión (%)', default=0.0)
    is_active = SelectField('Estado', choices=[(True, 'Activo'), (False, 'Inactivo')], default=True, coerce=to_bool)
    hire_date = DateTimeField('Fecha de Contratación', default=utcnow)
    user_id = SelectField('Usuario del Sistema (Opcional)', coerce=to_int_or_none, choices=[])
    notes = TextAreaField('Notas')
    submit = SubmitField('Guardar Asesor')

class StatusForm(FlaskForm):
    name = StringField('Nombre del Estatus', validators=[DataRequired(), Length(min=2, max=50)])
    display_name = StringField('Nombre para Mostrar', validators=[DataRequired(), Length(min=2, max=100)])
    color = StringField('Color (Hex)', validators=[DataRequired()], default="#6c757d")
    description = TextAreaField('Descripción')
    is_active = SelectField('Estado', choices=[('true', 'Activo'), ('false', 'Inactivo')], default='true')
    sort_order = IntegerField('Orden de Visualización', default=0)
    is_final = SelectField('Estatus Final', choices=[('false', 'No'), ('true', 'Sí')], default='false')
    submit = SubmitField('Guardar Estatus')

class PaintShopInfoForm(FlaskForm):
    shop_name = StringField('Nombre del Taller', validators=[DataRequired(), Length(min=2, max=200)])
    send_date = DateField('Fecha de Envío', validators=[DataRequired()], default=lambda: datetime.now(timezone.utc).date())
    delivery_date = DateField('Fecha de Entrega (opcional)')
    insurance_order_copy = FileField('Copia de Orden de Seguro', 
                                   validators=[FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Solo archivos de imagen y PDF')])
    notes = TextAreaField('Notas Adicionales')
    submit = SubmitField('Guardar Información')

class RepuestoForm(FlaskForm):
    numero_parte = StringField('Número de Parte', validators=[DataRequired(), Length(min=1, max=100)])
    descripcion = StringField('Descripción', validators=[DataRequired(), Length(min=1, max=500)])
    cantidad = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1, max=9999)], default=1)
    estatus = SelectField('Estatus', choices=[
        ('PENDIENTE', 'Pendiente'),
        ('PEDIDO', 'Pedido'),
        ('FACTURADO', 'Facturado'),
        ('EN_TRANSITO', 'En Tránsito')
    ], default='PENDIENTE')
    numero_pedido = StringField('Número de Pedido', validators=[Length(max=100)])
    fecha_pedido = DateField('Fecha de Pedido')
    fecha_facturacion = DateField('Fecha de Facturación')
    costo_unitario = FloatField('Costo Unitario', validators=[NumberRange(min=0)])
    costo_total = FloatField('Costo Total', validators=[NumberRange(min=0)])
    proveedor = StringField('Proveedor', validators=[Length(max=200)])
    notas = TextAreaField('Notas Adicionales')
    submit = SubmitField('Guardar Repuesto')

# ---------- Funciones Auxiliares ----------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
    """Verificar si el archivo es una imagen o PDF permitida"""
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def detect_encoding(file_path):
    """Detectar la codificación de un archivo"""
    import chardet
    
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Leer solo los primeros 10KB
            result = chardet.detect(raw_data)
            return result['encoding']
    except:
        return 'utf-8'  # Codificación por defecto

def read_html_with_encoding(file_path):
    """Leer archivo HTML con detección automática de codificación"""
    import io
    from bs4 import BeautifulSoup
    import re
    
    # Lista de codificaciones a probar (ordenadas por probabilidad de éxito)
    encodings = ['latin-1', 'cp1252', 'iso-8859-1', 'windows-1252', 'utf-8', 'ascii']
    
    # Intentar detectar la codificación
    detected_encoding = detect_encoding(file_path)
    if detected_encoding and detected_encoding not in encodings:
        encodings.insert(0, detected_encoding)
    
    # Método 1: Intentar con pandas.read_html con diferentes codificaciones
    for encoding in encodings:
        try:
            df_list = pd.read_html(file_path, encoding=encoding)
            return df_list
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as e:
            # Si es un error de codificación, continuar con el siguiente
            if any(codec_error in str(e).lower() for codec_error in ['codec', 'decode', 'encoding']):
                continue
            # Si es otro tipo de error, intentar con el siguiente
            continue
    
    # Método 2: Leer el archivo manualmente con errores ignorados
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()
            
            # Limpiar caracteres problemáticos
            content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', content)
            
            # Crear un StringIO para pandas
            from io import StringIO
            string_io = StringIO(content)
            
            df_list = pd.read_html(string_io)
            return df_list
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as e:
            continue
    
    # Método 3: Leer como binario y decodificar con errores ignorados
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Limpiar bytes problemáticos
        content = re.sub(rb'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', b'', content)
        
        # Intentar decodificar con diferentes codificaciones
        for encoding in encodings:
            try:
                decoded_content = content.decode(encoding, errors='ignore')
                # Limpiar caracteres problemáticos adicionales
                decoded_content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', decoded_content)
                
                from io import StringIO
                string_io = StringIO(decoded_content)
                df_list = pd.read_html(string_io)
                return df_list
            except:
                continue
    except Exception:
        pass
    
    # Método 4: Usar BeautifulSoup para limpiar el HTML
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()
            
            # Limpiar caracteres problemáticos
            content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', content)
            
            # Usar BeautifulSoup para limpiar el HTML
            soup = BeautifulSoup(content, 'html.parser')
            clean_html = str(soup)
            
            from io import StringIO
            string_io = StringIO(clean_html)
            
            df_list = pd.read_html(string_io)
            return df_list
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as e:
            continue
    
    # Método 5: Forzar lectura con latin-1 y limpieza agresiva
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Decodificar forzadamente con latin-1
        decoded_content = content.decode('latin-1', errors='ignore')
        
        # Limpieza agresiva de caracteres problemáticos
        decoded_content = re.sub(r'[^\x20-\x7E\u00A0-\u00FF\u0100-\u017F\u0180-\u024F]', '', decoded_content)
        
        from io import StringIO
        string_io = StringIO(decoded_content)
        
        df_list = pd.read_html(string_io)
        return df_list
    except Exception:
        pass
    
    # Método 6: Último intento sin especificar codificación
    try:
        return pd.read_html(file_path)
    except Exception as e:
        raise Exception(f"No se pudo leer el archivo con ninguna codificación. Error: {str(e)}")

def read_html_robust(file_path):
    """Función robusta para leer archivos HTML problemáticos"""
    import io
    import re
    from bs4 import BeautifulSoup
    import os
    
    # Verificar que el archivo existe
    if not os.path.exists(file_path):
        raise Exception(f"El archivo no existe: {file_path}")
    
    # Verificar el tamaño del archivo
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise Exception("El archivo está vacío")
    
    try:
        # Leer el archivo como binario
        with open(file_path, 'rb') as f:
            raw_content = f.read()
        
        # Limpiar bytes problemáticos
        cleaned_bytes = re.sub(rb'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', b'', raw_content)
        
        # Intentar diferentes codificaciones
        encodings = ['latin-1', 'cp1252', 'iso-8859-1', 'windows-1252', 'utf-8']
        
        for encoding in encodings:
            try:
                # Decodificar con errores ignorados
                content = cleaned_bytes.decode(encoding, errors='ignore')
                
                # Limpiar caracteres problemáticos adicionales
                content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', content)
                
                # Usar BeautifulSoup para limpiar el HTML
                soup = BeautifulSoup(content, 'html.parser')
                clean_html = str(soup)
                
                # Crear StringIO y leer con pandas
                from io import StringIO
                string_io = StringIO(clean_html)
                df_list = pd.read_html(string_io)
                
                if df_list and len(df_list) > 0:
                    return df_list
                    
            except Exception as e:
                continue
        
        # Si todo falla, intentar con el contenido original
        try:
            content = raw_content.decode('latin-1', errors='replace')
            content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', content)
            
            from io import StringIO
            string_io = StringIO(content)
            df_list = pd.read_html(string_io)
            return df_list
        except Exception as e:
            pass
            
    except Exception as e:
        pass
    
    raise Exception(f"No se pudo leer el archivo con ningún método robusto. Archivo: {file_path}, Tamaño: {file_size} bytes. Verifique que el archivo sea un archivo Excel válido (.xls o .xlsx).")

def parse_excel_file(file_path):
    """Procesar archivo Excel de comisiones de mecánicos"""
    import os
    
    # Verificar que el archivo existe
    if not os.path.exists(file_path):
        raise Exception(f"El archivo no existe: {file_path}")
    
    # Verificar el tamaño del archivo
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise Exception("El archivo está vacío")
    
    # Método 1: Leer como Excel real (.xlsx, .xls)
    df_list = None
    try:
        df = pd.read_excel(file_path)
        if df is not None and not df.empty:
            # Convertir DataFrame a lista para mantener compatibilidad
            df_list = [df]
    except Exception as e:
        print(f"Error leyendo como Excel: {e}")
    
    # Método 2: Intentar como HTML (para archivos .xls que son HTML)
    if df_list is None:
        try:
            df_list = read_html_with_encoding(file_path)
        except Exception as e2:
            print(f"Error leyendo como HTML: {e2}")
    
    # Método 3: Usar método robusto
    if df_list is None:
        try:
            df_list = read_html_robust(file_path)
        except Exception as e3:
            print(f"Error con método robusto: {e3}")
    
    # Si todos los métodos fallan
    if df_list is None or len(df_list) == 0:
        raise Exception(f"No se pudo leer el archivo con ningún método. Archivo: {file_path}, Tamaño: {file_size} bytes. Verifique que el archivo sea un archivo Excel válido (.xls o .xlsx).")
    
    # Procesar los datos una vez que tenemos df_list
    df = df_list[0]  # Primera tabla
    
    # El archivo ya tiene los encabezados correctos, usar directamente
    df_clean = df.copy()
    
    # Verificar que las columnas esperadas existen
    expected_columns = ['Mecánico', 'No. Orden', 'Recepción', 'Completado', 'Tiempo Real', 'Descripción']
    if not all(col in df_clean.columns for col in expected_columns):
        # Si no están las columnas esperadas, buscar la fila de encabezados
        header_row = None
        for i, row in df.iterrows():
            if 'Mecánico' in str(row.iloc[0]) or 'No. Orden' in str(row.iloc[2]):
                header_row = i
                break
        
        if header_row is not None:
            # Usar esa fila como encabezados
            df_clean = df.iloc[header_row+1:].copy()
            df_clean.columns = df.iloc[header_row].values
            df_clean = df_clean.reset_index(drop=True)
    
    # Procesar datos para extraer horas trabajadas
    processed_data = []
    
    for _, row in df_clean.iterrows():
        try:
            # Extraer datos relevantes usando nombres de columnas
            mecanico = str(row['Mecánico']) if pd.notna(row['Mecánico']) else None
            orden = str(row['No. Orden']) if pd.notna(row['No. Orden']) else None
            fecha_recepcion = str(row['Recepción']) if pd.notna(row['Recepción']) else None
            fecha_completado = str(row['Completado']) if pd.notna(row['Completado']) else None
            tiempo_real = str(row['Tiempo Real']) if pd.notna(row['Tiempo Real']) else None
            descripcion = str(row['Descripción']) if pd.notna(row['Descripción']) else None
            
            # Convertir tiempo real a horas (formato :00)
            horas_trabajadas = 0
            if tiempo_real and tiempo_real != 'nan' and tiempo_real != ':00':
                try:
                    # Convertir formato :00 a horas decimales
                    if ':' in tiempo_real:
                        parts = tiempo_real.split(':')
                        horas = int(parts[0]) if parts[0] else 0
                        minutos = int(parts[1]) if parts[1] else 0
                        horas_trabajadas = horas + (minutos / 60)
                except:
                    horas_trabajadas = 0
            
            # Convertir fechas
            fecha_trabajo = None
            if fecha_completado and fecha_completado != 'nan':
                try:
                    fecha_trabajo = pd.to_datetime(fecha_completado, format='%d/%m/%y')
                except:
                    try:
                        fecha_trabajo = pd.to_datetime(fecha_completado)
                    except:
                        fecha_trabajo = datetime.now()
            elif fecha_recepcion and fecha_recepcion != 'nan':
                try:
                    fecha_trabajo = pd.to_datetime(fecha_recepcion, format='%d/%m/%y')
                except:
                    try:
                        fecha_trabajo = pd.to_datetime(fecha_recepcion)
                    except:
                        fecha_trabajo = datetime.now()
            
            if mecanico and mecanico != 'nan' and horas_trabajadas > 0:
                # Buscar el técnico por código
                technician = Technician.query.filter_by(code=mecanico).first()
                technician_id = technician.id if technician else None
                
                processed_data.append({
                    'technician_id': technician_id,
                    'technician_name': mecanico,
                    'order_number': orden if orden != 'nan' else None,
                    'date_worked': fecha_trabajo or datetime.now(),
                    'hours_worked': horas_trabajadas,
                    'description': descripcion if descripcion != 'nan' else f'Trabajo en orden {orden}'
                })
        except Exception as e:
            continue
    
    return processed_data

def parse_orders_file(file_path):
    """Procesar archivo Excel de órdenes pendientes a facturar - Versión mejorada"""
    import pandas as pd
    import os
    
    # Verificar que el archivo existe
    if not os.path.exists(file_path):
        raise Exception(f"El archivo no existe: {file_path}")
    
    # Verificar el tamaño del archivo
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise Exception("El archivo está vacío")
    
    df_list = None
    
    # Método 1: Intentar leer como Excel real (.xlsx, .xls)
    try:
        print(f"🔍 Intentando leer como Excel real: {file_path}")
        df = pd.read_excel(file_path, engine='openpyxl')
        if df is not None and not df.empty:
            df_list = [df]
            print("✅ Archivo leído exitosamente como Excel")
    except Exception as e:
        print(f"❌ Error leyendo como Excel: {e}")
        
        # Método 2: Intentar con engine xlrd para archivos .xls antiguos
        try:
            print("🔍 Intentando con engine xlrd...")
            df = pd.read_excel(file_path, engine='xlrd')
            if df is not None and not df.empty:
                df_list = [df]
                print("✅ Archivo leído exitosamente con xlrd")
        except Exception as e2:
            print(f"❌ Error con xlrd: {e2}")
    
    # Método 3: Leer como HTML (para archivos .xls que son HTML)
    if df_list is None:
        try:
            print("🔍 Intentando leer como HTML...")
            df_list = read_html_with_encoding(file_path)
            print("✅ Archivo leído exitosamente como HTML")
        except Exception as e3:
            print(f"❌ Error leyendo como HTML: {e3}")
    
    # Método 4: Usar método robusto
    if df_list is None:
        try:
            print("🔍 Intentando método robusto...")
            df_list = read_html_robust(file_path)
            print("✅ Archivo leído exitosamente con método robusto")
        except Exception as e4:
            print(f"❌ Error con método robusto: {e4}")
    
    # Si todos los métodos fallan
    if df_list is None or len(df_list) == 0:
        raise Exception(f"No se pudo leer el archivo con ningún método robusto. Archivo: {file_path}, Tamaño: {file_size} bytes. Verifique que el archivo sea un archivo Excel válido (.xls o .xlsx).")
    
    try:
        df = df_list[0]  # Primera tabla
        
        print(f"📊 Datos leídos: {len(df)} filas, {len(df.columns)} columnas")
        print(f"📋 Primeras columnas: {list(df.columns[:5])}")
        
        # Detectar automáticamente la fila de encabezados
        header_row = None
        for i in range(min(10, len(df))):  # Buscar en las primeras 10 filas
            row_values = df.iloc[i].values
            # Buscar patrones que indiquen encabezados
            if any(str(val).lower() in ['orden', 'placa', 'cliente', 'fecha', 'no. orden', 'numero orden'] for val in row_values if pd.notna(val)):
                header_row = i
                break
        
        if header_row is None:
            # Si no se encuentra encabezado, usar la primera fila
            header_row = 0
            df_clean = df.copy()
            print("📌 Usando primera fila como encabezados")
        else:
            print(f"📌 Encabezados encontrados en fila {header_row}")
            # Usar la fila detectada como encabezados
            df_clean = df.iloc[header_row+1:].copy()
            df_clean.columns = df.iloc[header_row].values
            df_clean = df_clean.reset_index(drop=True)
        
        print(f"📊 Datos después de limpiar: {len(df_clean)} filas")
        
        # Mapeo de columnas más flexible basado en contenido
        column_mapping = {
            'receptor_code': ['receptor', 'codigo receptor', 'cod receptor', 'receptor code'],
            'receptor_name': ['receptor', 'nombre receptor', 'receptor nombre', 'receptor name'],
            'tipo_orden': ['tipo', 'tipo orden', 'tipo de orden', 'type'],
            'order_number': ['orden', 'numero orden', 'no orden', 'no. orden', 'order', 'numero', 'numero de orden'],
            'priority': ['prioridad', 'priority', 'pri'],
            'plate': ['placa', 'plate', 'matricula', 'placas'],
            'vin': ['vin', 'chasis', 'chassis', 'numero chasis'],
            'customer_code': ['codigo cliente', 'cod cliente', 'customer code', 'cliente code'],
            'customer_name': ['cliente', 'nombre cliente', 'customer', 'customer name', 'cliente name'],
            'supervisor_code': ['codigo supervisor', 'cod supervisor', 'supervisor code', 'supervisor cod'],
            'supervisor_name': ['supervisor', 'nombre supervisor', 'supervisor name', 'supervisor nombre'],
            'reception_date': ['fecha recepcion', 'reception date', 'fecha', 'fecha ingreso', 'ingreso', 'recepción', 'reception'],
            'promised_date': ['fecha prometida', 'promised date', 'promesa', 'fecha entrega', 'promised', 'completado'],
            'status_code': ['codigo estado', 'cod estado', 'status code', 'estado code'],
            'status_name': ['estado', 'status', 'status name', 'estado name'],
            'vehicle_type': ['tipo vehiculo', 'vehicle type', 'tipo vehículo'],
            'vehicle_type_name': ['nombre tipo vehiculo', 'vehicle type name', 'tipo vehiculo name'],
            'model_code': ['codigo modelo', 'cod modelo', 'model code', 'modelo code'],
            'model_name': ['modelo', 'model', 'model name', 'modelo name'],
            'brand_code': ['codigo marca', 'cod marca', 'brand code', 'marca code'],
            'brand_name': ['marca', 'brand', 'brand name', 'marca name'],
            'color': ['color', 'colores'],
            'total_value': ['valor', 'total', 'total value', 'valor total', 'precio'],
            'comments': ['comentarios', 'comments', 'observaciones', 'obs', 'notas', 'descripción', 'description']
        }
        
        # Renombrar columnas basado en coincidencias
        new_columns = []
        for i, col in enumerate(df_clean.columns):
            col_str = str(col).lower().strip()
            mapped = False
            
            for target_col, patterns in column_mapping.items():
                if any(pattern in col_str for pattern in patterns):
                    new_columns.append(target_col)
                    mapped = True
                    break
            
            if not mapped:
                new_columns.append(f'col_{i}')
        
        df_clean.columns = new_columns
        print(f"📋 Columnas mapeadas: {list(df_clean.columns)}")
        
        # Procesar datos para extraer órdenes
        processed_orders = []
        
        for idx, row in df_clean.iterrows():
            try:
                # Extraer datos básicos
                order_number = str(row.get('order_number', '')).strip() if pd.notna(row.get('order_number')) else ''
                plate = str(row.get('plate', '')).strip() if pd.notna(row.get('plate')) else ''
                customer_name = str(row.get('customer_name', '')).strip() if pd.notna(row.get('customer_name')) else ''
                
                # Solo procesar si tiene datos mínimos
                if not order_number and not plate:
                    continue
                
                # Procesar fechas - buscar en diferentes columnas posibles
                reception_date = None
                promised_date = None
                
                # Buscar fecha de recepción en diferentes columnas
                reception_columns = ['reception_date', 'reception', 'fecha_recepcion', 'fecha', 'ingreso']
                for col in reception_columns:
                    if pd.notna(row.get(col)):
                        try:
                            reception_date = pd.to_datetime(row.get(col))
                            print(f"   📅 Fecha recepción encontrada en columna '{col}': {reception_date.date()}")
                            break
                        except:
                            continue
                
                # Si no se encontró fecha de recepción, usar fecha actual como fallback
                if reception_date is None:
                    reception_date = utcnow()
                    print(f"   ⚠️  No se encontró fecha de recepción, usando fecha actual: {reception_date.date()}")
                
                # Buscar fecha prometida
                promised_columns = ['promised_date', 'promised', 'fecha_prometida', 'promesa', 'entrega']
                for col in promised_columns:
                    if pd.notna(row.get(col)):
                        try:
                            promised_date = pd.to_datetime(row.get(col))
                            print(f"   📅 Fecha prometida encontrada en columna '{col}': {promised_date.date()}")
                            break
                        except:
                            continue
                
                # Crear orden procesada
                order_data = {
                    'order_number': order_number,
                    'plate': plate,
                    'vin': str(row.get('vin', '')).strip() if pd.notna(row.get('vin')) else '',
                    'chasis': str(row.get('vin', '')).strip() if pd.notna(row.get('vin')) else '',
                    'brand': str(row.get('brand_name', '')).strip() if pd.notna(row.get('brand_name')) else '',
                    'modelo': str(row.get('model_name', '')).strip() if pd.notna(row.get('model_name')) else '',
                    'customer_name': customer_name,
                    'advisor': str(row.get('receptor_name', '')).strip() if pd.notna(row.get('receptor_name')) else '',
                    'technician': '',  # Se asignará después
                    'technician_id': None,
                    'service_type': 'Mantenimiento',
                    'status': 'RECEPCION',
                    'symptom': str(row.get('comments', '')).strip() if pd.notna(row.get('comments')) else '',
                    'priority': str(row.get('priority', 'NORMAL')).strip() if pd.notna(row.get('priority')) else 'NORMAL',
                    'promised_date': promised_date,
                    'reception_date': reception_date or utcnow()
                }
                
                processed_orders.append(order_data)
                
            except Exception as e:
                print(f"Error procesando fila {idx}: {e}")
                continue
        
        print(f"✅ Órdenes procesadas: {len(processed_orders)}")
        return processed_orders
        
    except Exception as e:
        raise Exception(f"Error procesando archivo de órdenes: {str(e)}")

# ---------- Decoradores de Autorización ----------
def admin_required(f):
    """Decorador para requerir rol de administrador"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'ADMIN':
            flash('Acceso denegado. Se requieren permisos de administrador.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ---------- Flask-Login Callback ----------
@login_manager.user_loader
def load_user(user_id):
    """Cargar usuario desde la base de datos"""
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        print(f"Error cargando usuario {user_id}: {e}")
        return None

# ---------- Routes ----------
# Rutas de Autenticación
@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        # Verificar si el usuario está autenticado de forma segura
        try:
            if current_user.is_authenticated:
                return redirect(url_for('dashboard'))
        except Exception as auth_error:
            # Si hay error al verificar autenticación, continuar con el login
            print(f"Warning: Error verificando autenticación: {auth_error}")
        
        form = LoginForm()
        if form.validate_on_submit():
            try:
                user = User.query.filter_by(username=form.username.data).first()
                if user and user.check_password(form.password.data) and user.is_active:
                    login_user(user)
                    flash(f'¡Bienvenido, {user.full_name}!', 'success')
                    next_page = request.args.get('next')
                    return redirect(next_page) if next_page else redirect(url_for('dashboard'))
                else:
                    flash('Usuario o contraseña incorrectos', 'error')
            except Exception as db_error:
                print(f"Error en login (base de datos): {db_error}")
                flash('Error de conexión a la base de datos. Por favor, contacta al administrador.', 'error')
        
        return render_template("login.html", form=form)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error en ruta /login: {e}")
        print(f"Traceback: {error_trace}")
        # Re-lanzar para que el handler de errores lo capture
        raise

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        # Verificar si el usuario ya existe
        if User.query.filter_by(username=form.username.data).first():
            flash('El nombre de usuario ya existe', 'error')
            return render_template("register.html", form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('El email ya está registrado', 'error')
            return render_template("register.html", form=form)
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('Usuario registrado exitosamente. Puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
    
    return render_template("register.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente', 'info')
    return redirect(url_for('login'))

@app.route("/")
@login_required
def dashboard():
    try:
        # Obtener parámetros de filtro
        brand_filter = request.args.get("brand", "")
        
        # Obtener estatus dinámicos
        status_choices = get_status_choices()
        status_names = [s[0] for s in status_choices]
        
        # Query base filtrada por rol del usuario
        base_query = get_orders_for_user(current_user)
        if brand_filter:
            base_query = base_query.filter(Order.brand.like(f"%{brand_filter}%"))
        
        # Aggregate counts per status con filtro de marca
        counts = {}
        for status in status_names:
            try:
                status_query = base_query.filter_by(status=status)
                counts[status] = status_query.count()
            except Exception as e:
                print(f"Error contando estatus {status}: {e}")
                counts[status] = 0
        
        total = sum(counts.values())
        
        # Órdenes más antiguas con filtro
        oldest = None
        oldest_days = 0
        try:
            oldest_query = base_query.order_by(Order.created_at.asc())
            oldest = oldest_query.first()
            if oldest:
                oldest_days = oldest.days_in_shop()
        except Exception as e:
            print(f"Error obteniendo orden más antigua: {e}")
        
        # Órdenes con 15+ días con filtro
        long_15 = []
        try:
            long_stays_query = base_query.filter(Order.status != "ENTREGADO")
            long_stays = long_stays_query.all()
            long_15 = [o for o in long_stays if o.days_in_shop() >= 15]
            
            # Cargar comentarios para las órdenes con 15+ días
            for order in long_15:
                try:
                    order.comments = OrderComment.query.filter_by(order_id=order.id).order_by(OrderComment.created_at.desc()).all()
                except Exception as e:
                    print(f"Error cargando comentarios para orden {order.id}: {e}")
                    order.comments = []
        except Exception as e:
            print(f"Error obteniendo órdenes con 15+ días: {e}")
        
        # Obtener marcas únicas para el filtro
        brands = []
        try:
            brands_query = db.session.query(Order.brand).filter(Order.brand.isnot(None)).distinct().all()
            brands = [b[0] for b in brands_query if b[0]]
        except Exception as e:
            print(f"Error obteniendo marcas: {e}")

        # Obtener colores de estado desde la base de datos
        status_colors = get_status_colors()

        return render_template("dashboard.html",
                             counts=counts,
                             total=total,
                             oldest_days=oldest_days,
                             long_15=long_15,
                             STATUS_CHOICES=status_choices,
                             status_colors=status_colors,
                             brands=brands,
                             selected_brand=brand_filter)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error en dashboard: {e}")
        print(f"Traceback: {error_trace}")
        # Re-lanzar el error para que el handler de errores lo capture
        raise

@app.route("/orders")
@login_required
def list_orders():
    status = request.args.get("status")
    brand = request.args.get("brand")
    advisor = request.args.get("advisor")
    q = request.args.get("q", "")
    sort_by = request.args.get("sort", "created_at")
    sort_order = request.args.get("order", "desc")
    
    # Query base filtrada por rol del usuario
    query = get_orders_for_user(current_user)
    
    # Obtener estatus dinámicos para validación
    valid_statuses = get_status_list()
    
    # Filtros
    if status and status in valid_statuses:
        query = query.filter_by(status=status)
    if brand:
        query = query.filter(Order.brand.like(f"%{brand}%"))
    if advisor:
        query = query.filter(Order.advisor.like(f"%{advisor}%"))
    
    # Búsqueda general
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Order.order_number.like(like),
                Order.plate.like(like),
                Order.customer_name.like(like),
                Order.vin.like(like),
                Order.chasis.like(like),
                Order.brand.like(like),
                Order.modelo.like(like),
                Order.advisor.like(like),
                Order.technician.like(like),
            )
        )
    
    # Ordenamiento
    valid_sort_fields = {
        'id': Order.id,
        'order_number': Order.order_number,
        'plate': Order.plate,
        'brand': Order.brand,
        'modelo': Order.modelo,
        'customer_name': Order.customer_name,
        'advisor': Order.advisor,
        'technician': Order.technician,
        'service_type': Order.service_type,
        'status': Order.status,
        'created_at': Order.created_at,
        'promised_date': Order.promised_date
    }
    
    if sort_by in valid_sort_fields:
        sort_field = valid_sort_fields[sort_by]
        if sort_order == "asc":
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())
    else:
        # Ordenamiento por defecto
        query = query.order_by(Order.created_at.desc())
    
    orders = query.all()
    
    # Cargar comentarios para cada orden
    for order in orders:
        order.comments = OrderComment.query.filter_by(order_id=order.id).order_by(OrderComment.created_at.desc()).all()
    
    # Obtener listas únicas para filtros
    brands = db.session.query(Order.brand).filter(Order.brand.isnot(None)).distinct().all()
    advisors = db.session.query(Order.advisor).filter(Order.advisor.isnot(None)).distinct().all()
    
    # Obtener estatus dinámicos
    status_choices = get_status_choices()
    
    # Obtener colores de estado desde la base de datos
    status_colors = get_status_colors()
    
    return render_template("orders_list.html", 
                         orders=orders, 
                         STATUS_CHOICES=status_choices, 
                         status_colors=status_colors,
                         selected_status=status,
                         selected_brand=brand,
                         selected_advisor=advisor,
                         brands=[b[0] for b in brands],
                         advisors=[a[0] for a in advisors],
                         q=q,
                         sort_by=sort_by,
                         sort_order=sort_order)

@app.route("/orders/new", methods=["GET", "POST"])
@login_required
def new_order():
    if request.method == "POST":
        # Obtener asesor y técnico por ID
        advisor_id = request.form.get("advisor_id")
        technician_id = request.form.get("technician_id")
        
        advisor = Advisor.query.get(advisor_id) if advisor_id else None
        technician = Technician.query.get(technician_id) if technician_id else None
        
        order = Order(
            order_number=request.form["order_number"],
            plate=request.form["plate"].upper(),
            vin=request.form.get("vin") or None,
            chasis=request.form.get("chasis") or None,
            brand=request.form.get("brand") or None,
            modelo=request.form.get("modelo") or None,
            customer_name=request.form["customer_name"],
            advisor=advisor.full_name if advisor else None,  # Para compatibilidad
            advisor_id=advisor_id or None,
            technician=technician.full_name if technician else None,  # Para compatibilidad
            technician_id=technician_id or None,
            technician_assigned_at=utcnow() if technician_id else None,  # Fecha de asignación
            service_type=request.form.get("service_type") or "Mantenimiento",
            status=request.form.get("status") or "RECEPCION",
            priority=request.form.get("priority") or "NORMAL",
            symptom=request.form.get("symptom") or None,
            promised_date=datetime.fromisoformat(request.form["promised_date"]) if request.form.get("promised_date") else None
        )
        db.session.add(order)
        db.session.commit()
        
        # Crear entrada inicial en el historial de estatus
        status_history = StatusHistory(
            order_id=order.id,
            old_status=None,
            new_status=order.status,
            changed_by="Sistema",
            change_reason="Orden creada"
        )
        db.session.add(status_history)
        db.session.commit()
        
        flash("Orden creada correctamente.", "success")
        return redirect(url_for("list_orders"))
    
    # Obtener asesores y técnicos activos para los dropdowns
    advisors = Advisor.query.filter_by(is_active=True).order_by(Advisor.code).all()
    technicians = Technician.query.filter_by(is_active=True).order_by(Technician.code).all()
    
    # Obtener estatus dinámicos
    status_choices = get_status_choices()
    
    return render_template("order_form.html", 
                         STATUS_CHOICES=status_choices,
                         advisors=advisors,
                         technicians=technicians)

@app.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    status_history = StatusHistory.query.filter_by(order_id=order_id).order_by(StatusHistory.created_at.desc()).all()
    comments = OrderComment.query.filter_by(order_id=order_id).order_by(OrderComment.created_at.desc()).all()
    # Obtener estatus dinámicos
    status_choices = get_status_choices()
    
    # Obtener colores de estado desde la base de datos
    status_colors = get_status_colors()
    
    return render_template("order_detail.html", 
                         order=order, 
                         STATUS_CHOICES=status_choices,
                         status_colors=status_colors,
                         status_history=status_history,
                         comments=comments)

@app.route("/orders/<int:order_id>/edit", methods=["GET", "POST"])
@login_required
def edit_order(order_id):
    order = Order.query.get_or_404(order_id)
    
    if request.method == "POST":
        # Guardar estado anterior para el historial
        old_status = order.status
        
        # Obtener asesor y técnico por ID
        advisor_id = request.form.get("advisor_id")
        technician_id = request.form.get("technician_id")
        
        advisor = Advisor.query.get(advisor_id) if advisor_id else None
        technician = Technician.query.get(technician_id) if technician_id else None
        
        # Verificar si se está asignando un técnico por primera vez
        old_technician_id = order.technician_id
        new_technician_id = technician_id or None
        
        # Actualizar campos de la orden
        order.order_number = request.form["order_number"]
        order.plate = request.form["plate"].upper()
        order.vin = request.form.get("vin") or None
        order.chasis = request.form.get("chasis") or None
        order.brand = request.form.get("brand") or None
        order.modelo = request.form.get("modelo") or None
        order.customer_name = request.form["customer_name"]
        order.advisor = advisor.full_name if advisor else None  # Para compatibilidad
        order.advisor_id = advisor_id or None
        order.technician = technician.full_name if technician else None  # Para compatibilidad
        order.technician_id = new_technician_id
        
        # Actualizar fecha de asignación al técnico si se asigna por primera vez
        if not old_technician_id and new_technician_id:
            order.technician_assigned_at = utcnow()
        elif old_technician_id and not new_technician_id:
            order.technician_assigned_at = None
        
        order.service_type = request.form.get("service_type") or "Mantenimiento"
        order.priority = request.form.get("priority") or "NORMAL"
        order.symptom = request.form.get("symptom") or None
        
        # Manejar fecha prometida
        if request.form.get("promised_date"):
            order.promised_date = datetime.fromisoformat(request.form["promised_date"])
        else:
            order.promised_date = None
        
        # Si cambió el estado, crear entrada en el historial
        new_status = request.form.get("status") or "RECEPCION"
        changed_by = current_user.full_name or current_user.username or "Usuario"
        if old_status != new_status:
            order.status = new_status
            status_history = StatusHistory(
                order_id=order.id,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
                change_reason=f"Cambio de estado de {old_status} a {new_status} (edición de orden)"
            )
            db.session.add(status_history)
        
        db.session.commit()
        
        # Notificar al asesor si el cambio fue hecho por admin, jefe de taller o supervisor
        if is_admin_or_manager(current_user):
            change_description = f"El estado cambió de {old_status} a {new_status}. Editado por {changed_by}."
            notify_advisor_on_order_change(order, change_description, changed_by)
        
        flash("Orden actualizada correctamente.", "success")
        return redirect(url_for("list_orders"))
    
    # Preparar datos para el formulario
    form_data = {
        'order_number': order.order_number,
        'plate': order.plate,
        'vin': order.vin or '',
        'chasis': order.chasis or '',
        'brand': order.brand or '',
        'modelo': order.modelo or '',
        'customer_name': order.customer_name,
        'advisor': order.advisor or '',
        'advisor_id': order.advisor_id or '',
        'technician': order.technician or '',
        'technician_id': order.technician_id or '',
        'service_type': order.service_type,
        'priority': order.priority,
        'status': order.status,
        'symptom': order.symptom or '',
        'promised_date': order.promised_date.strftime('%Y-%m-%dT%H:%M') if order.promised_date else ''
    }
    
    # Obtener asesores y técnicos activos para los dropdowns
    advisors = Advisor.query.filter_by(is_active=True).order_by(Advisor.code).all()
    technicians = Technician.query.filter_by(is_active=True).order_by(Technician.code).all()
    
    # Obtener estatus dinámicos
    status_choices = get_status_choices()
    
    return render_template("order_edit.html", 
                         order=order, 
                         form_data=form_data,
                         advisors=advisors,
                         technicians=technicians,
                         STATUS_CHOICES=status_choices)

@app.route("/orders/<int:order_id>/delete", methods=["POST"])
@login_required
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash("Orden eliminada.", "info")
    return redirect(url_for("list_orders"))

@app.route("/orders/<int:order_id>/status", methods=["POST"])
@login_required
def update_status(order_id):
    print(f"🔥 update_status llamada - order_id: {order_id}")
    print(f"📥 Headers: {dict(request.headers)}")
    print(f"📥 Raw data: {request.get_data()}")
    
    order = Order.query.get_or_404(order_id)
    new_status = request.json.get("status")
    change_reason = request.json.get("reason", "")
    
    print(f"📊 Datos recibidos - new_status: {new_status}, reason: {change_reason}")
    print(f"📊 Tipo de new_status: {type(new_status)}")
    print(f"📊 new_status.upper(): {new_status.upper() if new_status else 'None'}")
    
    # Usar el usuario actual en lugar del valor por defecto
    changed_by = current_user.full_name or current_user.username or "Usuario"
    
    # Validar que el estatus sea válido
    valid_statuses = get_status_list()
    print(f"📋 Estados válidos: {valid_statuses}")
    
    if new_status not in valid_statuses:
        print(f"❌ Estado inválido: {new_status}")
        return jsonify({"ok": False, "error": "Estado inválido"}), 400
    
    old_status = order.status
    order.status = new_status
    
    # Agregar razón por defecto si no se proporciona
    if not change_reason:
        change_reason = f"Cambio de estado de {old_status} a {new_status}"
    
    # Registrar en el historial
    status_history = StatusHistory(
        order_id=order.id,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        change_reason=change_reason
    )
    db.session.add(status_history)
    db.session.commit()
    
    print(f"✅ Estado cambiado de {old_status} a {new_status}")
    
    # Notificar al asesor si el cambio fue hecho por admin, jefe de taller o supervisor
    if is_admin_or_manager(current_user):
        change_description = f"El estado cambió de {old_status} a {new_status}. Razón: {change_reason}"
        notify_advisor_on_order_change(order, change_description, changed_by)
    
    # Verificar si el nuevo estado requiere información adicional del taller de pintura
    paint_shop_statuses = ["EN_TALLER_PINTURA", "TALLER_PINTURA", "EN_TALLER_DE_PINTURA"]
    
    if new_status.upper() in paint_shop_statuses:
        print("🎨 Requiere información de taller de pintura")
        return jsonify({"ok": True, "requires_paint_shop_info": True})
    
    # Verificar si el nuevo estado requiere información de repuestos
    print(f"🔍 Verificando si {new_status.upper()} == ESPERA_REPUESTOS")
    if new_status.upper() == "ESPERA_REPUESTOS":
        print("🔧 Requiere información de repuestos - retornando requires_repuestos_info: true")
        return jsonify({"ok": True, "requires_repuestos_info": True})
    
    print("✅ Cambio de estado normal")
    return jsonify({"ok": True})

@app.route("/api/status-choices")
@login_required
def api_status_choices():
    """API para obtener opciones de estatus para JavaScript"""
    status_choices = get_status_choices()
    return jsonify(status_choices)

@app.route("/orders/<int:order_id>/repuestos", methods=["GET", "POST"])
@login_required
def manage_repuestos(order_id):
    """Gestionar repuestos para una orden"""
    order = Order.query.get_or_404(order_id)
    
    if request.method == "POST":
        try:
            data = request.json
            repuesto = Repuesto(
                order_id=order.id,
                numero_parte=data.get('numero_parte'),
                descripcion=data.get('descripcion'),
                cantidad=data.get('cantidad', 1),
                estatus=data.get('estatus', 'PENDIENTE'),
                numero_pedido=data.get('numero_pedido'),
                fecha_pedido=datetime.strptime(data.get('fecha_pedido'), '%Y-%m-%d').date() if data.get('fecha_pedido') else None,
                fecha_facturacion=datetime.strptime(data.get('fecha_facturacion'), '%Y-%m-%d').date() if data.get('fecha_facturacion') else None,
                costo_unitario=data.get('costo_unitario'),
                costo_total=data.get('costo_total'),
                proveedor=data.get('proveedor'),
                notas=data.get('notas')
            )
            db.session.add(repuesto)
            db.session.commit()
            return jsonify({"ok": True, "repuesto_id": repuesto.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
    
    # GET - Obtener repuestos de la orden
    repuestos = Repuesto.query.filter_by(order_id=order.id).order_by(Repuesto.created_at.desc()).all()
    repuestos_data = []
    for repuesto in repuestos:
        repuestos_data.append({
            "id": repuesto.id,
            "numero_parte": repuesto.numero_parte,
            "descripcion": repuesto.descripcion,
            "cantidad": repuesto.cantidad,
            "estatus": repuesto.estatus,
            "numero_pedido": repuesto.numero_pedido,
            "fecha_pedido": repuesto.fecha_pedido.strftime('%Y-%m-%d') if repuesto.fecha_pedido else None,
            "fecha_facturacion": repuesto.fecha_facturacion.strftime('%Y-%m-%d') if repuesto.fecha_facturacion else None,
            "costo_unitario": repuesto.costo_unitario,
            "costo_total": repuesto.costo_total,
            "proveedor": repuesto.proveedor,
            "notas": repuesto.notas,
            "created_at": repuesto.created_at.strftime('%d/%m/%Y %H:%M')
        })
    
    return jsonify({"ok": True, "repuestos": repuestos_data})

@app.route("/orders/<int:order_id>/repuestos/form", methods=["GET", "POST"])
@login_required
def repuestos_form(order_id):
    """Formulario para agregar repuestos y cambiar estado a ESPERA_REPUESTOS"""
    order = Order.query.get_or_404(order_id)
    
    if request.method == "POST":
        try:
            # Crear el repuesto
            repuesto = Repuesto(
                order_id=order.id,
                numero_parte=request.form.get('numero_parte'),
                descripcion=request.form.get('descripcion'),
                cantidad=int(request.form.get('cantidad', 1)),
                estatus=request.form.get('estatus', 'PENDIENTE'),
                numero_pedido=request.form.get('numero_pedido'),
                fecha_pedido=datetime.strptime(request.form.get('fecha_pedido'), '%Y-%m-%d').date() if request.form.get('fecha_pedido') else None,
                fecha_facturacion=datetime.strptime(request.form.get('fecha_facturacion'), '%Y-%m-%d').date() if request.form.get('fecha_facturacion') else None,
                costo_unitario=float(request.form.get('costo_unitario')) if request.form.get('costo_unitario') else None,
                costo_total=float(request.form.get('costo_total')) if request.form.get('costo_total') else None,
                proveedor=request.form.get('proveedor'),
                notas=request.form.get('notas')
            )
            db.session.add(repuesto)
            
            # Cambiar el estado de la orden a ESPERA_REPUESTOS
            old_status = order.status
            order.status = 'ESPERA_REPUESTOS'
            
            # Registrar en el historial
            reason = request.form.get('change_reason', f'Cambio a ESPERA_REPUESTOS - Repuesto: {repuesto.numero_parte}')
            status_history = StatusHistory(
                order_id=order.id,
                old_status=old_status,
                new_status='ESPERA_REPUESTOS',
                changed_by=current_user.full_name or current_user.username or "Usuario",
                change_reason=reason
            )
            db.session.add(status_history)
            
            db.session.commit()
            flash(f'Repuesto guardado y estado cambiado a ESPERA_REPUESTOS', 'success')
            return redirect(url_for('order_detail', order_id=order.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar repuesto: {str(e)}', 'error')
    
    return render_template("repuestos_form.html", order=order)

@app.route("/orders/<int:order_id>/quick-status", methods=["GET", "POST"])
@login_required
def quick_status_change(order_id):
    """Cambio rápido de estado para una orden"""
    order = Order.query.get_or_404(order_id)
    
    if request.method == "POST":
        try:
            new_status = request.form.get('new_status')
            reason = request.form.get('reason', '')
            
            if not new_status:
                flash('Por favor selecciona un estado', 'error')
                return render_template("quick_status.html", order=order, status_choices=get_status_choices())
            
            # Validar que el estatus sea válido
            valid_statuses = get_status_list()
            if new_status not in valid_statuses:
                flash('Estado inválido', 'error')
                return render_template("quick_status.html", order=order, status_choices=get_status_choices())
            
            old_status = order.status
            order.status = new_status
            
            # Agregar razón por defecto si no se proporciona
            if not reason:
                reason = f"Cambio de estado de {old_status} a {new_status}"
            
            # Registrar en el historial
            status_history = StatusHistory(
                order_id=order.id,
                old_status=old_status,
                new_status=new_status,
                changed_by=current_user.full_name or current_user.username or "Usuario",
                change_reason=reason
            )
            db.session.add(status_history)
            db.session.commit()
            
            flash(f'Estado cambiado de {old_status} a {new_status}', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al cambiar estado: {str(e)}', 'error')
    
    return render_template("quick_status.html", order=order, status_choices=get_status_choices())

# ---------- Rutas para Información del Taller de Pintura ----------
@app.route("/orders/<int:order_id>/paint-shop-info", methods=["GET", "POST"])
@login_required
def paint_shop_info(order_id):
    """Gestionar información del taller de pintura para una orden"""
    order = Order.query.get_or_404(order_id)
    
    if request.method == "POST":
        form = PaintShopInfoForm()
        if form.validate_on_submit():
            # Verificar si ya existe información para esta orden
            existing_info = PaintShopInfo.query.filter_by(order_id=order_id).first()
            
            if existing_info:
                # Actualizar información existente
                existing_info.shop_name = form.shop_name.data
                # Convertir fecha a datetime (asumiendo hora 00:00:00)
                existing_info.send_date = datetime.combine(form.send_date.data, datetime.min.time())
                if form.delivery_date.data:
                    existing_info.delivery_date = datetime.combine(form.delivery_date.data, datetime.min.time())
                else:
                    existing_info.delivery_date = None
                existing_info.notes = form.notes.data
                
                # Manejar archivo de copia de orden de seguro
                if form.insurance_order_copy.data:
                    file = form.insurance_order_copy.data
                    if file and allowed_image_file(file.filename):
                        filename = secure_filename(file.filename)
                        # Crear subdirectorio para archivos de seguro
                        insurance_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'insurance_orders')
                        os.makedirs(insurance_folder, exist_ok=True)
                        file_path = os.path.join(insurance_folder, f"{order_id}_{filename}")
                        file.save(file_path)
                        # Guardar solo la ruta relativa desde static
                        existing_info.insurance_order_copy = f"uploads/insurance_orders/{order_id}_{filename}"
                
                db.session.commit()
                flash("Información del taller de pintura actualizada correctamente.", "success")
            else:
                # Crear nueva información
                insurance_file_path = None
                if form.insurance_order_copy.data:
                    file = form.insurance_order_copy.data
                    if file and allowed_image_file(file.filename):
                        filename = secure_filename(file.filename)
                        insurance_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'insurance_orders')
                        os.makedirs(insurance_folder, exist_ok=True)
                        file_path = os.path.join(insurance_folder, f"{order_id}_{filename}")
                        file.save(file_path)
                        # Guardar solo la ruta relativa desde static
                        insurance_file_path = f"uploads/insurance_orders/{order_id}_{filename}"
                
                paint_shop_info = PaintShopInfo(
                    order_id=order_id,
                    shop_name=form.shop_name.data,
                    # Convertir fecha a datetime (asumiendo hora 00:00:00)
                    send_date=datetime.combine(form.send_date.data, datetime.min.time()),
                    delivery_date=datetime.combine(form.delivery_date.data, datetime.min.time()) if form.delivery_date.data else None,
                    insurance_order_copy=insurance_file_path,
                    notes=form.notes.data
                )
                db.session.add(paint_shop_info)
                db.session.commit()
                flash("Información del taller de pintura guardada correctamente.", "success")
            
            return redirect(url_for("order_detail", order_id=order_id))
    else:
        # GET - Mostrar formulario
        form = PaintShopInfoForm()
        # Cargar datos existentes si los hay
        existing_info = PaintShopInfo.query.filter_by(order_id=order_id).first()
        if existing_info:
            form.shop_name.data = existing_info.shop_name
            form.send_date.data = existing_info.send_date.date() if existing_info.send_date else None
            form.delivery_date.data = existing_info.delivery_date.date() if existing_info.delivery_date else None
            form.notes.data = existing_info.notes
    
    # Obtener información existente para el template (tanto para GET como POST)
    existing_info = PaintShopInfo.query.filter_by(order_id=order_id).first()
    
    # Obtener colores de estado desde la base de datos
    status_colors = get_status_colors()
    
    return render_template("paint_shop_info_form.html", 
                         form=form, 
                         order=order, 
                         existing_info=existing_info,
                         status_colors=status_colors)

@app.route("/orders/<int:order_id>/paint-shop-info/view")
@login_required
def view_paint_shop_info(order_id):
    """Ver información del taller de pintura"""
    order = Order.query.get_or_404(order_id)
    paint_shop_info = PaintShopInfo.query.filter_by(order_id=order_id).first()
    
    if not paint_shop_info:
        flash("No hay información del taller de pintura para esta orden.", "info")
        return redirect(url_for("order_detail", order_id=order_id))
    
    # Obtener colores de estado desde la base de datos
    status_colors = get_status_colors()
    
    return render_template("paint_shop_info_view.html", 
                         order=order, 
                         paint_shop_info=paint_shop_info,
                         status_colors=status_colors)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """Servir archivos subidos desde la carpeta uploads"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/orders/<int:order_id>/paint-shop-info/delete", methods=["POST"])
@login_required
def delete_paint_shop_info(order_id):
    """Eliminar información del taller de pintura"""
    paint_shop_info = PaintShopInfo.query.filter_by(order_id=order_id).first()
    
    if paint_shop_info:
        # Eliminar archivo de copia de orden de seguro si existe
        if paint_shop_info.insurance_order_copy:
            # Construir la ruta completa del archivo
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], paint_shop_info.insurance_order_copy.replace('uploads/', ''))
            if os.path.exists(full_path):
                os.remove(full_path)
        
        db.session.delete(paint_shop_info)
        db.session.commit()
        flash("Información del taller de pintura eliminada correctamente.", "success")
    else:
        flash("No hay información del taller de pintura para eliminar.", "info")
    
    return redirect(url_for("order_detail", order_id=order_id))

@app.route("/orders/<int:order_id>/comments", methods=["POST"])
@login_required
def add_comment(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        
        # Manejar tanto JSON como formularios tradicionales
        if request.is_json:
            # Petición AJAX
            comment_text = request.json.get("comment")
            author = request.json.get("author", current_user.full_name if current_user else "Usuario")
            comment_type = request.json.get("type", "GENERAL")
        else:
            # Formulario tradicional
            comment_text = request.form.get("comment")
            author = request.form.get("author", current_user.full_name if current_user else "Usuario")
            comment_type = request.form.get("type", "GENERAL")
        
        print(f"🔥 AGREGANDO COMENTARIO - Orden {order_id}")
        print(f"📝 Comentario: {comment_text}")
        print(f"👤 Autor: {author}")
        print(f"🏷️ Tipo: {comment_type}")
        print(f"🌐 Es JSON: {request.is_json}")
        
        if not comment_text:
            if request.is_json:
                return jsonify({"ok": False, "error": "Comentario requerido"}), 400
            else:
                flash("Por favor escribe un comentario", "error")
                return redirect(url_for("order_detail", order_id=order_id))
        
        comment = OrderComment(
            order_id=order.id,
            comment=comment_text,
            author=author,
            comment_type=comment_type
        )
        db.session.add(comment)
        db.session.commit()
        
        print(f"✅ COMENTARIO AGREGADO EXITOSAMENTE - ID: {comment.id}")
        
        # Verificar si el comentario fue hecho por un asesor
        is_advisor_comment = False
        advisor_name = None
        
        if current_user.is_authenticated:
            # Verificar si el usuario actual es un asesor
            if current_user.role == 'ASESOR':
                is_advisor_comment = True
                advisor_name = current_user.full_name
            else:
                # Verificar si el usuario está asociado a un asesor
                advisor = Advisor.query.filter_by(user_id=current_user.id).first()
                if advisor:
                    is_advisor_comment = True
                    advisor_name = advisor.full_name
        
        # Si aún no se detectó como asesor, verificar si el autor del comentario es un asesor
        # (útil para casos donde el comentario viene por JSON/AJAX)
        if not is_advisor_comment and author:
            # Buscar si el autor corresponde a un asesor
            advisor_by_name = Advisor.query.filter_by(full_name=author).first()
            if advisor_by_name:
                is_advisor_comment = True
                advisor_name = advisor_by_name.full_name
            else:
                # Buscar por usuario asociado
                user_by_name = User.query.filter_by(full_name=author, role='ASESOR').first()
                if user_by_name:
                    is_advisor_comment = True
                    advisor_name = user_by_name.full_name
        
        # Si el comentario es de un asesor, notificar a administradores, jefes de taller y supervisores
        if is_advisor_comment and advisor_name:
            notify_managers_on_advisor_comment(order, comment_text, advisor_name)
        
        # Notificar al asesor cuando se agrega un comentario (si no es el mismo asesor)
        # Solo notificar si el comentario no fue hecho por el asesor de la orden
        advisor = Advisor.query.get(order.advisor_id) if order.advisor_id else None
        if advisor and author != advisor.full_name:
            notify_advisor_on_comment(order, comment_text, author)
        
        if request.is_json:
            return jsonify({"ok": True, "comment_id": comment.id})
        else:
            flash("Comentario agregado correctamente", "success")
            return redirect(url_for("order_detail", order_id=order_id))
        
    except Exception as e:
        print(f"❌ ERROR AGREGANDO COMENTARIO: {e}")
        db.session.rollback()
        
        if request.is_json:
            return jsonify({"ok": False, "error": str(e)}), 500
        else:
            flash(f"Error al agregar comentario: {str(e)}", "error")
            return redirect(url_for("order_detail", order_id=order_id))

@app.route("/orders/<int:order_id>/comments", methods=["GET"])
@login_required
def get_comments(order_id):
    order = Order.query.get_or_404(order_id)
    comments = OrderComment.query.filter_by(order_id=order_id).order_by(OrderComment.created_at.desc()).all()
    
    comments_data = []
    for comment in comments:
        comments_data.append({
            "id": comment.id,
            "comment": comment.comment,
            "author": comment.author,
            "type": comment.comment_type,
            "created_at": comment.created_at.strftime("%d/%m/%Y %H:%M")
        })
    
    return jsonify({"ok": True, "comments": comments_data})

@app.route("/api/orders/stats")
@login_required
def api_stats():
    counts = {s: Order.query.filter_by(status=s).count() for s in STATUS_CHOICES}
    return jsonify(counts)

# ---------- Rutas de Mantenimiento ----------
@app.route("/maintenance/status")
@login_required
def status_management():
    """Gestión de estatus - Vista principal"""
    # Obtener estatus de la base de datos
    statuses = Status.query.filter_by(is_active=True).order_by(Status.sort_order, Status.name).all()
    
    # Obtener conteos de órdenes por estatus
    status_counts = {}
    for status in statuses:
        status_counts[status.name] = Order.query.filter_by(status=status.name).count()
    
    return render_template("status_management.html", 
                         statuses=statuses, 
                         status_counts=status_counts)

@app.route("/maintenance/status/new", methods=["GET", "POST"])
@login_required
def new_status():
    """Crear nuevo estatus"""
    form = StatusForm()
    
    if form.validate_on_submit():
        # Verificar que el nombre no exista
        existing_status = Status.query.filter_by(name=form.name.data.upper()).first()
        if existing_status:
            flash("Ya existe un estatus con ese nombre.", "error")
            return render_template("status_form.html", form=form, title="Nuevo Estatus")
        
        status = Status(
            name=form.name.data.upper(),
            display_name=form.display_name.data,
            color=form.color.data,
            description=form.description.data,
            is_active=form.is_active.data == 'true',
            sort_order=form.sort_order.data,
            is_final=form.is_final.data == 'true'
        )
        
        db.session.add(status)
        db.session.commit()
        
        flash("Estatus creado correctamente.", "success")
        return redirect(url_for("status_management"))
    
    return render_template("status_form.html", form=form, title="Nuevo Estatus")

@app.route("/maintenance/status/<int:status_id>")
@login_required
def view_status(status_id):
    """Ver detalles de un estatus"""
    status = Status.query.get_or_404(status_id)
    
    # Obtener órdenes con este estatus
    orders = Order.query.filter_by(status=status.name).order_by(Order.created_at.desc()).limit(10).all()
    
    # Estadísticas
    total_orders = Order.query.filter_by(status=status.name).count()
    
    return render_template("status_detail.html", 
                         status=status, 
                         orders=orders, 
                         total_orders=total_orders)

@app.route("/maintenance/status/<int:status_id>/edit", methods=["GET", "POST"])
@login_required
def edit_status(status_id):
    """Editar estatus"""
    status = Status.query.get_or_404(status_id)
    form = StatusForm(obj=status)
    
    # Convertir valores booleanos a strings para el formulario
    if request.method == "GET":
        form.is_active.data = 'true' if status.is_active else 'false'
        form.is_final.data = 'true' if status.is_final else 'false'
    
    if form.validate_on_submit():
        # Verificar que el nombre no exista en otro estatus
        existing_status = Status.query.filter(
            Status.name == form.name.data.upper(),
            Status.id != status_id
        ).first()
        
        if existing_status:
            flash("Ya existe un estatus con ese nombre.", "error")
            return render_template("status_form.html", form=form, title="Editar Estatus", status=status)
        
        status.name = form.name.data.upper()
        status.display_name = form.display_name.data
        status.color = form.color.data
        status.description = form.description.data
        status.is_active = form.is_active.data == 'true'
        status.sort_order = form.sort_order.data
        status.is_final = form.is_final.data == 'true'
        
        db.session.commit()
        
        flash("Estatus actualizado correctamente.", "success")
        return redirect(url_for("status_management"))
    
    return render_template("status_form.html", form=form, title="Editar Estatus", status=status)

@app.route("/maintenance/status/<int:status_id>/delete", methods=["POST"])
@login_required
def delete_status(status_id):
    """Eliminar estatus"""
    status = Status.query.get_or_404(status_id)
    
    # Verificar si hay órdenes con este estatus
    orders_count = Order.query.filter_by(status=status.name).count()
    if orders_count > 0:
        flash(f"No se puede eliminar el estatus porque tiene {orders_count} orden(es) asignada(s).", "error")
        return redirect(url_for("status_management"))
    
    db.session.delete(status)
    db.session.commit()
    
    flash("Estatus eliminado correctamente.", "success")
    return redirect(url_for("status_management"))

@app.route("/maintenance/status/<int:status_id>/toggle-status", methods=["POST"])
@login_required
def toggle_status(status_id):
    """Activar/Desactivar estatus"""
    status = Status.query.get_or_404(status_id)
    status.is_active = not status.is_active
    db.session.commit()
    
    action = "activado" if status.is_active else "desactivado"
    flash(f"Estatus {action} correctamente.", "success")
    return redirect(url_for("status_management"))

@app.route("/maintenance/status/colors")
@login_required
def status_colors():
    """Configuración de colores de estatus"""
    statuses = Status.query.filter_by(is_active=True).order_by(Status.sort_order, Status.name).all()
    status_choices = get_status_choices()
    
    # Crear diccionario de colores para el template
    status_colors = {status.name: status.color for status in statuses}
    
    return render_template("status_colors.html", 
                         statuses=statuses,
                         STATUS_CHOICES=status_choices,
                         status_colors=status_colors)

@app.route("/maintenance/status/update", methods=["POST"])
@login_required
def update_status_config():
    """Actualizar configuración de estatus"""
    data = request.get_json()
    # Aquí podrías guardar configuraciones en base de datos
    # Por ahora solo retornamos éxito
    return jsonify({"ok": True, "message": "Configuración actualizada"})

# ---------- Nuevas Rutas para Módulos de Técnicos ----------
@app.route("/technicians/orders")
@login_required
def technician_orders():
    """Órdenes por técnico - Vista de calendario semanal"""
    # Obtener parámetros de filtro
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    technician_filter = request.args.get("technician", "")
    
    # Configurar fechas por defecto (semana actual)
    if not start_date:
        # Obtener el lunes de la semana actual
        today = datetime.now().date()
        days_since_monday = today.weekday()
        start_date = (today - timedelta(days=days_since_monday)).strftime("%Y-%m-%d")
    if not end_date:
        # Obtener el domingo de la semana actual
        today = datetime.now().date()
        days_until_sunday = 6 - today.weekday()
        end_date = (today + timedelta(days=days_until_sunday)).strftime("%Y-%m-%d")
    
    # Convertir a objetos datetime
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    
    # Obtener todos los técnicos activos
    technicians = Technician.query.filter_by(is_active=True).order_by(Technician.code).all()
    
    # Primero obtener horas del periodo para vincular órdenes trabajadas
    hours_records = TechnicianHours.query.filter(
        TechnicianHours.date_worked >= start_dt,
        TechnicianHours.date_worked < end_dt
    ).all()
    order_ids_with_hours = [hr.order_id for hr in hours_records if hr.order_id]

    # Obtener órdenes en el rango por (creación, actualización o asignación) o con horas en el periodo
    query = Order.query.filter(
        or_(
            and_(Order.created_at >= start_dt, Order.created_at < end_dt),
            and_(Order.updated_at >= start_dt, Order.updated_at < end_dt),
            and_(Order.technician_assigned_at >= start_dt, Order.technician_assigned_at < end_dt),
            Order.id.in_(order_ids_with_hours)
        )
    )
    
    # Filtrar por técnico si se especifica (por id o por nombre)
    if technician_filter:
        selected_tech = Technician.query.filter_by(full_name=technician_filter).first()
        if selected_tech:
            query = query.filter(or_(Order.technician_id == selected_tech.id, Order.technician == selected_tech.full_name))
        else:
            query = query.filter(Order.technician.like(f"%{technician_filter}%"))
    
    orders = query.all()
    
    # Organizar datos por técnico y día de la semana
    weekly_data = {}
    days_of_week = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    
    for technician in technicians:
        weekly_data[technician.id] = {
            'technician': technician,
            'days': {day: {'orders': [], 'total_hours': 0, 'status_counts': {}} for day in days_of_week},
            'total_orders': 0,
            'total_hours': 0,
            'status_summary': {}
        }
    
    # Procesar órdenes y asignar a días de la semana
    for order in orders:
        # Determinar el técnico (usar technician_id si existe, sino technician string)
        tech_id = None
        if order.technician_id:
            tech_id = order.technician_id
        else:
            # Buscar técnico por nombre si no hay technician_id
            tech = Technician.query.filter_by(full_name=order.technician).first()
            if tech:
                tech_id = tech.id
        
        if tech_id and tech_id in weekly_data:
            # Determinar la fecha de asignación al técnico
            # Usar technician_assigned_at si existe, sino usar updated_at si es más reciente que created_at
            if order.technician_assigned_at:
                assignment_date = order.technician_assigned_at
            elif order.updated_at > order.created_at:
                assignment_date = order.updated_at
            else:
                assignment_date = order.created_at
            
            # Solo mostrar la orden si la fecha de asignación está en el rango
            if start_dt <= assignment_date <= end_dt:
                day_name = days_of_week[assignment_date.weekday()]
                
                # Agregar orden al día correspondiente
                weekly_data[tech_id]['days'][day_name]['orders'].append(order)
                weekly_data[tech_id]['total_orders'] += 1
                
                # Contar estatus
                status = order.status
                if status not in weekly_data[tech_id]['days'][day_name]['status_counts']:
                    weekly_data[tech_id]['days'][day_name]['status_counts'][status] = 0
                weekly_data[tech_id]['days'][day_name]['status_counts'][status] += 1
                
                if status not in weekly_data[tech_id]['status_summary']:
                    weekly_data[tech_id]['status_summary'][status] = 0
                weekly_data[tech_id]['status_summary'][status] += 1
    
    # Calcular horas trabajadas por técnico (desde TechnicianHours) - reutiliza hours_records
    # Organizar horas por técnico usando technician_name
    tech_hours_by_name = {}
    for hour_record in hours_records:
        tech_name = hour_record.technician_name
        if tech_name not in tech_hours_by_name:
            tech_hours_by_name[tech_name] = []
        tech_hours_by_name[tech_name].append(hour_record)
    
    # Asignar horas a los técnicos en weekly_data
    for tech_id, data in weekly_data.items():
        technician = data['technician']
        tech_code = technician.code
        
        if tech_code in tech_hours_by_name:
            for hour_record in tech_hours_by_name[tech_code]:
                day_name = days_of_week[hour_record.date_worked.weekday()]
                data['days'][day_name]['total_hours'] += hour_record.hours_worked
                data['total_hours'] += hour_record.hours_worked
    
    # Obtener lista de técnicos para el filtro
    technician_names = [t.full_name for t in technicians]
    
    # Calcular resumen de horas por técnico
    # Incluir todos los técnicos que tienen horas registradas, incluso si no tienen órdenes
    hours_summary = []
    
    # Primero agregar técnicos con órdenes
    for tech_id, data in weekly_data.items():
        technician = data['technician']
        total_hours = data['total_hours']
        total_orders = data['total_orders']
        
        # Calcular promedio de horas por orden si hay órdenes
        avg_hours_per_order = total_hours / total_orders if total_orders > 0 else 0
        
        hours_summary.append({
            'technician': technician,
            'total_hours': total_hours,
            'total_orders': total_orders,
            'avg_hours_per_order': avg_hours_per_order
        })
    
    # Agregar técnicos que tienen horas pero no órdenes en el período
    for tech_code, hour_records in tech_hours_by_name.items():
        # Verificar si ya está en el resumen
        already_included = any(item['technician'].code == tech_code for item in hours_summary)
        
        if not already_included:
            # Buscar el técnico en la base de datos por código
            technician = Technician.query.filter_by(code=tech_code).first()
            if technician:
                total_hours = sum(record.hours_worked for record in hour_records)
                hours_summary.append({
                    'technician': technician,
                    'total_hours': total_hours,
                    'total_orders': 0,
                    'avg_hours_per_order': 0
                })
    
    # Ordenar por horas totales (descendente)
    hours_summary.sort(key=lambda x: x['total_hours'], reverse=True)
    
    # Resumen general de órdenes asignadas por técnico (independiente de la semana)
    technician_orders_summary = []
    
    # Obtener todos los técnicos activos
    all_technicians = Technician.query.filter_by(is_active=True).order_by(Technician.code).all()
    
    for technician in all_technicians:
        # Contar órdenes asignadas al técnico (todas, no solo del período)
        total_assigned_orders = Order.query.filter_by(technician_id=technician.id).count()
        
        # Contar órdenes por estado
        orders_by_status = {}
        status_counts = db.session.query(
            Order.status, 
            db.func.count(Order.id)
        ).filter_by(technician_id=technician.id).group_by(Order.status).all()
        
        for status, count in status_counts:
            orders_by_status[status] = count
        
        # Calcular estadísticas adicionales (buscar por código del técnico)
        total_hours_all_time = db.session.query(db.func.sum(TechnicianHours.hours_worked)).filter(
            TechnicianHours.technician_name == technician.code
        ).scalar() or 0
        
        # Órdenes más antiguas sin completar
        oldest_unfinished = Order.query.filter(
            Order.technician_id == technician.id,
            Order.status != "ENTREGADO"
        ).order_by(Order.created_at.asc()).first()
        
        oldest_days = 0
        if oldest_unfinished:
            oldest_days = (utcnow().date() - oldest_unfinished.created_at.date()).days
        
        technician_orders_summary.append({
            'technician': technician,
            'total_assigned_orders': total_assigned_orders,
            'orders_by_status': orders_by_status,
            'total_hours_all_time': total_hours_all_time,
            'oldest_unfinished_days': oldest_days,
            'oldest_unfinished_order': oldest_unfinished
        })
    
    # Ordenar por total de órdenes asignadas (descendente)
    technician_orders_summary.sort(key=lambda x: x['total_assigned_orders'], reverse=True)
    
    # Obtener estatus dinámicos
    status_choices = get_status_choices()
    
    # Obtener colores de estado desde la base de datos
    status_colors = get_status_colors()
    
    return render_template("technician_orders.html", 
                         weekly_data=weekly_data,
                         days_of_week=days_of_week,
                         start_date=start_date,
                         end_date=end_date,
                         selected_technician=technician_filter,
                         technicians=technician_names,
                         STATUS_CHOICES=status_choices,
                         status_colors=status_colors,
                         hours_summary=hours_summary,
                         technician_orders_summary=technician_orders_summary)

@app.route("/technicians/hours")
@login_required
def technician_hours():
    """Vista de horas trabajadas por técnicos"""
    technician = request.args.get("technician", "")
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    
    # Obtener lista de técnicos únicos
    technicians = db.session.query(TechnicianHours.technician_name).distinct().all()
    technicians = [t[0] for t in technicians]
    
    # Filtrar horas por técnico
    query = TechnicianHours.query
    if technician:
        query = query.filter(TechnicianHours.technician_name == technician)
    
    # Filtrar por mes si se especifica
    if month:
        year, month_num = month.split("-")
        start_date = datetime(int(year), int(month_num), 1)
        if int(month_num) == 12:
            end_date = datetime(int(year) + 1, 1, 1)
        else:
            end_date = datetime(int(year), int(month_num) + 1, 1)
        query = query.filter(TechnicianHours.date_worked >= start_date, TechnicianHours.date_worked < end_date)
    
    hours_records = query.order_by(TechnicianHours.date_worked.desc()).all()
    
    # Calcular estadísticas por técnico
    tech_hours_stats = {}
    for record in hours_records:
        tech = record.technician_name
        if tech not in tech_hours_stats:
            tech_hours_stats[tech] = {
                'total_hours': 0,
                'total_records': 0,
                'avg_hours_per_day': 0,
                'days_worked': set()
            }
        tech_hours_stats[tech]['total_hours'] += record.hours_worked
        tech_hours_stats[tech]['total_records'] += 1
        tech_hours_stats[tech]['days_worked'].add(record.date_worked.date())
    
    # Calcular promedios
    for tech in tech_hours_stats:
        days_count = len(tech_hours_stats[tech]['days_worked'])
        if days_count > 0:
            tech_hours_stats[tech]['avg_hours_per_day'] = tech_hours_stats[tech]['total_hours'] / days_count
        tech_hours_stats[tech]['days_worked'] = days_count
    
    return render_template("technician_hours.html", 
                         hours_records=hours_records,
                         technicians=technicians,
                         selected_technician=technician,
                         selected_month=month,
                         tech_hours_stats=tech_hours_stats)

@app.route("/technicians/hours/new", methods=["GET", "POST"])
@login_required
def new_technician_hours():
    """Registrar nuevas horas de técnico"""
    form = TechnicianHoursForm()
    
    # Poblar opciones de órdenes
    orders = Order.query.filter(Order.technician.isnot(None)).all()
    form.order_id.choices = [(0, "Sin orden específica")] + [(o.id, f"{o.order_number} - {o.plate}") for o in orders]
    
    if form.validate_on_submit():
        hours_record = TechnicianHours(
            technician_name=form.technician_name.data,
            order_id=form.order_id.data if form.order_id.data != 0 else None,
            date_worked=form.date_worked.data,
            hours_worked=form.hours_worked.data,
            description=form.description.data,
            created_by=current_user.full_name
        )
        db.session.add(hours_record)
        db.session.commit()
        
        flash("Horas registradas exitosamente", "success")
        return redirect(url_for("technician_hours"))
    
    return render_template("technician_hours_form.html", form=form)

# ---------- Rutas para Carga de Archivos Excel ----------
@app.route("/technicians/hours/upload", methods=["GET", "POST"])
@login_required
def upload_excel_hours():
    """Cargar archivo Excel de comisiones de mecánicos"""
    form = ExcelUploadForm()
    
    if form.validate_on_submit():
        try:
            file = form.file.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Procesar el archivo
                processed_data = parse_excel_file(file_path)
                
                if not processed_data:
                    flash("No se encontraron datos válidos en el archivo", "warning")
                    return render_template("upload_excel.html", form=form)
                
                # Guardar datos en la base de datos
                records_added = 0
                for data in processed_data:
                    # Buscar orden por número si existe
                    order_id = None
                    if data['order_number']:
                        order = Order.query.filter_by(order_number=data['order_number']).first()
                        if order:
                            order_id = order.id
                    
                    # Crear registro de horas
                    hours_record = TechnicianHours(
                        technician_id=data.get('technician_id'),
                        technician_name=data['technician_name'],
                        order_id=order_id,
                        date_worked=data['date_worked'],
                        hours_worked=data['hours_worked'],
                        description=data['description'],
                        created_by=current_user.full_name
                    )
                    db.session.add(hours_record)
                    records_added += 1
                
                db.session.commit()
                
                # Limpiar archivo temporal
                os.remove(file_path)
                
                flash(f"Archivo procesado exitosamente. Se agregaron {records_added} registros de horas.", "success")
                return redirect(url_for("technician_hours"))
            else:
                flash("Tipo de archivo no permitido", "error")
        except Exception as e:
            flash(f"Error procesando archivo: {str(e)}", "error")
    
    return render_template("upload_excel.html", form=form)

@app.route("/orders/upload", methods=["GET", "POST"])
@login_required
def upload_orders():
    """Cargar órdenes desde archivo Excel"""
    form = OrdersUploadForm()
    
    if form.validate_on_submit():
        try:
            file = form.file.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Procesar archivo
                processed_orders = parse_orders_file(file_path)
                
                if not processed_orders:
                    flash("No se encontraron órdenes válidas en el archivo", "warning")
                    return render_template("upload_orders.html", form=form)
                
                # Guardar en base de datos
                orders_added = 0
                orders_updated = 0
                
                for order_data in processed_orders:
                    # Verificar si la orden ya existe
                    existing_order = Order.query.filter_by(order_number=order_data['order_number']).first()
                    
                    if existing_order:
                        # Actualizar orden existente
                        existing_order.plate = order_data['plate']
                        existing_order.vin = order_data['vin']
                        existing_order.chasis = order_data['chasis']
                        existing_order.brand = order_data['brand']
                        existing_order.modelo = order_data.get('modelo', '')
                        existing_order.customer_name = order_data['customer_name']
                        existing_order.advisor = order_data['advisor']
                        existing_order.technician = order_data['technician']
                        existing_order.technician_id = order_data['technician_id']
                        existing_order.service_type = order_data['service_type']
                        existing_order.status = order_data['status']
                        existing_order.symptom = order_data['symptom']
                        existing_order.priority = order_data['priority']
                        existing_order.promised_date = order_data['promised_date']
                        existing_order.updated_at = utcnow()
                        orders_updated += 1
                    else:
                        # Crear nueva orden
                        new_order = Order(
                            order_number=order_data['order_number'],
                            plate=order_data['plate'],
                            vin=order_data['vin'],
                            chasis=order_data['chasis'],
                            brand=order_data['brand'],
                            modelo=order_data.get('modelo', ''),
                            customer_name=order_data['customer_name'],
                            advisor=order_data['advisor'],
                            technician=order_data['technician'],
                            technician_id=order_data['technician_id'],
                            service_type=order_data['service_type'],
                            status=order_data['status'],
                            symptom=order_data['symptom'],
                            priority=order_data['priority'],
                            promised_date=order_data['promised_date'],
                            created_at=order_data['reception_date']
                        )
                        db.session.add(new_order)
                        orders_added += 1
                
                db.session.commit()
                
                # Limpiar archivo temporal
                os.remove(file_path)
                
                flash(f'Se procesaron {len(processed_orders)} órdenes: {orders_added} nuevas, {orders_updated} actualizadas.', 'success')
                return redirect(url_for('list_orders'))
            else:
                flash('Tipo de archivo no permitido. Solo se aceptan archivos .xls y .xlsx', 'error')
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'error')
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
    
    return render_template("upload_orders.html", form=form)

@app.route("/technicians/hours/upload/sample")
@login_required
def download_sample_excel():
    """Descargar archivo de ejemplo para carga de datos"""
    # Crear un archivo de ejemplo
    sample_data = {
        'Mecánico': ['Juan Pérez', 'María García', 'Carlos López'],
        'No. Orden': ['ORD001', 'ORD002', 'ORD003'],
        'Recepción': ['01/10/25', '02/10/25', '03/10/25'],
        'Completado': ['01/10/25', '02/10/25', '03/10/25'],
        'Tiempo Real': ['8:00', '6:30', '4:15'],
        'Descripción': ['Reparación motor', 'Cambio de frenos', 'Revisión general']
    }
    
    df = pd.DataFrame(sample_data)
    sample_path = os.path.join(app.config['UPLOAD_FOLDER'], 'ejemplo_comisiones.xlsx')
    df.to_excel(sample_path, index=False)
    
    from flask import send_file
    return send_file(sample_path, as_attachment=True, download_name='ejemplo_comisiones.xlsx')

# ---------- Rutas para Gestión de Técnicos ----------
@app.route("/maintenance/technicians")
@login_required
def list_technicians():
    """Lista de técnicos"""
    search = request.args.get("search", "")
    specialty = request.args.get("specialty", "")
    status = request.args.get("status", "")
    
    query = Technician.query
    
    # Filtros
    if search:
        query = query.filter(
            db.or_(
                Technician.code.like(f"%{search}%"),
                Technician.full_name.like(f"%{search}%"),
                Technician.email.like(f"%{search}%")
            )
        )
    
    if specialty:
        query = query.filter(Technician.specialty == specialty)
    
    if status:
        is_active = status == "active"
        query = query.filter(Technician.is_active == is_active)
    
    technicians = query.order_by(Technician.code).all()
    
    # Obtener especialidades únicas para filtro
    specialties = db.session.query(Technician.specialty).filter(Technician.specialty.isnot(None)).distinct().all()
    specialties = [s[0] for s in specialties if s[0]]
    
    return render_template("technicians_list.html", 
                         technicians=technicians,
                         search=search,
                         selected_specialty=specialty,
                         selected_status=status,
                         specialties=specialties)

@app.route("/maintenance/technicians/new", methods=["GET", "POST"])
@login_required
def new_technician():
    """Crear nuevo técnico"""
    form = TechnicianForm()
    
    if form.validate_on_submit():
        # Verificar si el código ya existe
        existing_tech = Technician.query.filter_by(code=form.code.data).first()
        if existing_tech:
            flash("El código del técnico ya existe", "error")
            return render_template("technician_form.html", form=form, title="Nuevo Técnico")
        
        # Verificar si el email ya existe (si se proporciona)
        if form.email.data:
            existing_email = Technician.query.filter_by(email=form.email.data).first()
            if existing_email:
                flash("El email ya está registrado", "error")
                return render_template("technician_form.html", form=form, title="Nuevo Técnico")
        
        technician = Technician(
            code=form.code.data.upper(),
            full_name=form.full_name.data,
            email=form.email.data or None,
            phone=form.phone.data or None,
            specialty=form.specialty.data or None,
            hourly_rate=form.hourly_rate.data or 0.0,
            is_active=form.is_active.data,
            hire_date=form.hire_date.data,
            notes=form.notes.data or None
        )
        
        db.session.add(technician)
        db.session.commit()
        
        flash("Técnico creado exitosamente", "success")
        return redirect(url_for("list_technicians"))
    
    return render_template("technician_form.html", form=form, title="Nuevo Técnico")

@app.route("/maintenance/technicians/<int:technician_id>")
@login_required
def technician_detail(technician_id):
    """Detalle del técnico"""
    technician = Technician.query.get_or_404(technician_id)
    
    # Obtener estadísticas del técnico
    total_hours = db.session.query(db.func.sum(TechnicianHours.hours_worked)).filter(
        TechnicianHours.technician_id == technician_id
    ).scalar() or 0
    
    total_orders = Order.query.filter_by(technician_id=technician_id).count()
    
    # Obtener horas recientes
    recent_hours = TechnicianHours.query.filter_by(technician_id=technician_id).order_by(
        TechnicianHours.date_worked.desc()
    ).limit(10).all()
    
    # Obtener órdenes recientes
    recent_orders = Order.query.filter_by(technician_id=technician_id).order_by(
        Order.created_at.desc()
    ).limit(10).all()
    
    # Obtener colores de estado desde la base de datos
    status_colors = get_status_colors()
    
    return render_template("technician_detail.html", 
                         technician=technician,
                         total_hours=total_hours,
                         total_orders=total_orders,
                         recent_hours=recent_hours,
                         recent_orders=recent_orders,
                         status_colors=status_colors)

@app.route("/maintenance/technicians/<int:technician_id>/edit", methods=["GET", "POST"])
@login_required
def edit_technician(technician_id):
    """Editar técnico"""
    technician = Technician.query.get_or_404(technician_id)
    form = TechnicianForm(obj=technician)
    
    if form.validate_on_submit():
        # Verificar si el código ya existe (excluyendo el actual)
        existing_tech = Technician.query.filter(
            Technician.code == form.code.data.upper(),
            Technician.id != technician_id
        ).first()
        if existing_tech:
            flash("El código del técnico ya existe", "error")
            return render_template("technician_form.html", form=form, title="Editar Técnico", technician=technician)
        
        # Verificar si el email ya existe (excluyendo el actual)
        if form.email.data:
            existing_email = Technician.query.filter(
                Technician.email == form.email.data,
                Technician.id != technician_id
            ).first()
            if existing_email:
                flash("El email ya está registrado", "error")
                return render_template("technician_form.html", form=form, title="Editar Técnico", technician=technician)
        
        technician.code = form.code.data.upper()
        technician.full_name = form.full_name.data
        technician.email = form.email.data or None
        technician.phone = form.phone.data or None
        technician.specialty = form.specialty.data or None
        technician.hourly_rate = form.hourly_rate.data or 0.0
        technician.is_active = form.is_active.data
        technician.hire_date = form.hire_date.data
        technician.notes = form.notes.data or None
        
        db.session.commit()
        
        flash("Técnico actualizado exitosamente", "success")
        return redirect(url_for("technician_detail", technician_id=technician_id))
    
    return render_template("technician_form.html", form=form, title="Editar Técnico", technician=technician)

@app.route("/maintenance/technicians/<int:technician_id>/delete", methods=["POST"])
@login_required
def delete_technician(technician_id):
    """Eliminar técnico"""
    technician = Technician.query.get_or_404(technician_id)
    
    # Verificar si tiene órdenes o horas asociadas
    has_orders = Order.query.filter_by(technician_id=technician_id).count() > 0
    has_hours = TechnicianHours.query.filter_by(technician_id=technician_id).count() > 0
    
    if has_orders or has_hours:
        flash("No se puede eliminar el técnico porque tiene órdenes o horas registradas asociadas", "error")
        return redirect(url_for("technician_detail", technician_id=technician_id))
    
    db.session.delete(technician)
    db.session.commit()
    
    flash("Técnico eliminado exitosamente", "success")
    return redirect(url_for("list_technicians"))

@app.route("/maintenance/technicians/<int:technician_id>/toggle-status", methods=["POST"])
@login_required
def toggle_technician_status(technician_id):
    """Activar/desactivar técnico"""
    technician = Technician.query.get_or_404(technician_id)
    technician.is_active = not technician.is_active
    db.session.commit()
    
    status = "activado" if technician.is_active else "desactivado"
    flash(f"Técnico {status} exitosamente", "success")
    return redirect(url_for("technician_detail", technician_id=technician_id))

# ---------- Rutas para Gestión de Asesores ----------
@app.route("/maintenance/advisors")
@login_required
def list_advisors():
    """Lista de asesores"""
    search = request.args.get("search", "")
    department = request.args.get("department", "")
    status = request.args.get("status", "")
    
    query = Advisor.query
    
    # Filtros
    if search:
        query = query.filter(
            db.or_(
                Advisor.code.like(f"%{search}%"),
                Advisor.full_name.like(f"%{search}%"),
                Advisor.email.like(f"%{search}%")
            )
        )
    
    if department:
        query = query.filter(Advisor.department == department)
    
    if status:
        is_active = status == "active"
        query = query.filter(Advisor.is_active == is_active)
    
    advisors = query.order_by(Advisor.code).all()
    
    # Obtener departamentos únicos para filtro
    departments = db.session.query(Advisor.department).filter(Advisor.department.isnot(None)).distinct().all()
    departments = [d[0] for d in departments if d[0]]
    
    return render_template("advisors_list.html", 
                         advisors=advisors,
                         search=search,
                         selected_department=department,
                         selected_status=status,
                         departments=departments)

@app.route("/maintenance/advisors/new", methods=["GET", "POST"])
@login_required
def new_advisor():
    """Crear nuevo asesor"""
    form = AdvisorForm()
    
    # Cargar usuarios con rol ASESOR para el selector
    advisor_users = User.query.filter_by(role='ASESOR', is_active=True).all()
    form.user_id.choices = [('', 'No asociar usuario')] + [(u.id, f"{u.full_name} ({u.username})") for u in advisor_users]
    
    if form.validate_on_submit():
        # Verificar si el código ya existe
        existing_advisor = Advisor.query.filter_by(code=form.code.data).first()
        if existing_advisor:
            flash("El código del asesor ya existe", "error")
            return render_template("advisor_form.html", form=form, title="Nuevo Asesor", users=advisor_users)
        
        # Verificar si el email ya existe (si se proporciona)
        if form.email.data:
            existing_email = Advisor.query.filter_by(email=form.email.data).first()
            if existing_email:
                flash("El email ya está registrado", "error")
                return render_template("advisor_form.html", form=form, title="Nuevo Asesor", users=advisor_users)
        
        # Validar que el usuario seleccionado tenga rol ASESOR
        user_id = form.user_id.data  # Ya viene procesado por to_int_or_none
        if user_id:
            user = User.query.get(user_id)
            if user and user.role != 'ASESOR':
                flash("El usuario seleccionado debe tener rol ASESOR", "error")
                return render_template("advisor_form.html", form=form, title="Nuevo Asesor", users=advisor_users)
            
            # Verificar que el usuario no esté ya asociado a otro asesor
            existing_advisor_user = Advisor.query.filter_by(user_id=user_id).first()
            if existing_advisor_user:
                flash(f"El usuario ya está asociado al asesor {existing_advisor_user.code}", "error")
                return render_template("advisor_form.html", form=form, title="Nuevo Asesor", users=advisor_users)
        
        advisor = Advisor(
            code=form.code.data.upper(),
            full_name=form.full_name.data,
            email=form.email.data or None,
            phone=form.phone.data or None,
            department=form.department.data or None,
            commission_rate=form.commission_rate.data or 0.0,
            is_active=form.is_active.data,
            hire_date=form.hire_date.data,
            user_id=user_id,
            notes=form.notes.data or None
        )
        
        db.session.add(advisor)
        db.session.commit()
        
        flash("Asesor creado exitosamente", "success")
        return redirect(url_for("advisor_detail", advisor_id=advisor.id))
    
    return render_template("advisor_form.html", form=form, title="Nuevo Asesor", users=advisor_users)

@app.route("/maintenance/advisors/<int:advisor_id>")
@login_required
def advisor_detail(advisor_id):
    """Detalle del asesor"""
    advisor = Advisor.query.get_or_404(advisor_id)
    
    # Obtener órdenes asignadas
    orders = Order.query.filter_by(advisor_id=advisor_id).order_by(Order.created_at.desc()).limit(10).all()
    
    # Validar que las órdenes tengan advisor_id correcto
    for order in orders:
        if order.advisor_id != advisor_id:
            order.advisor_id = advisor_id
    if orders:
        db.session.commit()
    
    # Obtener colores de estado desde la base de datos
    status_colors = get_status_colors()
    
    return render_template("advisor_detail.html", advisor=advisor, orders=orders, status_colors=status_colors)

@app.route("/maintenance/advisors/<int:advisor_id>/edit", methods=["GET", "POST"])
@login_required
def edit_advisor(advisor_id):
    """Editar asesor"""
    advisor = Advisor.query.get_or_404(advisor_id)
    form = AdvisorForm(obj=advisor)
    
    # Cargar usuarios con rol ASESOR para el selector
    advisor_users = User.query.filter_by(role='ASESOR', is_active=True).all()
    form.user_id.choices = [('', 'No asociar usuario')] + [(u.id, f"{u.full_name} ({u.username})") for u in advisor_users]
    
    # Pre-cargar el user_id actual si existe
    if advisor.user_id:
        form.user_id.data = advisor.user_id
    
    if form.validate_on_submit():
        # Verificar si el código ya existe (excluyendo el actual)
        existing_advisor = Advisor.query.filter(
            Advisor.code == form.code.data.upper(),
            Advisor.id != advisor_id
        ).first()
        if existing_advisor:
            flash("El código del asesor ya existe", "error")
            return render_template("advisor_form.html", form=form, title="Editar Asesor", advisor=advisor, users=advisor_users)
        
        # Verificar si el email ya existe (excluyendo el actual)
        if form.email.data:
            existing_email = Advisor.query.filter(
                Advisor.email == form.email.data,
                Advisor.id != advisor_id
            ).first()
            if existing_email:
                flash("El email ya está registrado", "error")
                return render_template("advisor_form.html", form=form, title="Editar Asesor", advisor=advisor, users=advisor_users)
        
        # Validar que el usuario seleccionado tenga rol ASESOR
        user_id = form.user_id.data  # Ya viene procesado por to_int_or_none
        if user_id:
            user = User.query.get(user_id)
            if user and user.role != 'ASESOR':
                flash("El usuario seleccionado debe tener rol ASESOR", "error")
                return render_template("advisor_form.html", form=form, title="Editar Asesor", advisor=advisor, users=advisor_users)
            
            # Verificar que el usuario no esté ya asociado a otro asesor (excluyendo el actual)
            existing_advisor_user = Advisor.query.filter(
                Advisor.user_id == user_id,
                Advisor.id != advisor_id
            ).first()
            if existing_advisor_user:
                flash(f"El usuario ya está asociado al asesor {existing_advisor_user.code}", "error")
                return render_template("advisor_form.html", form=form, title="Editar Asesor", advisor=advisor, users=advisor_users)
        
        advisor.code = form.code.data.upper()
        advisor.full_name = form.full_name.data
        advisor.email = form.email.data or None
        advisor.phone = form.phone.data or None
        advisor.department = form.department.data or None
        advisor.commission_rate = form.commission_rate.data or 0.0
        advisor.is_active = form.is_active.data
        advisor.hire_date = form.hire_date.data
        advisor.user_id = user_id
        advisor.notes = form.notes.data or None
        
        db.session.commit()
        
        flash("Asesor actualizado exitosamente", "success")
        return redirect(url_for("advisor_detail", advisor_id=advisor_id))
    
    return render_template("advisor_form.html", form=form, title="Editar Asesor", advisor=advisor, users=advisor_users)

@app.route("/maintenance/advisors/<int:advisor_id>/delete", methods=["POST"])
@login_required
def delete_advisor(advisor_id):
    """Eliminar asesor"""
    advisor = Advisor.query.get_or_404(advisor_id)
    
    # Verificar si tiene órdenes asociadas
    has_orders = Order.query.filter_by(advisor_id=advisor_id).count() > 0
    
    if has_orders:
        flash("No se puede eliminar el asesor porque tiene órdenes asociadas", "error")
        return redirect(url_for("advisor_detail", advisor_id=advisor_id))
    
    db.session.delete(advisor)
    db.session.commit()
    
    flash("Asesor eliminado exitosamente", "success")
    return redirect(url_for("list_advisors"))

@app.route("/maintenance/advisors/<int:advisor_id>/toggle-status", methods=["POST"])
@login_required
def toggle_advisor_status(advisor_id):
    """Activar/desactivar asesor"""
    advisor = Advisor.query.get_or_404(advisor_id)
    advisor.is_active = not advisor.is_active
    db.session.commit()
    
    status = "activado" if advisor.is_active else "desactivado"
    flash(f"Asesor {status} exitosamente", "success")
    return redirect(url_for("advisor_detail", advisor_id=advisor_id))

# ---------- Rutas para Notificaciones ----------
@app.route("/notifications")
@login_required
def notifications():
    """Vista de notificaciones del usuario"""
    notifications_list = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(50).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    return render_template("notifications.html", 
                         notifications=notifications_list,
                         unread_count=unread_count)

@app.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    """Marcar notificación como leída"""
    notification = Notification.query.get_or_404(notification_id)
    
    # Verificar que la notificación pertenece al usuario actual
    if notification.user_id != current_user.id:
        return jsonify({"ok": False, "error": "No autorizado"}), 403
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({"ok": True})

@app.route("/notifications/mark-all-read", methods=["POST"])
@login_required
def mark_all_notifications_read():
    """Marcar todas las notificaciones como leídas"""
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    
    return jsonify({"ok": True})

@app.route("/notifications/count")
@login_required
def notifications_count():
    """Obtener contador de notificaciones no leídas"""
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({"count": count})

# ---------- Rutas para Recordatorios de Contacto ----------
@app.route("/check-contact-reminders")
@login_required
def check_contact_reminders_endpoint():
    """Endpoint para verificar y crear recordatorios de contacto (puede ser llamado por cron)"""
    if not is_admin_or_manager(current_user):
        return jsonify({"ok": False, "error": "No autorizado"}), 403
    
    reminders_created = check_contact_reminders()
    return jsonify({"ok": True, "reminders_created": reminders_created})

@app.route("/orders/<int:order_id>/register-contact", methods=["POST"])
@login_required
def register_contact(order_id):
    """Registrar contacto con cliente"""
    order = Order.query.get_or_404(order_id)
    
    # Verificar que el usuario es el asesor de la orden
    if order.advisor_id:
        advisor = Advisor.query.get(order.advisor_id)
        if advisor:
            # Usar el enlace directo user_id si existe, sino buscar por email o nombre
            user = None
            if advisor.user_id:
                user = User.query.get(advisor.user_id)
            else:
                # Fallback: buscar por email o nombre
                user = User.query.filter(
                    (User.email == advisor.email) | (User.full_name == advisor.full_name)
                ).first()
            
            if user and user.id != current_user.id:
                return jsonify({"ok": False, "error": "No autorizado"}), 403
    
    data = request.json if request.is_json else request.form
    contact_type = data.get("contact_type", "CALL")
    notes = data.get("notes", "")
    
    # Crear o actualizar registro de contacto
    contact = AdvisorContact.query.filter_by(
        order_id=order.id,
        advisor_id=order.advisor_id
    ).order_by(AdvisorContact.contact_date.desc()).first()
    
    if contact:
        # Actualizar contacto existente
        contact.contact_date = utcnow()
        contact.contact_type = contact_type
        contact.notes = notes
        contact.next_reminder_date = utcnow() + timedelta(hours=24)
    else:
        # Crear nuevo contacto
        contact = AdvisorContact(
            order_id=order.id,
            advisor_id=order.advisor_id,
            contact_date=utcnow(),
            contact_type=contact_type,
            notes=notes,
            next_reminder_date=utcnow() + timedelta(hours=24)
        )
        db.session.add(contact)
    
    db.session.commit()
    
    return jsonify({"ok": True, "message": "Contacto registrado correctamente"})

# ---------- Rutas para Gestión de Usuarios (Solo Admin) ----------
@app.route("/maintenance/users")
@admin_required
def list_users():
    """Listar todos los usuarios del sistema"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("users_list.html", users=users)

@app.route("/maintenance/users/new", methods=["GET", "POST"])
@admin_required
def new_user():
    """Crear nuevo usuario"""
    form = UserForm()
    
    if form.validate_on_submit():
        # Verificar si el usuario ya existe
        if User.query.filter_by(username=form.username.data).first():
            flash('El nombre de usuario ya existe', 'error')
            return render_template("user_form.html", form=form, title="Nuevo Usuario")
        
        if User.query.filter_by(email=form.email.data).first():
            flash('El email ya está registrado', 'error')
            return render_template("user_form.html", form=form, title="Nuevo Usuario")
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            role=form.role.data,
            is_active=form.is_active.data
        )
        
        # Solo establecer contraseña si se proporciona
        if form.password.data:
            user.set_password(form.password.data)
        else:
            flash('La contraseña es requerida para nuevos usuarios', 'error')
            return render_template("user_form.html", form=form, title="Nuevo Usuario")
        
        db.session.add(user)
        db.session.commit()
        
        flash('Usuario creado exitosamente.', 'success')
        return redirect(url_for('list_users'))
    
    return render_template("user_form.html", form=form, title="Nuevo Usuario")

@app.route("/maintenance/users/<int:user_id>")
@admin_required
def user_detail(user_id):
    """Detalle del usuario"""
    user = User.query.get_or_404(user_id)
    
    # Obtener estadísticas del usuario
    notifications_count = Notification.query.filter_by(user_id=user_id).count()
    unread_notifications = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    
    return render_template("user_detail.html", 
                         user=user,
                         notifications_count=notifications_count,
                         unread_notifications=unread_notifications)

@app.route("/maintenance/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    """Editar usuario existente"""
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    
    # Prevenir que el admin se desactive a sí mismo
    if user_id == current_user.id and request.method == "POST":
        if not form.is_active.data:
            flash('No puedes desactivar tu propia cuenta', 'error')
            form.is_active.data = True
    
    if form.validate_on_submit():
        # Verificar si el username o email ya existen en otro usuario
        existing_user = User.query.filter(User.username == form.username.data, User.id != user_id).first()
        if existing_user:
            flash('El nombre de usuario ya está en uso por otro usuario', 'error')
            return render_template("user_form.html", form=form, user=user, title="Editar Usuario")
        
        existing_email = User.query.filter(User.email == form.email.data, User.id != user_id).first()
        if existing_email:
            flash('El email ya está en uso por otro usuario', 'error')
            return render_template("user_form.html", form=form, user=user, title="Editar Usuario")
        
        user.username = form.username.data
        user.email = form.email.data
        user.full_name = form.full_name.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        
        # Solo actualizar contraseña si se proporciona una nueva
        if form.password.data:
            user.set_password(form.password.data)
        
        db.session.commit()
        
        flash('Usuario actualizado exitosamente.', 'success')
        return redirect(url_for('user_detail', user_id=user_id))
    
    # Pre-cargar datos del usuario en el formulario
    form.username.data = user.username
    form.email.data = user.email
    form.full_name.data = user.full_name
    form.role.data = user.role
    form.is_active.data = user.is_active
    
    return render_template("user_form.html", form=form, user=user, title="Editar Usuario")

@app.route("/maintenance/users/<int:user_id>/toggle-status", methods=["POST"])
@admin_required
def toggle_user_status(user_id):
    """Activar/desactivar usuario"""
    user = User.query.get_or_404(user_id)
    
    # Prevenir que el admin se desactive a sí mismo
    if user_id == current_user.id:
        flash('No puedes desactivar tu propia cuenta', 'error')
        return redirect(url_for('user_detail', user_id=user_id))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = "activado" if user.is_active else "desactivado"
    flash(f'Usuario {status} exitosamente', 'success')
    return redirect(url_for('user_detail', user_id=user_id))

@app.route("/maintenance/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    """Eliminar usuario"""
    user = User.query.get_or_404(user_id)
    
    # Prevenir que el admin se elimine a sí mismo
    if user_id == current_user.id:
        flash('No puedes eliminar tu propia cuenta', 'error')
        return redirect(url_for('user_detail', user_id=user_id))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Usuario {username} eliminado exitosamente.', 'success')
    return redirect(url_for('list_users'))

# ---------- Rutas para Validación y Corrección de Enlaces ----------
@app.route("/maintenance/validate-advisor-links")
@admin_required
def validate_advisor_links():
    """Validar y corregir enlaces de advisor_id en órdenes"""
    issues_found = []
    issues_fixed = []
    
    # Obtener todas las órdenes
    orders = Order.query.all()
    
    for order in orders:
        # Verificar si tiene advisor_id pero el advisor no existe
        if order.advisor_id:
            advisor = Advisor.query.get(order.advisor_id)
            if not advisor:
                issues_found.append({
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'issue': f'advisor_id {order.advisor_id} no existe',
                    'current_advisor_name': order.advisor
                })
                
                # Intentar encontrar el asesor por nombre
                if order.advisor:
                    matching_advisor = Advisor.query.filter_by(full_name=order.advisor).first()
                    if matching_advisor:
                        order.advisor_id = matching_advisor.id
                        issues_fixed.append({
                            'order_id': order.id,
                            'order_number': order.order_number,
                            'action': f'Enlazado con asesor {matching_advisor.code} por nombre'
                        })
                    else:
                        # Si no se encuentra, limpiar el advisor_id
                        order.advisor_id = None
                        issues_fixed.append({
                            'order_id': order.id,
                            'order_number': order.order_number,
                            'action': 'advisor_id limpiado (asesor no encontrado)'
                        })
        
        # Verificar si tiene advisor (string) pero no advisor_id
        elif order.advisor:
            matching_advisor = Advisor.query.filter_by(full_name=order.advisor).first()
            if matching_advisor:
                order.advisor_id = matching_advisor.id
                issues_fixed.append({
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'action': f'Enlazado con asesor {matching_advisor.code} por nombre'
                })
    
    if issues_fixed:
        db.session.commit()
    
    return render_template("validate_advisor_links.html",
                         issues_found=issues_found,
                         issues_fixed=issues_fixed)

# Agregar función 'now' al contexto global de Jinja2
@app.template_global()
def now():
    """Función para obtener la fecha y hora actual en templates"""
    return utcnow()

# Manejo de errores para producción
@app.errorhandler(500)
def internal_error(error):
    """Manejo de errores internos del servidor"""
    try:
        db.session.rollback()
    except:
        pass  # Si hay error en la sesión, continuar
    
    import traceback
    error_trace = traceback.format_exc()
    print(f"Error 500: {error}")
    print(f"Traceback: {error_trace}")
    
    # Intentar renderizar el template, si falla usar respuesta simple
    try:
        # Mostrar traceback solo en desarrollo
        show_traceback = os.environ.get('FLASK_ENV') != 'production' or os.environ.get('FLASK_DEBUG') == '1'
        # Preparar variables de forma segura
        error_str = str(error) if error else "Error desconocido"
        message_str = "Error interno del servidor"
        traceback_str = error_trace if show_traceback else None
        
        # Intentar renderizar con contexto mínimo
        try:
            return render_template('error.html', 
                                 error=error_str, 
                                 traceback=traceback_str, 
                                 message=message_str), 500
        except Exception as render_error:
            # Si el render falla, puede ser por contexto corrupto, intentar con contexto limpio
            print(f"Error en render_template: {render_error}")
            import traceback as tb
            print(f"Traceback del render_error: {tb.format_exc()}")
            # Crear un contexto mínimo
            from flask import has_request_context
            if not has_request_context():
                # Si no hay contexto de request, crear uno mínimo
                try:
                    with app.test_request_context('/'):
                        return render_template('error.html', 
                                             error=error_str, 
                                             traceback=traceback_str, 
                                             message=message_str), 500
                except Exception as context_error:
                    print(f"Error con contexto de test: {context_error}")
                    raise render_error
            else:
                raise render_error
    except Exception as template_error:
        print(f"Error renderizando template de error: {template_error}")
        print(f"Error original: {error}")
        import traceback as tb
        print(f"Traceback del error de template: {tb.format_exc()}")
        # Fallback: respuesta HTML simple sin depender de templates ni contexto de Flask
        html_response = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error 500 - AutoSVC</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            padding: 20px;
        }}
        .error-container {{
            max-width: 600px;
            width: 100%;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .error-header {{
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .error-body {{
            padding: 30px;
        }}
        h1 {{ color: #dc3545; margin: 0 0 20px 0; }}
        .error-box {{
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .btn {{
            display: inline-block;
            padding: 10px 20px;
            background: #0d6efd;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 20px;
        }}
        .btn:hover {{
            background: #0b5ed7;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-header">
            <h1>⚠️ Error 500</h1>
            <p style="margin: 0;">Error Interno del Servidor</p>
        </div>
        <div class="error-body">
            <div class="error-box">
                <p><strong>Ha ocurrido un error en el servidor.</strong></p>
                <p>Por favor, contacta al administrador del sistema.</p>
                <p><strong>Error:</strong> {str(error)}</p>
            </div>
            <a href="/" class="btn">Volver al inicio</a>
        </div>
    </div>
</body>
</html>"""
        return html_response, 500, {'Content-Type': 'text/html; charset=utf-8'}

@app.errorhandler(404)
def not_found_error(error):
    """Manejo de errores 404"""
    try:
        return render_template('error.html', error=str(error), message="Página no encontrada"), 404
    except Exception as template_error:
        print(f"Error renderizando template de error: {template_error}")
        # Fallback: respuesta HTML simple sin depender de templates
        html_response = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error 404</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
        h1 {{ color: #ffc107; }}
        .error-box {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Error 404 - Página no encontrada</h1>
    <div class="error-box">
        <p>La página que buscas no existe.</p>
    </div>
    <p><a href="/">Volver al inicio</a></p>
</body>
</html>"""
        return html_response, 404, {'Content-Type': 'text/html; charset=utf-8'}

# Inicializar base de datos (solo para desarrollo)
# En producción, ejecutar: flask db upgrade
with app.app_context():
    try:
        # Solo crear tablas en desarrollo si no están en producción
        if os.environ.get('FLASK_ENV') != 'production' and not os.environ.get('DATABASE_URL'):
            db.create_all()
            print("✅ Tablas de base de datos inicializadas")
    except Exception as e:
        print(f"⚠️ Warning: No se pudieron crear las tablas automáticamente: {e}")
        print("💡 En producción, ejecuta: flask db upgrade")

if __name__ == "__main__":
    # Allow debug during development
    app.secret_key = os.environ.get("SECRET_KEY", "devkey")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
