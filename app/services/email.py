import html
import smtplib
from datetime import date, timedelta
from email.message import EmailMessage

from flask import current_app

from app.models import Habit, HabitLog, User
from app.streaks import calculate_streaks


def _unfinished_habits(user, today):
    week_start = today - timedelta(days=today.weekday())
    due = []
    for habit in Habit.query.filter_by(user_id=user.id).order_by(Habit.title).all():
        completed_dates = [
            row.logged_on
            for row in HabitLog.query.filter_by(habit_id=habit.id, completed=True).all()
        ]
        current_streak, longest_streak = calculate_streaks(habit, completed_dates, today)
        streak_unit = "day" if habit.frequency == "daily" else "week"
        streak_summary = (
            f"Current streak: {current_streak} {streak_unit}"
            f"{'' if current_streak == 1 else 's'} · best: {longest_streak} {streak_unit}"
            f"{'' if longest_streak == 1 else 's'}"
        )
        if habit.frequency == "daily":
            if today not in completed_dates:
                due.append((habit, f"Today’s check-in is still open · {streak_summary}"))
        else:
            completed = sum(week_start <= day <= today for day in completed_dates)
            if completed < habit.target_goal:
                remaining = habit.target_goal - completed
                due.append((
                    habit,
                    f"{remaining} of {habit.target_goal} weekly check-ins remaining · {streak_summary}",
                ))
    return due


def _make_message(user, due, today):
    message = EmailMessage()
    message["Subject"] = f"Your habit check-in for {today:%A, %B} {today.day}"
    message["From"] = current_app.config["SMTP_FROM"]
    message["To"] = user.email
    plain_lines = ["A small step today keeps your habits moving.", ""]
    html_rows = []
    for habit, status in due:
        plain_lines.append(f"- {habit.title}: {status}")
        html_rows.append(
            "<tr><td style=\"padding:12px 0;border-bottom:1px solid #e8e8e3;"
            "font-weight:600\">"
            f"{html.escape(habit.title)}</td><td style=\"padding:12px 0;"
            f"border-bottom:1px solid #e8e8e3;color:#526052\">{html.escape(status)}</td></tr>"
        )
    plain_lines.extend(["", "You can do this. Open your Habit Tracker to check in."])
    message.set_content("\n".join(plain_lines))
    message.add_alternative(
        "<!doctype html><html><body style=\"margin:0;background:#f5f6f1;"
        "font-family:Arial,sans-serif;color:#17251d\"><div style=\"max-width:600px;"
        "margin:32px auto;background:#fff;padding:32px;border-radius:16px\">"
        "<p style=\"color:#42724e;font-weight:700;letter-spacing:.08em;"
        "text-transform:uppercase;font-size:12px\">A note for your future self</p>"
        f"<h1 style=\"font-size:26px\">Your habits for {today:%A, %B} {today.day}</h1>"
        "<p>Small steps add up. Here’s what’s still on your list:</p>"
        "<table style=\"width:100%;border-collapse:collapse\">"
        + "".join(html_rows)
        + "</table><p style=\"margin-top:24px;color:#526052\">You’ve got this. "
        "Open your Habit Tracker and check in when you’re ready.</p></div></body></html>",
        subtype="html",
    )
    return message


def _send(message):
    host = current_app.config.get("SMTP_HOST")
    if not host or not current_app.config.get("SMTP_FROM"):
        raise RuntimeError("SMTP_HOST and SMTP_FROM must be configured to send reminders.")
    port = current_app.config["SMTP_PORT"]
    username = current_app.config.get("SMTP_USER")
    password = current_app.config.get("SMTP_PASSWORD")
    if current_app.config.get("SMTP_USE_TLS"):
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            if username:
                server.login(username, password or "")
            server.send_message(message)
    else:
        with smtplib.SMTP_SSL(host, port, timeout=20) as server:
            if username:
                server.login(username, password or "")
            server.send_message(message)


def send_due_reminders(today=None):
    today = today or date.today()
    sent = failures = 0
    for user in User.query.order_by(User.id).yield_per(100):
        try:
            due = _unfinished_habits(user, today)
            if not due:
                continue
            _send(_make_message(user, due, today))
            sent += 1
        except (OSError, smtplib.SMTPException, RuntimeError) as error:
            current_app.logger.error("Reminder delivery failed for user %s: %s", user.id, error)
            failures += 1
    return sent, failures
