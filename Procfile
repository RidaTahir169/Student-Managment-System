web: python manage.py migrate --noinput && python manage.py seed_data && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --log-file -
worker: celery -A config worker -l info
beat: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler