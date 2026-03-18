from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import func
import re

from app.main import bp
from app.extensions import db
from app.models import Set, Card, Collection


def admin_required():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


def card_sort_key(card):
    text = (card.number or "").strip()
    match = re.match(r"(\d+)", text)
    if match:
        return int(match.group(1))
    return 9999


@bp.route("/")
@login_required
def index():
    sets = Set.query.order_by(Set.name.asc()).all()

    overview = []

    for s in sets:
        total = db.session.query(func.count(Card.id))\
            .filter(Card.set_id == s.id)\
            .scalar()

        owned = db.session.query(func.count(Collection.id))\
            .join(Card, Collection.card_id == Card.id)\
            .filter(
                Collection.user_id == current_user.id,
                Card.set_id == s.id
            )\
            .scalar()

        percent = round((owned / total) * 100, 1) if total else 0.0

        overview.append({
            "set": s,
            "owned": owned,
            "total": total,
            "percent": percent
        })

    total_cards_all = sum(row["total"] for row in overview)
    owned_cards_all = sum(row["owned"] for row in overview)
    percent_all = round((owned_cards_all / total_cards_all) * 100, 1) if total_cards_all else 0.0

    sets_total = len(overview)
    sets_complete = sum(
        1 for row in overview if row["total"] > 0 and row["owned"] == row["total"]
    )

    return render_template(
        "index.html",
        overview=overview,
        total_cards_all=total_cards_all,
        owned_cards_all=owned_cards_all,
        percent_all=percent_all,
        sets_total=sets_total,
        sets_complete=sets_complete
    )


# =========================
# ADMIN: SETS VERWALTEN
# =========================
@bp.route("/admin/sets", methods=["GET", "POST"])
@login_required
def manage_sets():
    if not current_user.is_admin:
        flash("Kein Zugriff.")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        name = request.form["name"].strip()
        series = request.form.get("series", "").strip()
        year_raw = request.form.get("year", "").strip()

        year = int(year_raw) if year_raw else None

        if Set.query.filter_by(name=name).first():
            flash("Dieses Set existiert bereits.")
            return redirect(url_for("main.manage_sets"))

        new_set = Set(
            name=name,
            series=series or None,
            release_year=year
        )

        db.session.add(new_set)
        db.session.commit()

        flash("Set erstellt.")
        return redirect(url_for("main.manage_sets"))

    sets = Set.query.order_by(Set.name.asc()).all()
    return render_template("manage_sets.html", sets=sets)


# =========================
# ADMIN: SET BEARBEITEN / LÖSCHEN
# =========================
@bp.route("/admin/sets/<int:set_id>/edit", methods=["GET", "POST"])
@login_required
def admin_edit_set(set_id):
    admin_required()
    s = Set.query.get_or_404(set_id)

    if request.method == "POST":
        name = request.form["name"].strip()
        series = request.form.get("series", "").strip()
        year_raw = request.form.get("year", "").strip()
        year = int(year_raw) if year_raw else None

        existing = Set.query.filter(Set.name == name, Set.id != s.id).first()
        if existing:
            flash("Dieses Set existiert bereits.", "warning")
            return redirect(url_for("main.admin_edit_set", set_id=s.id))

        if not name:
            flash("Name darf nicht leer sein.", "warning")
            return redirect(url_for("main.admin_edit_set", set_id=s.id))

        s.name = name
        s.series = series or None
        s.release_year = year

        db.session.commit()
        flash("Set gespeichert.", "success")
        return redirect(url_for("main.manage_sets"))

    return render_template("edit_set.html", s=s)


@bp.route("/admin/sets/<int:set_id>/delete", methods=["POST"])
@login_required
def admin_delete_set(set_id):
    admin_required()
    s = Set.query.get_or_404(set_id)

    db.session.delete(s)
    db.session.commit()

    flash("Set gelöscht.", "success")
    return redirect(url_for("main.manage_sets"))


