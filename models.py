from extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    order_id = db.relationship('Order', backref='user', lazy=True)
    is_admin = db.Column(db.Boolean, default = False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tracking_number = db.Column(db.String(20), unique=True, nullable=False)
    order_type = db.Column(db.String(20), nullable=False)
    weight = db.Column(db.String(10), nullable=True)
    transport = db.Column(db.String(10), nullable=False)
    urgency = db.Column(db.String(10), nullable=False)
    origin = db.Column(db.String(50), nullable=False)
    destination = db.Column(db.String(50), nullable=False)
    distance = db.Column(db.Float, nullable=False)
    delivery_time = db.Column(db.Float, nullable=False)
    remaining_time = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='Принят в обработку')
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 🛠 Новое поле: Время создания заказа

