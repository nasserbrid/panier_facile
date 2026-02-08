#!/bin/bash
set -e

# Script d'entrypoint pour démarrer différents services
# Utilise la variable d'environnement APP_TYPE pour déterminer quel service lancer

case "${APP_TYPE:-web}" in
  web)
    echo "Starting Django Web Server with Gunicorn..."
    # Fake les migrations initiales (tables existent déjà en base)
    python manage.py migrate contact 0001_initial --fake || true
    python manage.py migrate supermarkets 0001_initial --fake || true
    python manage.py migrate supermarkets 0002_remove_old_add_pricecomparison --fake || true
    python manage.py migrate

    # Créer les tables ProductMatch si elles n'existent pas (migration fakée mais tables absentes)
    python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()

# Créer panier_carrefourproductmatch si absente
cursor.execute(\"\"\"
CREATE TABLE IF NOT EXISTS panier_carrefourproductmatch (
    id BIGSERIAL PRIMARY KEY,
    store_id VARCHAR(20) DEFAULT 'scraping',
    product_name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2),
    product_url VARCHAR(200),
    is_available BOOLEAN DEFAULT TRUE,
    match_score DOUBLE PRECISION DEFAULT 0.0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ingredient_id BIGINT NOT NULL REFERENCES panier_ingredient(id) ON DELETE CASCADE
);
\"\"\")

# Créer supermarkets_aldiproductmatch si absente
cursor.execute(\"\"\"
CREATE TABLE IF NOT EXISTS supermarkets_aldiproductmatch (
    id BIGSERIAL PRIMARY KEY,
    store_id VARCHAR(20) DEFAULT 'scraping',
    product_name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2),
    product_url VARCHAR(200),
    is_available BOOLEAN DEFAULT TRUE,
    match_score DOUBLE PRECISION DEFAULT 0.0,
    image_url VARCHAR(200),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ingredient_id BIGINT NOT NULL REFERENCES panier_ingredient(id) ON DELETE CASCADE
);
\"\"\")

print('Tables ProductMatch vérifiées/créées.')
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
