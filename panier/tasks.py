"""
Tâches Celery pour l'application panier.

Ce module contient les tâches asynchrones, notamment l'envoi
de notifications pour les paniers anciens.
"""
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.conf import settings
from datetime import timedelta
from .models import Panier
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    name='panier.tasks.send_old_basket_notifications'
)
def send_old_basket_notifications(self):
    """
    Envoie des notifications par email aux utilisateurs pour les paniers
    créés il y a exactement 14 jours et qui n'ont pas encore reçu de notification.

    Cette tâche est exécutée quotidiennement par Celery Beat à 8h et 18h.

    Fonctionnement:
    - Recherche tous les paniers créés il y a 14 jours (±1 jour de tolérance)
    - Vérifie que notification_sent est False
    - Envoie un email avec la liste des courses du panier
    - Marque le panier comme notifié (notification_sent=True, notification_sent_date=now)

    Returns:
        dict: Statistiques d'envoi (succès, échecs, total)
    """
    try:
        now = timezone.now()
        target_date = now - timedelta(days=14)

        # Tolérance d'un jour pour éviter de manquer des notifications
        # en cas de problème de serveur
        start_date = target_date - timedelta(days=1)
        end_date = target_date + timedelta(days=1)

        # Récupérer les paniers éligibles
        paniers_a_notifier = Panier.objects.filter(
            date_creation__date__gte=start_date.date(),
            date_creation__date__lte=end_date.date(),
            notification_sent=False
        ).select_related('user')

        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }

        logger.info(f"Début envoi notifications - {paniers_a_notifier.count()} paniers trouvés")

        for panier in paniers_a_notifier:
            stats['total'] += 1

            try:
                # Récupérer les courses du panier
                courses = panier.courses.all()
                liste_courses = "\n".join([f"- {course.titre}" for course in courses])

                # Composer le message
                message = (
                    f"Bonjour {panier.user.username},\n\n"
                    f"Vous devez faire vos courses car cela fait deux semaines depuis votre dernier panier.\n"
                    f"Voici la liste des courses de ce panier :\n"
                    f"{liste_courses if liste_courses else 'Aucune course.'}\n\n"
                    f"À bientôt sur PanierFacile !\n\n"
                    f"---\n"
                    f"Panier créé le {panier.date_creation.strftime('%d/%m/%Y à %H:%M')}\n"
                    f"Pour vous désabonner de ces notifications, connectez-vous à votre compte."
                )

                # Envoyer l'email
                send_mail(
                    subject="Rappel : Il est temps de refaire vos courses !",
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[panier.user.email],
                    fail_silently=False,
                )

                # Marquer le panier comme notifié
                panier.notification_sent = True
                panier.notification_sent_date = now
                panier.save(update_fields=['notification_sent', 'notification_sent_date'])

                stats['success'] += 1
                logger.info(f"Notification envoyée avec succès pour le panier #{panier.id} - {panier.user.email}")

            except Exception as e:
                stats['failed'] += 1
                error_msg = f"Erreur pour panier #{panier.id}: {str(e)}"
                stats['errors'].append(error_msg)
                logger.error(error_msg)

        # Log final
        logger.info(
            f"Envoi notifications terminé - "
            f"Total: {stats['total']}, "
            f"Succès: {stats['success']}, "
            f"Échecs: {stats['failed']}"
        )

        return stats

    except Exception as e:
        # En cas d'erreur globale, retry la tâche
        logger.error(f"Erreur globale dans send_old_basket_notifications: {str(e)}")
        raise self.retry(exc=e)


@shared_task(name='panier.tasks.test_celery')
def test_celery():
    """
    Tâche de test pour vérifier que Celery fonctionne correctement.

    Usage:
        from panier.tasks import test_celery
        test_celery.delay()
    """
    logger.info("✅ Celery fonctionne correctement!")
    return "Celery is working!"


