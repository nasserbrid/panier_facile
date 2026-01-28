"""
Vues pour le health check et les notifications automatiques.
"""
import os
import time
import logging
from django.http import JsonResponse
from django.core import management
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django_ratelimit.decorators import ratelimit

logger = logging.getLogger(__name__)


@ratelimit(key='ip', rate='5/h', method=['GET', 'POST'])
@csrf_exempt
@require_http_methods(["GET", "POST"])
def trigger_notification(request):
    """
    Endpoint sécurisé pour déclencher les notifications quotidiennes.
    Appelé par cron-job.org avec un token de sécurité.
    Rate limit: 5 requêtes par heure par IP.
    """
    start_time = time.time()

    if getattr(request, 'limited', False):
        logger.warning(f"Rate limit dépassé pour IP: {request.META.get('REMOTE_ADDR')}")
        return JsonResponse({
            "error": "Too many requests"
        }, status=429)

    logger.info("=" * 70)
    logger.info(f"Requête de notification reçue à {timezone.now()}")
    logger.info(f"   User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
    logger.info(f"   IP: {request.META.get('REMOTE_ADDR', 'Unknown')}")
    logger.info(f"   Method: {request.method}")

    token = request.headers.get("X-CRON-TOKEN")
    expected_token = os.getenv("TOKEN")

    if not expected_token:
        logger.error("TOKEN environnement non configuré !")
        return JsonResponse({
            "error": "Server configuration error"
        }, status=500)

    if token != expected_token:
        logger.warning(f"Tentative d'accès non autorisé")
        logger.warning(f"   Token reçu: {token[:10] if token else 'None'}...")
        logger.warning(f"   IP: {request.META.get('REMOTE_ADDR', 'Unknown')}")
        return JsonResponse({
            "error": "Unauthorized"
        }, status=403)

    logger.info("Token validé avec succès")

    try:
        logger.info("Démarrage de l'envoi des notifications...")

        management.call_command('notify_old_paniers')

        elapsed_time = time.time() - start_time

        logger.info("Notifications envoyées avec succès")
        logger.info(f"   Temps d'exécution: {elapsed_time:.2f}s")
        logger.info("=" * 70)

        return JsonResponse({
            "status": "ok",
            "message": "Notifications sent successfully",
            "execution_time_seconds": round(elapsed_time, 2),
            "timestamp": timezone.now().isoformat()
        }, status=200)

    except Exception as e:
        elapsed_time = time.time() - start_time

        logger.error("=" * 70)
        logger.error(f"Erreur lors de l'envoi des notifications")
        logger.error(f"   Erreur: {str(e)}")
        logger.error(f"   Temps avant échec: {elapsed_time:.2f}s")
        logger.error("=" * 70)
        logger.exception("Stacktrace complète:")

        return JsonResponse({
            "status": "error",
            "message": "Failed to send notifications",
            "error": str(e),
            "execution_time_seconds": round(elapsed_time, 2),
            "timestamp": timezone.now().isoformat()
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "HEAD"])
def health_check(request):
    """
    Endpoint de santé simple pour les monitoring et keep-alive.
    Pas d'authentification requise.
    """
    return JsonResponse({
        "status": "healthy",
        "service": "panier_facile",
        "timestamp": timezone.now().isoformat()
    }, status=200)
