from models import db, User
from flask import Flask

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:4780@localhost/millionaire_db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    # Проверяем, есть ли админ в базе
    admin = User.query.filter_by(username="admin").first()
    
    if not admin:
        new_admin = User(username="admin", is_admin=True)
        new_admin.set_password("admin123")  # Пароль: admin123
        db.session.add(new_admin)
        db.session.commit()
        print("✅ Админ создан! Логин: admin, Пароль: admin123")
    else:
        print("⚠️ Админ уже существует.")
