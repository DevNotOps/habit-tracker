FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/.deps" \
    PATH="/app/.deps/bin:${PATH}"

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --no-create-home app

COPY --chown=app:app .deps /app/.deps
COPY --chown=app:app app ./app
COPY --chown=app:app wsgi.py ./wsgi.py

USER app

EXPOSE 8000

CMD ["python", "-m", "gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]
