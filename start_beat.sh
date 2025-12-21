#!/bin/bash
# Script de démarrage pour Celery Beat
# Utilisé par Coolify pour démarrer le service Celery Beat Scheduler

echo "Starting Celery Beat..."
celery -A core beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
