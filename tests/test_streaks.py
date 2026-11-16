import unittest
from datetime import date, timedelta
from types import SimpleNamespace

from app.streaks import calculate_streaks


class StreakTests(unittest.TestCase):
    def test_daily_streak_continues_through_yesterday_and_tracks_longest(self):
        today = date(2026, 11, 13)
        habit = SimpleNamespace(frequency="daily", target_goal=1)
        dates = [today - timedelta(days=offset) for offset in (1, 2, 3, 6, 7)]
        self.assertEqual(calculate_streaks(habit, dates, today), (3, 3))

    def test_daily_streak_breaks_after_a_missed_day(self):
        today = date(2026, 11, 13)
        habit = SimpleNamespace(frequency="daily", target_goal=1)
        dates = [today - timedelta(days=offset) for offset in (2, 3, 7, 8, 9)]
        self.assertEqual(calculate_streaks(habit, dates, today), (0, 3))

    def test_weekly_streak_counts_only_goal_complete_weeks(self):
        today = date(2026, 11, 13)
        habit = SimpleNamespace(frequency="weekly", target_goal=2)
        dates = [
            date(2026, 10, 26), date(2026, 10, 28),
            date(2026, 11, 2), date(2026, 11, 5),
            date(2026, 11, 9),
        ]
        self.assertEqual(calculate_streaks(habit, dates, today), (2, 2))


if __name__ == "__main__":
    unittest.main()
