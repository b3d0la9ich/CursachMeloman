import os
import csv
from pathlib import Path
from random import randint

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import (
    LoginManager, login_user, current_user, login_required, logout_user
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from flask_migrate import Migrate
from sqlalchemy import func

from models import db, User, Track, Catalog, seed_catalog


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # --- Конфиг ---
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://melouser:melopass@localhost:5432/meloman"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # --- Инициализация ---
    db.init_app(app)
    Migrate(app, db)

    login_manager = LoginManager(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- Формы ---
    class RegisterForm(FlaskForm):
        email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
        password = PasswordField("Пароль", validators=[DataRequired(), Length(min=6, max=64)])
        password2 = PasswordField("Повторите пароль", validators=[DataRequired(), EqualTo("password")])
        submit = SubmitField("Зарегистрироваться")

    class LoginForm(FlaskForm):
        email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
        password = PasswordField("Пароль", validators=[DataRequired(), Length(min=6, max=64)])
        submit = SubmitField("Войти")

    class TrackForm(FlaskForm):
        title = StringField("Название трека", validators=[DataRequired(), Length(min=1, max=255)])
        artist = StringField("Исполнитель", validators=[DataRequired(), Length(min=1, max=255)])
        submit = SubmitField("Добавить")

    # --- Роуты страниц ---
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        form = RegisterForm()
        if form.validate_on_submit():
            email = form.email.data.lower().strip()
            if db.session.query(User).filter_by(email=email).first():
                flash("Пользователь с таким email уже зарегистрирован", "warning")
                return render_template("register.html", form=form)

            user = User(email=email)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()

            login_user(user)
            flash("Регистрация выполнена", "success")
            return redirect(url_for("dashboard"))
        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        form = LoginForm()
        if form.validate_on_submit():
            email = form.email.data.lower().strip()
            user = db.session.query(User).filter_by(email=email).first()
            if not user or not user.check_password(form.password.data):
                flash("Неверный email или пароль", "danger")
                return render_template("login.html", form=form)

            login_user(user)
            flash("Вы вошли в аккаунт", "success")
            return redirect(url_for("dashboard"))
        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Вы вышли из аккаунта", "info")
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        return render_template("dashboard.html")

    # ---- Список песен ----
    @app.route("/songs", methods=["GET", "POST"])
    @login_required
    def songs():
        form = TrackForm()
        if form.validate_on_submit():
            title = form.title.data.strip()
            artist = form.artist.data.strip()

            # Если есть точное совпадение в каталоге — нормализуем регистр/пробелы
            c = (
                db.session.query(Catalog)
                .filter(
                    func.lower(Catalog.title) == title.lower(),
                    func.lower(Catalog.artist) == artist.lower(),
                )
                .first()
            )
            if c:
                title, artist = c.title, c.artist

            track = Track(title=title, artist=artist, owner=current_user)
            try:
                db.session.add(track)
                db.session.commit()
                flash("Трек добавлен", "success")
                return redirect(url_for("songs"))
            except Exception:
                db.session.rollback()
                flash("Такой трек уже есть в вашем списке", "warning")

        # фильтр по исполнителю (?artist=...)
        artist_q = request.args.get("artist", "", type=str).strip()
        q = db.session.query(Track).filter(Track.user_id == current_user.id)
        if artist_q:
            q = q.filter(func.lower(Track.artist).contains(artist_q.lower()))
        tracks = q.order_by(Track.artist.asc(), Track.title.asc()).all()

        return render_template("songs.html", form=form, tracks=tracks, artist_filter=artist_q)

    @app.post("/songs/<int:track_id>/delete")
    @login_required
    def delete_song(track_id: int):
        track = (
            db.session.query(Track)
            .filter_by(id=track_id, user_id=current_user.id)
            .first_or_404()
        )
        db.session.delete(track)
        db.session.commit()
        flash("Трек удалён", "info")
        return redirect(url_for("songs"))

    # ---- Доверюсь удаче ----
    @app.route("/lucky")
    @login_required
    def lucky():
        user_pairs = (
            db.session.query(Track.title, Track.artist)
            .filter_by(user_id=current_user.id)
            .all()
        )
        owned = {(t, a) for t, a in user_pairs}

        candidates = db.session.query(Catalog).all()
        candidates = [c for c in candidates if (c.title, c.artist) not in owned]

        picked = candidates[randint(0, len(candidates) - 1)] if candidates else None
        return render_template("lucky.html", picked=picked)

    @app.post("/lucky/add/<int:catalog_id>")
    @login_required
    def lucky_add(catalog_id: int):
        c = db.session.get(Catalog, catalog_id)
        if not c:
            flash("Трек не найден в каталоге", "warning")
            return redirect(url_for("lucky"))
        try:
            db.session.add(Track(title=c.title, artist=c.artist, owner=current_user))
            db.session.commit()
            flash("Трек добавлен в ваш список", "success")
        except Exception:
            db.session.rollback()
            flash("Этот трек уже есть у вас", "info")
        return redirect(url_for("songs"))

    # --- API для автодополнения ---
    @app.get("/api/suggest/artists")
    @login_required
    def suggest_artists():
        q = (request.args.get("q") or "").strip()
        if not q:
            return jsonify([])
        rows = (
            db.session.query(Catalog.artist)
            .filter(func.lower(Catalog.artist).contains(q.lower()))
            .distinct()
            .order_by(Catalog.artist.asc())
            .limit(10)
            .all()
        )
        return jsonify([r[0] for r in rows])

    @app.get("/api/suggest/tracks")
    @login_required
    def suggest_tracks():
        q = (request.args.get("q") or "").strip()
        artist = (request.args.get("artist") or "").strip()
        if not q:
            return jsonify([])
        query = db.session.query(Catalog.title).filter(
            func.lower(Catalog.title).contains(q.lower())
        )
        if artist:
            query = query.filter(func.lower(Catalog.artist) == artist.lower())
        rows = query.distinct().order_by(Catalog.title.asc()).limit(10).all()
        return jsonify([r[0] for r in rows])

    # --- CLI: демо-сид и импорт большого каталога ---
    @app.cli.command("seed-catalog")
    def seed_catalog_cmd():
        """Добавить демо-набор треков в Catalog (если пусто)."""
        seed_catalog(db.session)
        print("🎵 Каталог наполнен демо-данными.")

    @app.cli.command("load-catalog")
    def load_catalog_cmd():
        """Импорт каталога из data/catalog.csv (формат: title,artist; без заголовка)."""
        csv_path = Path("data/catalog.csv")
        if not csv_path.exists():
            print("❌ Файл data/catalog.csv не найден")
            return
        added = 0
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                title = (row[0] or "").strip()
                artist = (row[1] or "").strip()
                if not title or not artist:
                    continue
                exists = (
                    db.session.query(Catalog.id)
                    .filter(
                        func.lower(Catalog.title) == title.lower(),
                        func.lower(Catalog.artist) == artist.lower(),
                    )
                    .first()
                )
                if exists:
                    continue
                db.session.add(Catalog(title=title, artist=artist))
                added += 1
            db.session.commit()
        print(f"✅ Импорт завершён. Добавлено: {added}")

    return app


app = create_app()

if __name__ == "__main__":
    # Локальный запуск без gunicorn
    app.run(host="0.0.0.0", port=5000, debug=True)
