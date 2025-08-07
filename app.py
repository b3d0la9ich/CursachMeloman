from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import string
import os
from extensions import db
from models import User, Order
from sqlalchemy.exc import OperationalError
from sqlalchemy import text

# Конфигурация
app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:4780@db/music_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Константы
ADMIN_CODE = 'admin123'

# Страницы
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        admin_code = request.form.get('admin_code', '').strip()

        if not username or not password:
            flash('⚠️ Поля не могут быть пустыми.')
            return redirect(url_for('register'))

        if len(username) < 3 or len(username) > 20:
            flash('⚠️ Имя пользователя должно быть от 3 до 20 символов.')
            return redirect(url_for('register'))

        if len(password) < 6 or len(password) > 30:
            flash('⚠️ Пароль должен быть от 6 до 30 символов.')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('⚠️ Пользователь с таким именем уже существует.')
            return redirect(url_for('register'))

        is_admin = (admin_code == ADMIN_CODE)

        if admin_code and not is_admin:
            flash('🚫 Неверный код администратора.')
            return redirect(url_for('register'))

        user = User(username=username, password=generate_password_hash(password), is_admin=is_admin)
        db.session.add(user)
        db.session.commit()

        flash('✅ Регистрация прошла успешно. Войдите в аккаунт.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            return redirect(url_for('dashboard'))
        flash('❌ Неверное имя пользователя или пароль.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('✅ Вы вышли из аккаунта.')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('⚠️ Войдите для доступа.')
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    return render_template('dashboard.html', username=user.username, user=user)

@app.route('/admin_panel')
def admin_panel():
    if 'user_id' not in session:
        flash('⚠️ Войдите для доступа.')
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    if not user.is_admin:
        flash('🚫 Недостаточно прав.')
        return redirect(url_for('dashboard'))

    orders = Order.query.all()
    return render_template('admin_panel.html', orders=orders)

# Автоочистка базы данных при старте
if __name__ == '__main__':
    with app.app_context():
        try:
            print("⏳ Очистка базы...")
            db.session.execute(text('DROP SCHEMA public CASCADE;'))
            db.session.execute(text('CREATE SCHEMA public;'))
            db.session.commit()
            print("✅ База данных очищена.")

            print("⏳ Создание новых таблиц...")
            db.create_all()
            print("✅ Таблицы созданы.")
        except OperationalError:
            print("❌ Ошибка подключения к базе.")

    app.run(debug=True, port=5000, host='0.0.0.0')
