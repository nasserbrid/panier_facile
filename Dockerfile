# -----------------------------
# Étape 1 : Image de base
# -----------------------------
FROM python:3.12-slim

# Empêche Python d'écrire des fichiers .pyc et force le flush stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RUN_MAIN=true

# Je définis le dossier de travail
WORKDIR /app

# -----------------------------
# Étape 2 : J'installe les dépendances système
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
# Étape 3 : J'installe les dépendances Python
# -----------------------------
COPY requirements.txt .
# Installer pip et les dépendances avec nettoyage agressif pour économiser la RAM
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge && \
    find /usr/local/lib/python3.12 -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

# -----------------------------
# Étape 4 : Je copie le code source
# -----------------------------
COPY . .

# -----------------------------
# Étape 5 : Je collecte les fichiers statiques
# -----------------------------
# J'utilise SQLite temporairement pour collectstatic (pas besoin de vraie DB)
ENV DATABASE_URL=sqlite:///tmp/db.sqlite3
RUN echo "=== Running collectstatic ===" && \
    python manage.py collectstatic --noinput --verbosity 2 && \
    echo "=== Collectstatic complete - $(ls -1 staticfiles/ | wc -l) files collected ==="

# -----------------------------
# Étape 6 : J'expose le port
# -----------------------------
EXPOSE 8000

# -----------------------------
# Étape 7 : Script de démarrage conditionnel
# -----------------------------
# Je crée un script d'entrypoint qui choisit la commande selon APP_TYPE
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

CMD ["/docker-entrypoint.sh"]