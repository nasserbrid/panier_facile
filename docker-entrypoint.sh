#!/bin/bash
set -e

# Script d'entrypoint pour démarrer différents services
# Utilise la variable d'environnement APP_TYPE pour déterminer quel service lancer

case "${APP_TYPE:-web}" in
  web)
    echo "Starting Django Web Server with Gunicorn..."
    # Fake TOUTES les migrations supermarkets (tables gérées manuellement ci-dessous)
    python manage.py migrate contact 0001_initial --fake || true
    python manage.py migrate supermarkets 0001_initial --fake || true
    python manage.py migrate supermarkets 0002_remove_old_add_pricecomparison --fake || true
    python manage.py migrate supermarkets 0003_replace_auchan_with_aldi --fake || true
    python manage.py migrate

    # Gérer les tables et colonnes manuellement (migrations fakées)
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

# Créer supermarkets_pricecomparison si absente
cursor.execute(\"\"\"
CREATE TABLE IF NOT EXISTS supermarkets_pricecomparison (
    id BIGSERIAL PRIMARY KEY,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    carrefour_total DECIMAL(10, 2),
    aldi_total DECIMAL(10, 2),
    carrefour_found INTEGER DEFAULT 0,
    aldi_found INTEGER DEFAULT 0,
    total_ingredients INTEGER DEFAULT 0,
    cheapest_supermarket VARCHAR(20) DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id BIGINT NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    panier_id BIGINT NOT NULL REFERENCES panier_panier(id) ON DELETE CASCADE
);
\"\"\")

# Supprimer les anciennes tables si elles existent
cursor.execute(\"DROP TABLE IF EXISTS panier_intermarcheproductmatch CASCADE;\")
cursor.execute(\"DROP TABLE IF EXISTS panier_auchanproductmatch CASCADE;\")

# Renommer colonnes auchan -> aldi dans PriceComparison (si pas encore fait)
cursor.execute(\"\"\"
DO \$\$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='supermarkets_pricecomparison' AND column_name='auchan_total') THEN
        ALTER TABLE supermarkets_pricecomparison RENAME COLUMN auchan_total TO aldi_total;
        ALTER TABLE supermarkets_pricecomparison RENAME COLUMN auchan_found TO aldi_found;
    END IF;
END \$\$;
\"\"\")

print('Tables et colonnes vérifiées/mises à jour.')
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
