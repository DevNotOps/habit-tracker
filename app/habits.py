from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.models import Habit, HabitLog, HabitNote
from app.streaks import calculate_streaks

habits_bp = Blueprint("habits", __name__)


def _owned_habit(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
    if habit is None:
        abort(404)
    return habit


def _habit_form_values():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    frequency = request.form.get("frequency", "daily")
    try:
        goal = int(request.form.get("target_goal", "1"))
    except ValueError:
        goal = 0
    errors = []
    if not title or len(title) > 120:
        errors.append("Habit title must be between 1 and 120 characters.")
    if len(description) > 500:
        errors.append("Description must be 500 characters or fewer.")
    if frequency not in {"daily", "weekly"}:
        errors.append("Choose a daily or weekly frequency.")
    if frequency == "daily":
        goal = 1
    elif not 1 <= goal <= 7:
        errors.append("A weekly goal must be between 1 and 7 check-ins.")
    return title, description, frequency, goal, errors


@habits_bp.get("/")
@login_required
def dashboard():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    seven_day_start = today - timedelta(days=6)
    habits = Habit.query.filter_by(user_id=current_user.id).order_by(Habit.created_at.desc()).all()
    logs = HabitLog.query.join(Habit).filter(
        Habit.user_id == current_user.id,
        HabitLog.completed.is_(True),
    ).all()
    logs_by_habit = {}
    for log in logs:
        logs_by_habit.setdefault(log.habit_id, []).append(log.logged_on)
    today_notes = {
        note.habit_id: note
        for note in HabitNote.query.join(Habit).filter(
            Habit.user_id == current_user.id,
            HabitNote.note_date == today,
        ).all()
    }
    note_counts = dict(
        db.session.query(HabitNote.habit_id, func.count(HabitNote.id))
        .join(Habit)
        .filter(Habit.user_id == current_user.id)
        .group_by(HabitNote.habit_id)
        .all()
    )
    cards = []
    weekly_checkins = 0
    weekly_target = 0
    for habit in habits:
        completed_dates = logs_by_habit.get(habit.id, [])
        completed_dates_set = set(completed_dates)
        completed_this_week = [
            day for day in completed_dates if week_start <= day <= today
        ]
        completed_last_seven = sum(day >= seven_day_start for day in completed_dates)
        weekly_checkins += completed_last_seven
        weekly_target += 7 if habit.frequency == "daily" else habit.target_goal
        if habit.frequency == "daily":
            status_count = int(today in completed_dates)
            status_goal = 1
        else:
            status_count = len(completed_this_week)
            status_goal = habit.target_goal
        current_streak, longest_streak = calculate_streaks(habit, completed_dates, today)
        cards.append({
            "habit": habit,
            "done_today": today in completed_dates,
            "status_count": status_count,
            "status_goal": status_goal,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "week_days": [
                {
                    "date": day,
                    "completed": day in completed_dates_set,
                    "is_today": day == today,
                }
                for day in (today - timedelta(days=offset) for offset in range(6, -1, -1))
            ],
            "completed_last_seven": completed_last_seven,
            "today_note": today_notes.get(habit.id),
            "note_count": note_counts.get(habit.id, 0),
        })
    completion_percent = round(100 * min(weekly_checkins, weekly_target) / weekly_target) if weekly_target else 0
    total_checkins = sum(len(dates) for dates in logs_by_habit.values())
    return render_template(
        "habits/dashboard.html",
        cards=cards,
        today=today,
        completion_percent=completion_percent,
        weekly_checkins=weekly_checkins,
        total_checkins=total_checkins,
    )


@habits_bp.route("/habits/new", methods=["GET", "POST"])
@login_required
def create_habit():
    if request.method == "POST":
        title, description, frequency, goal, errors = _habit_form_values()
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("habits/form.html", habit=None), 400
        db.session.add(Habit(
            user_id=current_user.id,
            title=title,
            description=description,
            frequency=frequency,
            target_goal=goal,
        ))
        db.session.commit()
        flash("Habit created.", "success")
        return redirect(url_for("habits.dashboard"))
    return render_template("habits/form.html", habit=None)


@habits_bp.route("/habits/<int:habit_id>/edit", methods=["GET", "POST"])
@login_required
def edit_habit(habit_id):
    habit = _owned_habit(habit_id)
    if request.method == "POST":
        title, description, frequency, goal, errors = _habit_form_values()
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("habits/form.html", habit=habit), 400
        habit.title = title
        habit.description = description
        habit.frequency = frequency
        habit.target_goal = goal
        db.session.commit()
        flash("Habit updated.", "success")
        return redirect(url_for("habits.dashboard"))
    return render_template("habits/form.html", habit=habit)


@habits_bp.post("/habits/<int:habit_id>/delete")
@login_required
def delete_habit(habit_id):
    habit = _owned_habit(habit_id)
    db.session.delete(habit)
    db.session.commit()
    flash("Habit deleted.", "info")
    return redirect(url_for("habits.dashboard"))


@habits_bp.post("/habits/<int:habit_id>/check-in")
@login_required
def check_in(habit_id):
    habit = _owned_habit(habit_id)
    today = date.today()
    log = HabitLog.query.filter_by(habit_id=habit.id, logged_on=today).first()
    if log is None:
        log = HabitLog(habit_id=habit.id, logged_on=today, completed=True)
        db.session.add(log)
    else:
        log.completed = not log.completed
    db.session.commit()
    flash("Check-in updated.", "success")
    return redirect(url_for("habits.dashboard"))


@habits_bp.get("/habits/<int:habit_id>/notes")
@login_required
def habit_notes(habit_id):
    habit = _owned_habit(habit_id)
    notes = HabitNote.query.filter_by(habit_id=habit.id).order_by(
        HabitNote.note_date.desc(),
        HabitNote.updated_at.desc(),
    ).paginate(page=request.args.get("page", 1, type=int), per_page=20, error_out=False)
    return render_template("habits/notes.html", habit=habit, notes=notes)


@habits_bp.post("/habits/<int:habit_id>/notes")
@login_required
def save_habit_note(habit_id):
    habit = _owned_habit(habit_id)
    note_date_value = request.form.get("note_date", date.today().isoformat())
    try:
        note_date = datetime.strptime(note_date_value, "%Y-%m-%d").date()
    except ValueError:
        abort(400, description="Choose a valid note date.")
    if note_date > date.today():
        abort(400, description="Notes cannot be dated in the future.")

    note = HabitNote.query.filter_by(habit_id=habit.id, note_date=note_date).first()
    if request.form.get("delete") and note is not None:
        db.session.delete(note)
        db.session.commit()
        flash("Note deleted.", "info")
    else:
        body = request.form.get("body", "").strip()
        if len(body) > 2000:
            flash("Notes must be 2,000 characters or fewer.", "error")
            return redirect(url_for("habits.habit_notes", habit_id=habit.id))
        if not body:
            if note is not None:
                db.session.delete(note)
                db.session.commit()
                flash("Note deleted.", "info")
            else:
                flash("Write a note before saving.", "error")
        else:
            if note is None:
                note = HabitNote(habit_id=habit.id, note_date=note_date, body=body)
                db.session.add(note)
            else:
                note.body = body
            db.session.commit()
            flash("Note saved.", "success")

    if request.form.get("return_to") == "journal":
        return redirect(url_for("habits.habit_notes", habit_id=habit.id))
    return redirect(url_for("habits.dashboard", _anchor=f"habit-{habit.id}"))
