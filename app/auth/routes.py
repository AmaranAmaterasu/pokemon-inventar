from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from app.auth import bp
from app.extensions import db
from app.models import User


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            flash("Username bereits vergeben")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("Email bereits registriert")
            return redirect(url_for("auth.register"))

        user = User(username=username, email=email)

        # erster registrierter User wird Admin
        if User.query.count() == 0:
            user.is_admin = True

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Registrierung erfolgreich. Bitte einloggen.")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("Ungültige Login-Daten")
            return redirect(url_for("auth.login"))

        login_user(user)
        return redirect(url_for("main.index"))

    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))