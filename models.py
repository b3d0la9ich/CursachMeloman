from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import func

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    tracks = db.relationship("Track", backref="owner", cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Track(db.Model):
    __tablename__ = "tracks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=False, index=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("title", "artist", "user_id", name="uq_user_track"),
    )


class Catalog(db.Model):
    __tablename__ = "catalog"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    artist = db.Column(db.String(255), nullable=False, index=True)

    year = db.Column(db.Integer)              # год выпуска
    album = db.Column(db.String(255))         # альбом
    lyrics = db.Column(db.Text)               # текст песни

    __table_args__ = (db.UniqueConstraint("title", "artist", name="uq_catalog"),)

                         
def seed_catalog(db_session):
    """Наполнение каталога тестовыми треками (однократно)."""
    if db_session.query(Catalog).count() > 0:
        return
    sample = [
        ("Blinding Lights", "The Weeknd"),
        ("bad guy", "Billie Eilish"),
        ("Smells Like Teen Spirit", "Nirvana"),
        ("Lose Yourself", "Eminem"),
        ("Shape of You", "Ed Sheeran"),
        ("Seven Nation Army", "The White Stripes"),
        ("Believer", "Imagine Dragons"),
        ("Take On Me", "a-ha"),
        ("Yellow", "Coldplay"),
        ("Zombie", "The Cranberries"),
        ("Radioactive", "Imagine Dragons"),
        ("Numb", "Linkin Park"),
        ("Nothing Else Matters", "Metallica"),
    ]
    db_session.bulk_save_objects([Catalog(title=t, artist=a) for t, a in sample])
    db_session.commit()

class Playlist(db.Model):
    __tablename__ = "playlists"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    cover = db.Column(db.String(512), nullable=True)  # относительный путь внутри /static, например: uploads/playlists/xxx.jpg
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)

    owner = db.relationship("User", backref=db.backref("playlists", cascade="all, delete-orphan", lazy="dynamic"))

    def __repr__(self):
        return f"<Playlist {self.id}:{self.title!r}>"


class PlaylistTrack(db.Model):
    __tablename__ = "playlist_tracks"
    playlist_id = db.Column(db.Integer, db.ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True)
    track_id = db.Column(db.Integer, db.ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True)
    added_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)

    playlist = db.relationship("Playlist", backref=db.backref("items", cascade="all, delete-orphan", lazy="dynamic"))
    track = db.relationship("Track")

    def __repr__(self):
        return f"<PlaylistTrack pl={self.playlist_id} track={self.track_id}>"
