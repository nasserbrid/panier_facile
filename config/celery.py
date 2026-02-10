"""
Configuration Celery pour PanierFacile.

Ce fichier configure Celery pour gérer les tâches asynchrones,
notamment l'envoi de notifications aux utilisateurs.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Définir le module de settings Django par défaut
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Créer l'application Celery
app = Celery('panier_facile')

# Charger la configuration depuis Django settings
# - namespace='CELERY' signifie que toutes les variables de config
#   commençant par CELERY_ dans settings.py seront utilisées
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-découverte des tâches dans les applications Django
app.autodiscover_tasks()

# Configuration du scheduler Celery Beat pour les tâches périodiques
app.conf.beat_schedule = {
    'send-basket-notifications-morning': {
        'task': 'panier.tasks.send_old_basket_notifications',
        'schedule': crontab(hour=8, minute=0),  # Tous les jours à 8h00 (heure Paris)
        'options': {
            'expires': 3600,  # La tâche expire après 1 heure si non exécutée
        },
    },
    'send-basket-notifications-evening': {
        'task': 'panier.tasks.send_old_basket_notifications',
        'schedule': crontab(hour=18, minute=0),  # Tous les jours à 18h00 (heure Paris)
        'options': {
            'expires': 3600,
        },
    },
}

# Configuration du fuseau horaire pour Celery Beat
app.conf.timezone = 'Europe/Paris'

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tâche de débogage pour tester Celery."""
    print(f'Request: {self.request!r}')
