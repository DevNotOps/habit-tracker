import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("habits.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        errors = []
        if len(email) > 254 or not _EMAIL_RE.match(email):
            errors.append("Enter a valid email address.")
        if not 12 <= len(password) <= 128:
            errors.append("Use a password between 12 and 128 characters.")
        if User.query.filter(func.lower(User.email) == email).first():
            errors.append("An account with that email already exists.")
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("auth/register.html"), 400

        user = User()
        user.email = email
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if User.query.filter(func.lower(User.email) == email).first():
                flash("An account with that email already exists.", "error")
                return render_template("auth/register.html"), 400
            raise
        login_user(user)
        flash("Your account is ready. Start with one small habit.", "success")
        return redirect(url_for("habits.dashboard"))
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("habits.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter(func.lower(User.email) == email).first()
        if user is None or not user.check_password(password):
            flash("Email or password is incorrect.", "error")
            return render_template("auth/login.html"), 401
        login_user(user, remember=False, fresh=True)
        return redirect(url_for("habits.dashboard"))
    return render_template("auth/login.html")


@auth_bp.post("/logout")
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
