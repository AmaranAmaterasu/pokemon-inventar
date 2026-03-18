import secrets
from datetime import datetime, timedelta

from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Set(db.Model):
    __tablename__ = "sets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    series = db.Column(db.String(120))
    release_year = db.Column(db.Integer)

    cards = db.relationship(
        "Card",
        backref="set",                # dann kannst du c.set benutzen
        cascade="all, delete-orphan", # Cards werden mitgelöscht
        passive_deletes=True
    )


class Card(db.Model):
    __tablename__ = "cards"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    number = db.Column(db.String(20), nullable=False)  # z.B. 12/102
    rarity = db.Column(db.String(50))

    set_id = db.Column(
    db.Integer,
    db.ForeignKey("sets.id", ondelete="CASCADE", name="fk_cards_set_id_sets"),
    nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint("set_id", "number", name="unique_card_in_set"),
    )


class Collection(db.Model):
    __tablename__ = "collections"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    card_id = db.Column(db.Integer, db.ForeignKey("cards.id"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "card_id", name="unique_user_card"),
    )


class ApiToken(db.Model):
    __tablename__ = "api_tokens"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    @staticmethod
    def generate(user_id: int, days_valid: int = 30):
        tok = secrets.token_urlsafe(32)
        return ApiToken(
            token=tok,
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(days=days_valid),
        )