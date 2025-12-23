# -----------------------------
# Étape 1 : Image de base
# -----------------------------
FROM python:3.12-slim

# Empêche Python d'écrire des fichiers .pyc et force le flush stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RUN_MAIN=true

# Définir le dossier de travail
WORKDIR /app

# -----------------------------
# Étape 2 : Installer les dépendances système
# -----------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    gdal-bin \
    libgdal-dev \
    binutils \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Étape 3 : Installer les dépendances Python
# -----------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# -----------------------------
# Étape 4 : Copier le code source
# -----------------------------
COPY . .

# -----------------------------
# Étape 5 : Collecter les fichiers statiques
# -----------------------------
# Utiliser SQLite temporairement pour collectstatic (pas besoin de vraie DB)
ENV DATABASE_URL=sqlite:///tmp/db.sqlite3
RUN python manage.py collectstatic --noinput

# -----------------------------
# Étape 6 : Exposer le port
# -----------------------------
EXPOSE 8000

# -----------------------------
# Étape 7 : Script de démarrage conditionnel
# -----------------------------
# Créer un script d'entrypoint qui choisit la commande selon APP_TYPE
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

CMD ["/docker-entrypoint.sh"]