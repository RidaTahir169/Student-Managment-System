#!/bin/bash
set -e

# 1. Run database migrations
echo "==> Running database migrations..."
python manage.py migrate --noinput

# 2. Seed initial admin account, teachers, students, and courses if database is empty
echo "==> Seeding initial data and demo accounts..."
python manage.py seed_data

# 3. Start Celery worker & beat in background if REDIS_URL is provided
if [ -n "$REDIS_URL" ]; then
    echo "==> Starting Celery worker (detached)..."
    celery -A config worker -l info --detach
    echo "==> Starting Celery beat (detached)..."
    celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler --detach
else
    echo "==> REDIS_URL not set. Skipping Celery worker and beat."
fi

# 4. Start Gunicorn in foreground
echo "==> Starting Gunicorn web server..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --log-file -