@shared_task(bind=True, max_retries=3, name='panier.tasks.update_intermarche_prices')
def update_intermarche_prices(self):
    """
    Tâche Celery pour mettre à jour les prix Intermarché
    Scrape les produits pour tous les ingrédients

    Exécutée quotidiennement via Celery Beat
    """
    from .models import Ingredient, IntermarcheProductMatch
    from .intermarche_scraper import search_intermarche_products

    logger.info("Début de la mise à jour des prix Intermarché")

    try:
        # Récupérer tous les ingrédients
        ingredients = Ingredient.objects.all()
        total = ingredients.count()

        logger.info(f"Mise à jour des prix pour {total} ingrédients")

        updated_count = 0
        created_count = 0
        error_count = 0

        for index, ingredient in enumerate(ingredients, 1):
            try:
                logger.info(f"[{index}/{total}] Recherche de '{ingredient.nom}'...")

                # Rechercher les produits
                products = search_intermarche_products(ingredient.nom)

                if not products:
                    logger.warning(f"Aucun produit trouvé pour '{ingredient.nom}'")
                    continue

                # Prendre le premier produit (le plus pertinent)
                best_product = products[0]

                # Mettre à jour ou créer le match
                match, created = IntermarcheProductMatch.objects.update_or_create(
                    ingredient=ingredient,
                    defaults={
                        'product_name': best_product['name'],
                        'price': best_product.get('price'),
                        'is_available': best_product.get('is_available', True),
                        'product_url': best_product.get('url'),
                        'last_updated': timezone.now()
                    }
                )

                if created:
                    created_count += 1
                    logger.info(f"✓ Créé match pour '{ingredient.nom}': {best_product['name']} - {best_product.get('price')}€")
                else:
                    updated_count += 1
                    logger.info(f"✓ Mis à jour '{ingredient.nom}': {best_product['name']} - {best_product.get('price')}€")

            except Exception as e:
                error_count += 1
                logger.error(f"✗ Erreur pour '{ingredient.nom}': {e}")
                continue

        logger.info(f"Mise à jour terminée: {created_count} créés, {updated_count} mis à jour, {error_count} erreurs")

        return {
            'status': 'success',
            'total': total,
            'created': created_count,
            'updated': updated_count,
            'errors': error_count
        }

    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des prix: {e}")
        # Retry avec backoff exponentiel
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(name='panier.tasks.update_single_ingredient_price')
def update_single_ingredient_price(ingredient_id: int):
    """
    Tâche pour mettre à jour le prix d'un seul ingrédient

    Args:
        ingredient_id: ID de l'ingrédient à mettre à jour
    """
    from .models import Ingredient, IntermarcheProductMatch
    from .intermarche_scraper import search_intermarche_products

    try:
        ingredient = Ingredient.objects.get(id=ingredient_id)
        logger.info(f"Mise à jour du prix pour '{ingredient.nom}'")

        products = search_intermarche_products(ingredient.nom)

        if not products:
            logger.warning(f"Aucun produit trouvé pour '{ingredient.nom}'")
            return {'status': 'no_products_found'}

        best_product = products[0]

        match, created = IntermarcheProductMatch.objects.update_or_create(
            ingredient=ingredient,
            defaults={
                'product_name': best_product['name'],
                'price': best_product.get('price'),
                'is_available': best_product.get('is_available', True),
                'product_url': best_product.get('url'),
                'last_updated': timezone.now()
            }
        )

        action = 'created' if created else 'updated'
        logger.info(f"Prix {action} pour '{ingredient.nom}': {best_product['name']} - {best_product.get('price')}€")

        return {
            'status': 'success',
            'action': action,
            'product': best_product
        }

    except Ingredient.DoesNotExist:
        logger.error(f"Ingrédient {ingredient_id} non trouvé")
        return {'status': 'error', 'message': 'Ingredient not found'}

    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de l'ingrédient {ingredient_id}: {e}")
        return {'status': 'error', 'message': str(e)}
