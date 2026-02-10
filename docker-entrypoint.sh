#!/bin/bash
set -e

# Script d'entrypoint pour démarrer différents services
# Utilise la variable d'environnement APP_TYPE pour déterminer quel service lancer

case "${APP_TYPE:-web}" in
  web)
    echo "Starting Django Web Server with Gunicorn..."
    python manage.py migrate contact 0001_initial --fake || true
    python manage.py migrate

    # Gérer les tables manuellement (migration contact fakée)
    python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()

# Créer panier_customerreview si absente (migration contact fakée)
cursor.execute(\"\"\"
CREATE TABLE IF NOT EXISTS panier_customerreview (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) DEFAULT '',
    email VARCHAR(254) DEFAULT '',
    rating INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    review TEXT NOT NULL,
    would_recommend BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_approved BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE
);
\"\"\")

# Supprimer les anciennes tables supermarkets si elles existent
cursor.execute(\"DROP TABLE IF EXISTS supermarkets_leclercproductmatch CASCADE;\")
cursor.execute(\"DROP TABLE IF EXISTS supermarkets_lidlproductmatch CASCADE;\")
cursor.execute(\"DROP TABLE IF EXISTS supermarkets_aldiproductmatch CASCADE;\")
cursor.execute(\"DROP TABLE IF EXISTS supermarkets_pricecomparison CASCADE;\")
cursor.execute(\"DROP TABLE IF EXISTS panier_intermarcheproductmatch CASCADE;\")
cursor.execute(\"DROP TABLE IF EXISTS panier_auchanproductmatch CASCADE;\")
cursor.execute(\"DROP TABLE IF EXISTS panier_carrefourproductmatch CASCADE;\")

print('Tables vérifiées/nettoyées.')
" || true
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
