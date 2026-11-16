import unittest
from datetime import date, timedelta
from unittest.mock import patch

from app import create_app, db
from app.models import Habit, HabitLog, HabitNote, User


class HabitAppTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "WTF_CSRF_ENABLED": False,
            "SMTP_FROM": "reminders@example.com",
            "SMTP_HOST": "smtp.example.com",
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def register_and_login(self, email="one@example.com"):
        return self.client.post("/register", data={
            "email": email,
            "password": "a-very-strong-password",
        }, follow_redirects=True)

    def test_registration_create_checkin_and_undo(self):
        response = self.register_and_login()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"My Habits", response.data)

        response = self.client.post("/habits/new", data={
            "title": "Read for ten minutes",
            "description": "A book before bed",
            "frequency": "daily",
            "target_goal": "1",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        habit = Habit.query.one()
        self.assertIn(b"Read for ten minutes", response.data)

        self.client.post(f"/habits/{habit.id}/check-in")
        self.assertTrue(Habit.query.one().logs[0].completed)
        self.client.post(f"/habits/{habit.id}/check-in")
        self.assertFalse(Habit.query.one().logs[0].completed)

    def test_dashboard_summarizes_the_last_seven_days(self):
        self.register_and_login()
        self.client.post("/habits/new", data={
            "title": "Daily walk",
            "frequency": "daily",
            "target_goal": "1",
        })
        habit = Habit.query.one()
        db.session.add_all([
            HabitLog(
                habit_id=habit.id,
                logged_on=date.today() - timedelta(days=offset),
                completed=True,
            )
            for offset in range(7)
        ])
        db.session.commit()

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"--progress: 100%", response.data)
        self.assertIn(b"7</strong>", response.data)
        self.assertEqual(response.data.count(b'class="week-dot '), 7)

    def test_habit_is_not_accessible_to_another_user(self):
        self.register_and_login()
        self.client.post("/habits/new", data={
            "title": "Private habit",
            "frequency": "daily",
            "target_goal": "1",
        })
        self.client.post("/logout")

        second_user = User(email="two@example.com")
        second_user.set_password("another-strong-password")
        db.session.add(second_user)
        db.session.commit()
        self.client.post("/login", data={
            "email": "two@example.com",
            "password": "another-strong-password",
        })

        response = self.client.post("/habits/1/delete")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Habit.query.count(), 1)

    def test_reminder_includes_only_unfinished_habits_and_escapes_html(self):
        from app.services.email import send_due_reminders

        user = User(email="mail@example.com")
        user.set_password("another-strong-password")
        daily = Habit(user=user, title="Already done", frequency="daily", target_goal=1)
        weekly = Habit(user=user, title="<script>alert(1)</script>", frequency="weekly", target_goal=2)
        db.session.add_all([user, daily, weekly])
        db.session.flush()
        db.session.add(HabitLog(habit_id=daily.id, logged_on=date(2026, 11, 13), completed=True))
        db.session.add(HabitLog(habit_id=weekly.id, logged_on=date(2026, 11, 12), completed=True))
        db.session.commit()

        with patch("app.services.email._send") as send:
            sent, failures = send_due_reminders(date(2026, 11, 13))

        self.assertEqual((sent, failures), (1, 0))
        message = send.call_args.args[0]
        html_body = message.get_body(preferencelist=("html",)).get_content()
        self.assertIn("&lt;script&gt;", html_body)
        self.assertIn("Current streak:", html_body)
        self.assertNotIn("Already done", html_body)

    def test_daily_notes_are_saved_edited_and_deleted_separately_from_checkins(self):
        self.register_and_login()
        self.client.post("/habits/new", data={
            "title": "Journal habit",
            "frequency": "daily",
            "target_goal": "1",
        })
        habit = Habit.query.one()
        note_url = f"/habits/{habit.id}/notes"
        today = date.today().isoformat()

        response = self.client.post(note_url, data={
            "note_date": today,
            "body": "Felt good to get started.",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Felt good to get started.", response.data)
        self.assertEqual(HabitNote.query.one().note_date, date.today())
        self.assertEqual(HabitLog.query.count(), 0)

        response = self.client.post(note_url, data={
            "note_date": today,
            "body": "Updated reflection.",
            "return_to": "journal",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Updated reflection.", response.data)
        self.assertEqual(HabitNote.query.one().body, "Updated reflection.")

        response = self.client.post(note_url, data={
            "note_date": today,
            "delete": "1",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(HabitNote.query.count(), 0)

    def test_note_dates_cannot_be_in_the_future(self):
        self.register_and_login()
        self.client.post("/habits/new", data={
            "title": "Journal habit",
            "frequency": "daily",
            "target_goal": "1",
        })
        response = self.client.post("/habits/1/notes", data={
            "note_date": "2999-01-01",
            "body": "A future note",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(HabitNote.query.count(), 0)


if __name__ == "__main__":
    unittest.main()
