from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os

app = Flask(__name__)
CORS(app)

# JWT
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # желательно через переменные окружения
jwt = JWTManager(app)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# 🔹 Проверка соединения
@app.route("/api/hello", methods=["GET"])
def hello():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 'Меломан подключен к БД!'")
        msg = cur.fetchone()[0]
        cur.close()
        conn.close()
        return jsonify({"message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Регистрация
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email и пароль обязательны"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            return jsonify({"message": "Пользователь уже существует"}), 409

        password_hash = generate_password_hash(password)
        cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (email, password_hash))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Регистрация успешна"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Вход
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE email = %s", (email,))
        row = cur.fetchone()

        if not row or not check_password_hash(row[0], password):
            return jsonify({"message": "Неверные учетные данные"}), 401

        access_token = create_access_token(identity=email)
        return jsonify({"token": access_token}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=3000, host="0.0.0.0")
