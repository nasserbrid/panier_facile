#!/bin/bash
# Script de démarrage pour Celery Worker
# Utilisé par Coolify pour démarrer le service Celery Worker

echo "Starting Celery Worker..."
celery -A config worker --loglevel=info --concurrency=2
