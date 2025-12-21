"""
Initialisation de l'application Django et Celery.
"""
# Ceci garantit que l'app Celery est toujours importée quand Django démarre
# pour que shared_task utilise cette app.
from .celery import app as celery_app

__all__ = ('celery_app',)
