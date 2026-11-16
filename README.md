# Habit Loop

A responsive habit tracker built with Flask, SQLAlchemy, PostgreSQL, server-side login sessions, and optional SMTP reminders.

## Requirements

- Python 3.10+
- PostgreSQL 13+
- An SMTP account to send reminders (optional until the reminder command is used)

## Set up locally

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `SECRET_KEY`, `DATABASE_URL`, and your SMTP settings. Generate a strong application key with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Create a PostgreSQL role and database (run these from a PostgreSQL shell such as `psql`; replace the example password):

```sql
CREATE USER habit_user WITH PASSWORD 'change-me';
CREATE DATABASE habit_tracker OWNER habit_user;
```

Initialize the schema and run the development server:

```powershell
flask --app wsgi:app init-db
flask --app wsgi:app run
```

Open <http://127.0.0.1:5000> and create an account. The application does not create schema automatically on web startup; use `init-db` for a new installation. `init-db` also creates new tables added by an application update; use a migration tool such as Flask-Migrate/Alembic for changes to existing tables.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# Edit .env and create the PostgreSQL user/database as above.
flask --app wsgi:app init-db
flask --app wsgi:app run
```

## Docker

Docker Compose runs the Flask app and PostgreSQL together. First, create `.env` and set unique, strong values for `SECRET_KEY` and `POSTGRES_PASSWORD`:

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Use the generated value for `SECRET_KEY`; set a strong `POSTGRES_PASSWORD`. Compose configures the app's `DATABASE_URL` to connect to the `db` service automatically, so you do not need to change the localhost URL in `.env.example`.

Build and start the stack:

```powershell
docker compose up --build -d
```

Compose waits for PostgreSQL to become healthy, runs the schema initializer, then starts the app. Open <http://localhost:8000>. PostgreSQL data is kept in the named `postgres_data` volume. The app runs Gunicorn as a non-root user. SMTP settings in `.env` are optional unless you want to send reminders.

View logs, stop the services, or stop them and remove the database volume:

```bash
docker compose logs -f
docker compose down
docker compose down --volumes
```

The final command permanently deletes the Compose PostgreSQL data volume.

## Production

Set `SECRET_KEY` to a unique random secret, set `SESSION_COOKIE_SECURE=true` behind HTTPS, and configure a production `DATABASE_URL` and SMTP credentials. Run behind a TLS-terminating reverse proxy with a production WSGI server:

```bash
gunicorn --workers 2 --bind 0.0.0.0:8000 wsgi:app
```

Keep `.env` out of source control. Database connections use SQLAlchemy pooling with pre-ping and connection recycling. Forms use CSRF protection; passwords are hashed with Werkzeug's password hashing implementation; authenticated pages are served over Flask-Login sessions.

## Email reminders

The scheduled command sends one styled HTML/plain-text reminder to each user who has an incomplete daily check-in or has not yet reached a weekly goal. Users with no unfinished goals do not receive email. SMTP errors are logged, and the command exits unsuccessfully if any delivery fails.

Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, and `SMTP_USE_TLS`, then test manually:

```powershell
flask --app wsgi:app send-reminders
```

Schedule the command once per day with Windows Task Scheduler or cron. For cron, activate the virtual environment and load the same environment variables used by the web process before running `flask --app wsgi:app send-reminders`. The reminder job is a CLI command, not an unauthenticated public endpoint.

## Behavior

- Daily habits are checked in once per local server date.
- Weekly habits have a goal of 1–7 check-ins, counted Monday through Sunday.
- A check-in can be toggled off for the current date.
- Each habit has a separate daily note, with a paginated journal for reviewing, editing, and deleting past notes. Notes do not affect check-ins or streaks.
- Current streaks allow today to remain incomplete while preserving a streak completed through yesterday; longest streaks use consecutive days for daily habits and consecutive goal-complete weeks for weekly habits.
- All habits belong to their signed-in owner. Deleting a habit also removes its check-in history.
