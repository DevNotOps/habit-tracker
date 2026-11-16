import os

import click
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.engine import make_url

db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    database_url = os.environ.get("DATABASE_URL")
    secret_key = os.environ.get("SECRET_KEY")

    if not test_config and not database_url:
        raise RuntimeError("DATABASE_URL must be set.")
    if not test_config and not secret_key:
        raise RuntimeError("SECRET_KEY must be set.")

    if database_url:
        parsed_url = make_url(database_url)
        if parsed_url.drivername == "postgres":
            database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif parsed_url.drivername == "postgresql":
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    app.config.from_mapping(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "pool_recycle": 300},
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
        SMTP_HOST=os.environ.get("SMTP_HOST"),
        SMTP_PORT=int(os.environ.get("SMTP_PORT", "587")),
        SMTP_USER=os.environ.get("SMTP_USER"),
        SMTP_PASSWORD=os.environ.get("SMTP_PASSWORD"),
        SMTP_FROM=os.environ.get("SMTP_FROM") or os.environ.get("SMTP_USER"),
        SMTP_USE_TLS=os.environ.get("SMTP_USE_TLS", "true").lower() == "true",
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    from app.auth import auth_bp
    from app.habits import habits_bp
    from app.models import User

    app.register_blueprint(auth_bp)
    app.register_blueprint(habits_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables."""
        with app.app_context():
            db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("send-reminders")
    def send_reminders_command():
        """Send habit reminders to users with unfinished goals."""
        from app.services.email import send_due_reminders

        with app.app_context():
            sent, failures = send_due_reminders()
        click.echo(f"Reminder emails sent: {sent}; failures: {failures}.")
        if failures:
            raise click.ClickException("One or more reminder emails could not be sent.")

    return app
