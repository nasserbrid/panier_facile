"""
Tâches Celery pour l'application panier.

Tâches:
- send_old_basket_notifications : rappel email pour paniers anciens
"""
from celery import shared_task
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from .models import Panier

import logging

logger = logging.getLogger(__name__)

User = get_user_model()


# ── Tâches Celery ───────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    name='panier.tasks.send_old_basket_notifications'
)
def send_old_basket_notifications(self):
    """Envoie des rappels email pour les paniers créés il y a 14 jours."""
    try:
        now = timezone.now()
        target_date = now - timedelta(days=14)

        paniers = Panier.objects.filter(
            date_creation__date__gte=(target_date - timedelta(days=1)).date(),
            date_creation__date__lte=(target_date + timedelta(days=1)).date(),
            notification_sent=False
        ).select_related('user')

        stats = {'total': 0, 'success': 0, 'failed': 0}
        logger.info(f"Notifications: {paniers.count()} paniers trouvés")

        for panier in paniers:
            stats['total'] += 1
            try:
                courses = panier.courses.all()
                liste = "\n".join([f"- {c.titre}" for c in courses])

                send_mail(
                    subject="Rappel : Il est temps de refaire vos courses !",
                    message=(
                        f"Bonjour {panier.user.username},\n\n"
                        f"Cela fait deux semaines depuis votre dernier panier.\n"
                        f"Voici votre liste :\n{liste or 'Aucune course.'}\n\n"
                        f"À bientôt sur PanierFacile !"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[panier.user.email],
                    fail_silently=False,
                )

                panier.notification_sent = True
                panier.notification_sent_date = now
                panier.save(update_fields=['notification_sent', 'notification_sent_date'])
                stats['success'] += 1

            except Exception as e:
                stats['failed'] += 1
                logger.error(f"Notification panier #{panier.id}: {e}")

        logger.info(f"Notifications: {stats['success']}/{stats['total']} envoyées")
        return stats

    except Exception as e:
        logger.error(f"Erreur notifications: {e}")
        raise self.retry(exc=e)


@shared_task(name='panier.tasks.test_celery')
def test_celery():
    """Tâche de test Celery."""
    logger.info("Celery fonctionne correctement!")
    return "Celery is working!"
