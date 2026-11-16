from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    habits = db.relationship("Habit", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Habit(db.Model):
    __table_args__ = (
        db.CheckConstraint("frequency IN ('daily', 'weekly')", name="ck_habit_frequency"),
        db.CheckConstraint("target_goal BETWEEN 1 AND 7", name="ck_habit_target_goal"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500), nullable=False, default="")
    frequency = db.Column(db.String(10), nullable=False, default="daily")
    target_goal = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    user = db.relationship("User", back_populates="habits")
    logs = db.relationship("HabitLog", back_populates="habit", cascade="all, delete-orphan")


class HabitLog(db.Model):
    __table_args__ = (
        db.UniqueConstraint("habit_id", "logged_on", name="uq_habit_log_date"),
        db.Index("ix_habit_log_habit_date_completed", "habit_id", "logged_on", "completed"),
    )

    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey("habit.id", ondelete="CASCADE"), nullable=False)
    logged_on = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    habit = db.relationship("Habit", back_populates="logs")


class HabitNote(db.Model):
    __table_args__ = (
        db.UniqueConstraint("habit_id", "note_date", name="uq_habit_note_date"),
        db.Index("ix_habit_note_habit_date", "habit_id", "note_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey("habit.id", ondelete="CASCADE"), nullable=False)
    note_date = db.Column(db.Date, nullable=False)
    body = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    habit = db.relationship("Habit", backref=db.backref("notes", cascade="all, delete-orphan"))
