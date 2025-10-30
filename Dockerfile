# -----------------------------
# Étape 1 : Image de base
# -----------------------------
FROM python:3.12-slim

# Empêche Python d'écrire des fichiers .pyc et force le flush stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Définir le dossier de travail
WORKDIR /app

# -----------------------------
# Étape 2 : Installer les dépendances système
# -----------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
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
RUN python manage.py collectstatic --noinput

# -----------------------------
# Étape 6 : Exposer le port
# -----------------------------
EXPOSE 8000

# -----------------------------
# Étape 7 : Lancer l’application avec Gunicorn
# -----------------------------
CMD ["bash", "-c", "python manage.py migrate && gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers=1 --threads=2"]

