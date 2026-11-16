from collections import Counter
from datetime import date, timedelta


def _week_start(day):
    return day - timedelta(days=day.weekday())


def calculate_streaks(habit, completed_dates, today=None):
    """Return (current, longest), counting consecutive days or goal-complete weeks."""
    today = today or date.today()
    dates = set(completed_dates)

    if habit.frequency == "daily":
        if today in dates:
            cursor = today
        elif today - timedelta(days=1) in dates:
            cursor = today - timedelta(days=1)
        else:
            cursor = None

        current = 0
        while cursor and cursor in dates:
            current += 1
            cursor -= timedelta(days=1)

        longest = run = 0
        previous = None
        for day in sorted(dates):
            run = run + 1 if previous and day == previous + timedelta(days=1) else 1
            longest = max(longest, run)
            previous = day
        return current, longest

    counts = Counter(_week_start(day) for day in dates)
    complete_weeks = {week for week, count in counts.items() if count >= habit.target_goal}
    current_week = _week_start(today)
    if current_week not in complete_weeks:
        current_week -= timedelta(days=7)
    current = 0
    while current_week in complete_weeks:
        current += 1
        current_week -= timedelta(days=7)

    longest = run = 0
    previous_week = None
    for week in sorted(complete_weeks):
        run = run + 1 if previous_week and week == previous_week + timedelta(days=7) else 1
        longest = max(longest, run)
        previous_week = week
    return current, longest