# =========================
# ADMIN: CARDS VERWALTEN
# =========================
@bp.route("/admin/sets/<int:set_id>/cards", methods=["GET", "POST"])
@login_required
def manage_cards(set_id):
    if not current_user.is_admin:
        flash("Kein Zugriff.")
        return redirect(url_for("main.index"))

    selected_set = Set.query.get_or_404(set_id)

    if request.method == "POST":
        name = request.form["name"].strip()
        number = request.form["number"].strip()
        rarity = request.form.get("rarity", "").strip()

        if Card.query.filter_by(set_id=set_id, number=number).first():
            flash("Diese Kartennummer existiert bereits im Set.")
            return redirect(url_for("main.manage_cards", set_id=set_id))

        card = Card(
            name=name,
            number=number,
            rarity=rarity or None,
            set_id=set_id
        )

        db.session.add(card)
        db.session.commit()

        flash("Karte hinzugefügt.")
        return redirect(url_for("main.manage_cards", set_id=set_id))

    cards = Card.query.filter_by(set_id=set_id).all()
    cards = sorted(cards, key=card_sort_key)

    return render_template("manage_cards.html", selected_set=selected_set, cards=cards)


# =========================
# ADMIN: CARD BEARBEITEN / LÖSCHEN
# =========================
@bp.route("/admin/cards/<int:card_id>/edit", methods=["GET", "POST"])
@login_required
def admin_edit_card(card_id):
    admin_required()
    c = Card.query.get_or_404(card_id)

    if request.method == "POST":
        name = request.form["name"].strip()
        number = request.form["number"].strip()
        rarity = request.form.get("rarity", "").strip()

        if not name or not number:
            flash("Name und Nummer dürfen nicht leer sein.", "warning")
            return redirect(url_for("main.admin_edit_card", card_id=c.id))

        existing = Card.query.filter(
            Card.set_id == c.set_id,
            Card.number == number,
            Card.id != c.id
        ).first()
        if existing:
            flash("Diese Kartennummer existiert bereits im Set.", "warning")
            return redirect(url_for("main.admin_edit_card", card_id=c.id))

        c.name = name
        c.number = number
        c.rarity = rarity or None

        db.session.commit()
        flash("Karte gespeichert.", "success")
        return redirect(url_for("main.manage_cards", set_id=c.set_id))

    return render_template("edit_card.html", c=c)


@bp.route("/admin/cards/<int:card_id>/delete", methods=["POST"])
@login_required
def admin_delete_card(card_id):
    admin_required()
    c = Card.query.get_or_404(card_id)
    set_id = c.set_id

    db.session.delete(c)
    db.session.commit()

    flash("Karte gelöscht.", "success")
    return redirect(url_for("main.manage_cards", set_id=set_id))


# =========================
# USER: SET ANSEHEN + BESITZ TOGGLEN
# =========================
@bp.route("/sets/<int:set_id>", methods=["GET", "POST"])
@login_required
def view_set(set_id):
    selected_set = Set.query.get_or_404(set_id)

    if request.method == "POST":
        card_id = int(request.form["card_id"])

        existing = Collection.query.filter_by(
            user_id=current_user.id,
            card_id=card_id
        ).first()

        if existing:
            db.session.delete(existing)
        else:
            db.session.add(Collection(user_id=current_user.id, card_id=card_id))

        db.session.commit()
        return redirect(url_for("main.view_set", set_id=set_id))

    cards = Card.query.filter_by(set_id=set_id).all()
    cards = sorted(cards, key=card_sort_key)

    owned_cards = {
        c.card_id
        for c in Collection.query.filter_by(user_id=current_user.id).all()
    }

    total_cards = len(cards)
    owned_count = sum(1 for card in cards if card.id in owned_cards)
    progress_percent = round((owned_count / total_cards) * 100, 1) if total_cards > 0 else 0.0
    missing_cards = [card for card in cards if card.id not in owned_cards]
    missing_cards = sorted(missing_cards, key=card_sort_key)

    return render_template(
        "view_set.html",
        selected_set=selected_set,
        cards=cards,
        owned_cards=owned_cards,
        total_cards=total_cards,
        owned_count=owned_count,
        progress_percent=progress_percent,
        missing_cards=missing_cards
    )