from datetime import datetime
from functools import wraps

from flask import jsonify, request
from sqlalchemy import func

from app.api import bp
from app.extensions import db
from app.models import User, Set, Card, Collection, ApiToken


def require_api_token(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify(error="Missing Bearer token"), 401

        token_value = auth.replace("Bearer ", "", 1).strip()

        token = ApiToken.query.filter_by(token=token_value).first()
        if token is None:
            return jsonify(error="Invalid token"), 401

        if token.expires_at < datetime.utcnow():
            return jsonify(error="Token expired"), 401

        kwargs["api_user_id"] = token.user_id
        return fn(*args, **kwargs)

    return wrapper


@bp.route("/health")
def health():
    return jsonify(status="ok")


@bp.route("/token", methods=["POST"])
def create_token():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify(error="username and password required"), 400

    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return jsonify(error="invalid credentials"), 401

    token = ApiToken.generate(user_id=user.id, days_valid=30)
    db.session.add(token)
    db.session.commit()

    return jsonify(
        token=token.token,
        token_type="Bearer",
        expires_at=token.expires_at.isoformat() + "Z",
    )


@bp.route("/sets", methods=["GET"])
@require_api_token
def api_sets(api_user_id):
    sets = Set.query.order_by(Set.name.asc()).all()
    return jsonify([
        {"id": s.id, "name": s.name, "series": s.series, "release_year": s.release_year}
        for s in sets
    ])


@bp.route("/sets/<int:set_id>/progress", methods=["GET"])
@require_api_token
def api_set_progress(set_id, api_user_id):

    total = (
        db.session.query(func.count(Card.id))
        .filter(Card.set_id == set_id)
        .scalar()
    )

    owned = (
        db.session.query(func.count(Collection.id))
        .join(Card, Collection.card_id == Card.id)
        .filter(
            Collection.user_id == api_user_id,
            Card.set_id == set_id
        )
        .scalar()
    )

    percent = round((owned / total) * 100, 1) if total else 0.0

    return jsonify(set_id=set_id, owned=owned, total=total, percent=percent)


@bp.route("/sets/<int:set_id>/missing", methods=["GET"])
@require_api_token
def api_set_missing(set_id, api_user_id):
    cards = Card.query.filter_by(set_id=set_id).order_by(Card.number.asc()).all()

    owned_ids = {
        c.card_id
        for c in Collection.query.join(Card, Collection.card_id == Card.id)
        .filter(Collection.user_id == api_user_id, Card.set_id == set_id)
        .all()
    }

    missing = [
        {"id": c.id, "number": c.number, "name": c.name, "rarity": c.rarity}
        for c in cards
        if c.id not in owned_ids
    ]

    return jsonify(set_id=set_id, missing=missing, missing_count=len(missing))