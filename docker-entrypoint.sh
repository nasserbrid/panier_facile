#!/bin/bash
set -e

# Script d'entrypoint pour démarrer différents services
# Utilise la variable d'environnement APP_TYPE pour déterminer quel service lancer

case "${APP_TYPE:-web}" in
  web)
    echo "Starting Django Web Server with Gunicorn..."
    # Fake migrations pour apps dont les tables existent déjà
    python manage.py migrate contact --fake-initial || true
    python manage.py migrate supermarkets --fake-initial || true
    python manage.py migrate
    exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers=2 --threads=4 --timeout=120 --access-logfile - --error-logfile -
    ;;

  worker)
    echo "Starting Celery Worker..."
    exec celery -A config worker --loglevel=info --concurrency=2
    ;;

  beat)
    echo "Starting Celery Beat Scheduler..."
    exec celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    ;;

  *)
    echo "Error: Unknown APP_TYPE='${APP_TYPE}'"
    echo "Valid values: web, worker, beat"
    exit 1
    ;;
esac
