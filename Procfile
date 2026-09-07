web: bash start.sh
worker: celery -A config worker -l info
beat: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler