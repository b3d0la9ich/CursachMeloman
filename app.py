import os
import csv
from pathlib import Path
from random import randint

from uuid import uuid4
from pathlib import Path
from flask_wtf.file import FileField, FileAllowed
from wtforms import TextAreaField
from models import db, User, Track, Catalog, seed_catalog, Playlist, PlaylistTrack

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import (
    LoginManager, login_user, current_user, login_required, logout_user
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from flask_migrate import Migrate
from sqlalchemy import func, tuple_

from models import db, User, Track, Catalog, seed_catalog


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # --- Конфиг ---
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "secretkey")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://melouser:melopass@localhost:5432/meloman"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB
    app.config["PLAYLIST_COVERS_REL"] = "uploads/playlists"  # относит. путь внутри /static
    # гарантируем, что папка для обложек существует
    (Path(app.root_path) / "static" / app.config["PLAYLIST_COVERS_REL"]).mkdir(parents=True, exist_ok=True)

    # --- Инициализация ---
    db.init_app(app)

    with app.app_context():
        db.create_all()

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

    class PlaylistForm(FlaskForm):
        title = StringField("Название", validators=[DataRequired(), Length(min=1, max=255)])
        description = TextAreaField("Описание", validators=[Length(max=2000)])
        cover = FileField("Обложка", validators=[FileAllowed(["png","jpg","jpeg","webp","gif"], "Только изображения!")])
        submit = SubmitField("Создать")

    def _save_cover(file_storage):
        if not file_storage or not getattr(file_storage, "filename", ""):
            return None
        ext = Path(file_storage.filename).suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            flash("Недопустимый формат обложки", "warning")
            return None
        name = f"{uuid4().hex}{ext}"
        rel_dir = Path(app.config["PLAYLIST_COVERS_REL"])             # uploads/playlists
        abs_dir = Path(app.root_path) / "static" / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=True)
        (abs_dir / name).save(file_storage) if hasattr(Path, "save") else file_storage.save(abs_dir / name)
        return str(rel_dir / name).replace("\\", "/")                 # например: uploads/playlists/abc.jpg


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
    
        # --- Плейлисты: список/создание ---
    @app.route("/playlists", methods=["GET", "POST"])
    @login_required
    def playlists():
        form = PlaylistForm()
        if form.validate_on_submit():
            cover_rel = _save_cover(form.cover.data)
            pl = Playlist(
                user_id=current_user.id,
                title=form.title.data.strip(),
                description=(form.description.data or "").strip() or None,
                cover=cover_rel
            )
            db.session.add(pl)
            db.session.commit()
            flash("Плейлист создан", "success")
            return redirect(url_for("playlists"))
        pls = (db.session.query(Playlist)
               .filter_by(user_id=current_user.id)
               .order_by(Playlist.created_at.desc())
               .all())
        # количество треков для карточек
        counts = {pl.id: db.session.query(PlaylistTrack).filter_by(playlist_id=pl.id).count() for pl in pls}
        return render_template("playlists.html", form=form, playlists=pls, counts=counts)

    # --- Детали плейлиста и управление треками ---
    @app.route("/playlists/<int:pl_id>")
    @login_required
    def playlist_detail(pl_id: int):
        pl = (db.session.query(Playlist)
              .filter_by(id=pl_id, user_id=current_user.id)
              .first_or_404())
        # треки в плейлисте
        items = (db.session.query(PlaylistTrack)
                 .filter_by(playlist_id=pl.id)
                 .join(Track, PlaylistTrack.track_id == Track.id)
                 .order_by(Track.artist.asc(), Track.title.asc())
                 .all())
        in_ids = {it.track_id for it in items}
        # можно добавить только свои треки, которых нет в плейлисте
        candidates = (db.session.query(Track)
                      .filter(Track.user_id == current_user.id)
                      .filter(~Track.id.in_(in_ids) if in_ids else True)
                      .order_by(Track.artist.asc(), Track.title.asc())
                      .all())
        details_by_track = {}
        if items:
            pairs = [(it.track.title.lower().strip(), it.track.artist.lower().strip()) for it in items]
            cat_rows = (db.session.query(Catalog)
                        .filter(tuple_(func.lower(Catalog.title), func.lower(Catalog.artist)).in_(pairs))
                        .all())
            cat_map = {(c.title.lower().strip(), c.artist.lower().strip()): c for c in cat_rows}
            for it in items:
                key = (it.track.title.lower().strip(), it.track.artist.lower().strip())
                details_by_track[it.track_id] = cat_map.get(key)

        return render_template(
            "playlist_detail.html",
            pl=pl, items=items, candidates=candidates,
            details_by_track=details_by_track  # передаём в шаблон
        )

    @app.post("/playlists/<int:pl_id>/add")
    @login_required
    def playlist_add_track(pl_id: int):
        pl = (db.session.query(Playlist)
              .filter_by(id=pl_id, user_id=current_user.id)
              .first_or_404())
        track_id = request.form.get("track_id", type=int)
        if not track_id:
            flash("Не выбран трек", "warning")
            return redirect(url_for("playlist_detail", pl_id=pl.id))
        track = (db.session.query(Track)
                 .filter_by(id=track_id, user_id=current_user.id)
                 .first())
        if not track:
            flash("Нельзя добавить этот трек", "danger")
            return redirect(url_for("playlist_detail", pl_id=pl.id))
        exists = db.session.query(PlaylistTrack).filter_by(playlist_id=pl.id, track_id=track.id).first()
        if exists:
            flash("Трек уже в плейлисте", "info")
            return redirect(url_for("playlist_detail", pl_id=pl.id))
        db.session.add(PlaylistTrack(playlist_id=pl.id, track_id=track.id))
        db.session.commit()
        flash("Трек добавлен в плейлист", "success")
        return redirect(url_for("playlist_detail", pl_id=pl.id))

    @app.post("/playlists/<int:pl_id>/remove/<int:track_id>")
    @login_required
    def playlist_remove_track(pl_id: int, track_id: int):
        pl = (db.session.query(Playlist)
              .filter_by(id=pl_id, user_id=current_user.id)
              .first_or_404())
        pt = db.session.query(PlaylistTrack).filter_by(playlist_id=pl.id, track_id=track_id).first()
        if pt:
            db.session.delete(pt)
            db.session.commit()
            flash("Трек удалён из плейлиста", "info")
        return redirect(url_for("playlist_detail", pl_id=pl.id))

    @app.post("/playlists/<int:pl_id>/delete")
    @login_required
    def playlist_delete(pl_id: int):
        pl = (db.session.query(Playlist)
              .filter_by(id=pl_id, user_id=current_user.id)
              .first_or_404())
        # по желанию можно удалить файл обложки
        try:
            if pl.cover:
                abs_path = Path(app.root_path) / "static" / pl.cover
                if abs_path.exists():
                    abs_path.unlink(missing_ok=True)
        except Exception:
            pass
        db.session.delete(pl)
        db.session.commit()
        flash("Плейлист удалён", "info")
        return redirect(url_for("playlists"))


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

        # фильтр по исполнителю 
        artist_q = request.args.get("artist", "", type=str).strip()
        q = db.session.query(Track).filter(Track.user_id == current_user.id)
        if artist_q:
            q = q.filter(func.lower(Track.artist).contains(artist_q.lower()))
        tracks = q.order_by(Track.artist.asc(), Track.title.asc()).all()

        details_by_track = {}
        if tracks:
            pairs = [(t.title.lower().strip(), t.artist.lower().strip()) for t in tracks]
            cat_rows = (
                db.session.query(Catalog)
                .filter(
                    tuple_(func.lower(Catalog.title), func.lower(Catalog.artist)).in_(pairs)
                ).all()
            )
            cat_map = { (c.title.lower().strip(), c.artist.lower().strip()): c for c in cat_rows }
            for t in tracks:
                details_by_track[t.id] = cat_map.get((t.title.lower().strip(), t.artist.lower().strip()))

        return render_template(
            "songs.html",
            form=form, tracks=tracks, artist_filter=artist_q,
            details_by_track=details_by_track  
        )

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
        print("Каталог наполнен демо-данными.")

    @app.cli.command("load-catalog")
    def load_catalog_cmd():
        """Импорт каталога из data/catalog.csv.
        Формат: title,artist[,year[,album[,lyrics_or_path]]]
        5-я колонка: либо текст песни, либо относительный путь к файлу
        в data/lyrics (например: "Imagine Dragons - Radioactive.txt").
        """
        csv_path = Path("data/catalog.csv")
        if not csv_path.exists():
            print("Файл data/catalog.csv не найден")
            return

        def to_int_safe(x):
            try: return int(str(x).strip())
            except: return None

        def read_lyrics_from_path(val: str | None, artist: str, title: str) -> str | None:
            """Если val похоже на имя файла — читаем его; иначе пытаемся автофайл '<artist> - <title>.txt'."""
            base_dir = Path("data/lyrics")
            # явный путь в CSV
            if val:
                p = Path(val)
                if not p.is_absolute():
                    p = base_dir / p
                if p.exists() and p.is_file():
                    try:
                        return p.read_text(encoding="utf-8")
                    except Exception:
                        return None
                # если строка не путь/файл — трактуем как прямой текст
                if val.strip() and not any(val.lower().endswith(ext) for ext in (".txt", ".md", ".lrc")):
                    return val
            # авто-поиск по шаблону
            auto = base_dir / f"{artist} - {title}.txt"
            if auto.exists():
                try:
                    return auto.read_text(encoding="utf-8")
                except Exception:
                    return None
            return None

        added = updated = skipped = 0

        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)

            # пытаемся распознать заголовок
            first_row = next(reader, None)
            if first_row is None:
                print("Пустой CSV")
                return

            has_header = (
                len(first_row) >= 2 and
                first_row[0].strip().lower() in ("title", "название", "трек") and
                first_row[1].strip().lower() in ("artist", "исполнитель")
            )
            rows_iter = reader if has_header else [first_row] + list(reader)

            for row in rows_iter:
                if not row or all(not (c or "").strip() for c in row):
                    continue

                title  = (row[0] or "").strip()
                artist = (row[1] or "").strip()
                year   = to_int_safe(row[2]) if len(row) >= 3 and row[2] else None
                album  = (row[3] or "").strip() if len(row) >= 4 else None
                lyr_raw = (row[4] or "").strip() if len(row) >= 5 else ""

                if not title or not artist:
                    continue

                # читаем текст (из файла/строки/автофайла)
                lyrics = read_lyrics_from_path(lyr_raw, artist, title)
                if lyrics:
                    lyrics = lyrics[:50000]  # безопасный лимит

                existing = (
                    db.session.query(Catalog)
                    .filter(func.lower(Catalog.title) == title.lower(),
                            func.lower(Catalog.artist) == artist.lower())
                    .first()
                )

                if existing:
                    changed = False
                    if year and not existing.year:
                        existing.year = year; changed = True
                    if album and not (existing.album or "").strip():
                        existing.album = album; changed = True
                    if lyrics and not (existing.lyrics or "").strip():
                        existing.lyrics = lyrics; changed = True
                    if changed: updated += 1
                    else: skipped += 1
                else:
                    db.session.add(Catalog(
                        title=title, artist=artist, year=year,
                        album=(album or None),
                        lyrics=(lyrics or None)
                    ))
                    added += 1

            db.session.commit()

        print(f"✅ Импорт завершён. Добавлено: {added}, обновлено: {updated}, пропущено: {skipped}")

    return app    

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

