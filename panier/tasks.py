"""
Tâches Celery pour l'application panier.

Tâches:
- send_old_basket_notifications : rappel email pour paniers anciens
- compare_supermarket_prices    : comparaison Carrefour vs Aldi
- scrape_ingredient_prices      : cache proactif des prix
- refresh_popular_ingredients   : rafraîchissement quotidien du cache
"""
from celery import shared_task
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from .models import Panier

import logging

logger = logging.getLogger(__name__)

User = get_user_model()

CACHE_DURATION = timedelta(hours=24)
STORE_ID = 'scraping'


# ── Helpers ─────────────────────────────────────────────────────

def _get_ingredient_paniers(panier):
    """Récupère ou crée les IngredientPanier à partir des courses du panier."""
    from .models import Ingredient, IngredientPanier

    courses = panier.courses.filter(
        ingredient__isnull=False
    ).exclude(ingredient='')

    result = []
    for course in courses:
        lines = [l.strip() for l in course.ingredient.split('\n') if l.strip()]
        for text in lines:
            ingredient, _ = Ingredient.objects.get_or_create(
                nom=text,
                defaults={'quantite': '1', 'unite': ''}
            )
            ing_panier, _ = IngredientPanier.objects.get_or_create(
                panier=panier,
                ingredient=ingredient,
                defaults={'quantite': 1}
            )
            result.append(ing_panier)
    return result


def _scrape_supermarket(scraper_name, ingredients, model_class, task=None,
                        progress_offset=0, progress_total=0):
    """
    Scrape une liste d'ingrédients pour un supermarché donné.

    Args:
        scraper_name: 'carrefour' ou 'aldi'
        ingredients: liste d'objets Ingredient
        model_class: CarrefourProductMatch ou AldiProductMatch
        task: tâche Celery pour progress updates (optionnel)
        progress_offset: offset pour la barre de progression
        progress_total: total pour la barre de progression

    Returns:
        (total_price, found_count, error_count)
    """
    from supermarkets.scrapers import ScraperFactory

    total_price = Decimal('0.00')
    found_count = 0
    error_count = 0

    # Phase 1 : vérifier le cache
    to_scrape = []
    for ingredient in ingredients:
        cached = model_class.objects.filter(
            ingredient=ingredient,
            store_id=STORE_ID,
            last_updated__gte=timezone.now() - CACHE_DURATION
        ).first()

        if cached and cached.product_name and cached.price:
            total_price += Decimal(str(cached.price))
            found_count += 1
        else:
            to_scrape.append(ingredient)

    if not to_scrape:
        logger.info(f"[{scraper_name}] Tous en cache ({found_count}/{len(ingredients)})")
        return total_price, found_count, error_count

    # Phase 2 : scraper les manquants
    logger.info(f"[{scraper_name}] Scraping {len(to_scrape)} produits...")

    try:
        with ScraperFactory.get(scraper_name, headless=True, timeout=20000) as scraper:
            for idx, ingredient in enumerate(to_scrape):
                try:
                    products = scraper.search(ingredient.nom)

                    if not products:
                        logger.warning(f"[{scraper_name}] 0 résultats pour '{ingredient.nom}'")
                        error_count += 1
                        continue

                    best = products[0]
                    match, created = model_class.objects.update_or_create(
                        ingredient=ingredient,
                        store_id=STORE_ID,
                        defaults={
                            'product_name': best.get('product_name', ''),
                            'price': best.get('price'),
                            'is_available': best.get('is_available', True),
                            'product_url': best.get('product_url', ''),
                            'image_url': best.get('image_url', ''),
                            'match_score': 0.8,
                            'last_updated': timezone.now()
                        }
                    )

                    if match.price:
                        total_price += Decimal(str(match.price))
                        found_count += 1

                    action = "Créé" if created else "Mis à jour"
                    logger.info(f"[{scraper_name}] {action}: '{ingredient.nom}' → "
                                f"{best.get('product_name')} {best.get('price')}€")

                    if task and progress_total:
                        task.update_state(state='PROGRESS', meta={
                            'current': progress_offset + found_count + idx,
                            'total': progress_total,
                            'supermarket': scraper_name,
                            'message': f'{scraper_name}: {ingredient.nom}'
                        })

                except Exception as e:
                    error_count += 1
                    logger.error(f"[{scraper_name}] Erreur '{ingredient.nom}': {e}")

    except Exception as e:
        logger.error(f"[{scraper_name}] Erreur navigateur: {e}")

    return total_price, found_count, error_count


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


@shared_task(
    bind=True,
    max_retries=2,
    name='panier.tasks.match_carrefour_products'
)
def match_carrefour_products(self, panier_id, store_id=STORE_ID):
    """Matche les ingrédients d'un panier avec les produits Carrefour."""
    from supermarkets.models import CarrefourProductMatch

    try:
        panier = Panier.objects.get(id=panier_id)
        ing_paniers = _get_ingredient_paniers(panier)

        if not ing_paniers:
            return {'status': 'error', 'message': 'Aucun ingrédient', 'matched': 0, 'total': 0}

        ingredients = [ip.ingredient for ip in ing_paniers]
        _, found, errors = _scrape_supermarket('carrefour', ingredients, CarrefourProductMatch)

        total = len(ingredients)
        rate = (found / total * 100) if total else 0
        logger.info(f"Carrefour panier #{panier_id}: {found}/{total} ({rate:.0f}%)")

        return {
            'status': 'success', 'panier_id': panier_id,
            'matched': found, 'total': total,
            'errors': errors, 'success_rate': rate
        }

    except Panier.DoesNotExist:
        return {'status': 'error', 'message': f'Panier {panier_id} non trouvé'}
    except Exception as e:
        logger.error(f"Erreur Carrefour panier {panier_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        return {'status': 'error', 'message': str(e)}


@shared_task(
    bind=True,
    max_retries=2,
    name='panier.tasks.compare_supermarket_prices'
)
def compare_supermarket_prices(self, panier_id: int, user_id: int,
                               latitude: float, longitude: float):
    """Compare les prix d'un panier entre Carrefour et Aldi."""
    from supermarkets.models import PriceComparison, CarrefourProductMatch, AldiProductMatch

    try:
        panier = Panier.objects.get(id=panier_id)
        user = User.objects.get(id=user_id)
        ing_paniers = _get_ingredient_paniers(panier)

        if not ing_paniers:
            return {'status': 'error', 'message': 'Aucun ingrédient'}

        ingredients = [ip.ingredient for ip in ing_paniers]
        total = len(ingredients)

        self.update_state(state='PROGRESS', meta={
            'current': 0, 'total': total * 2,
            'supermarket': 'initialisation',
            'message': 'Préparation de la comparaison...'
        })

        # Carrefour
        carrefour_total, carrefour_found, _ = _scrape_supermarket(
            'carrefour', ingredients, CarrefourProductMatch,
            task=self, progress_offset=0, progress_total=total * 2
        )

        # Aldi
        aldi_total, aldi_found, _ = _scrape_supermarket(
            'aldi', ingredients, AldiProductMatch,
            task=self, progress_offset=total, progress_total=total * 2
        )

        comparison = PriceComparison.objects.create(
            user=user,
            panier=panier,
            latitude=latitude,
            longitude=longitude,
            carrefour_total=carrefour_total if carrefour_found else None,
            aldi_total=aldi_total if aldi_found else None,
            carrefour_found=carrefour_found,
            aldi_found=aldi_found,
            total_ingredients=total,
        )

        logger.info(
            f"Comparaison: Carrefour={carrefour_total}€ ({carrefour_found}), "
            f"Aldi={aldi_total}€ ({aldi_found}), "
            f"Moins cher: {comparison.cheapest_supermarket}"
        )

        return {
            'status': 'success',
            'comparison_id': comparison.id,
            'carrefour_total': float(carrefour_total),
            'aldi_total': float(aldi_total),
            'carrefour_found': carrefour_found,
            'aldi_found': aldi_found,
            'cheapest': comparison.cheapest_supermarket,
        }

    except Panier.DoesNotExist:
        return {'status': 'error', 'message': f'Panier {panier_id} non trouvé'}
    except Exception as e:
        logger.error(f"Erreur comparaison panier {panier_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        return {'status': 'error', 'message': str(e)}


@shared_task(
    bind=True,
    max_retries=2,
    name='panier.tasks.scrape_ingredient_prices'
)
def scrape_ingredient_prices(self, ingredient_names: list, priority: str = 'normal'):
    """Cache proactif: scrape les prix pour une liste d'ingrédients."""
    from supermarkets.models import CarrefourProductMatch, AldiProductMatch
    from .models import Ingredient

    if not ingredient_names:
        return {'status': 'success', 'scraped': 0}

    logger.info(f"[Cache] Scraping {len(ingredient_names)} ingrédients (priorité: {priority})")

    # Créer les objets Ingredient
    ingredients = []
    for name in ingredient_names:
        ing, _ = Ingredient.objects.get_or_create(
            nom=name.strip(),
            defaults={'quantite': '1', 'unite': ''}
        )
        ingredients.append(ing)

    # Scraper les deux enseignes
    _, carrefour_found, carrefour_errors = _scrape_supermarket(
        'carrefour', ingredients, CarrefourProductMatch
    )
    _, aldi_found, aldi_errors = _scrape_supermarket(
        'aldi', ingredients, AldiProductMatch
    )

    logger.info(
        f"[Cache] Terminé: Carrefour={carrefour_found}, Aldi={aldi_found}, "
        f"erreurs={carrefour_errors + aldi_errors}"
    )

    return {
        'status': 'success',
        'total': len(ingredient_names),
        'carrefour_scraped': carrefour_found,
        'aldi_scraped': aldi_found,
        'errors': carrefour_errors + aldi_errors,
    }


@shared_task(name='panier.tasks.refresh_popular_ingredients')
def refresh_popular_ingredients():
    """Rafraîchit le cache des 50 ingrédients les plus utilisés."""
    from .models import IngredientPanier
    from django.db.models import Count

    popular = (
        IngredientPanier.objects
        .values('ingredient__nom')
        .annotate(usage_count=Count('id'))
        .order_by('-usage_count')[:50]
    )

    names = [item['ingredient__nom'] for item in popular]

    if names:
        logger.info(f"[Cache] Rafraîchissement de {len(names)} ingrédients populaires")
        scrape_ingredient_prices.delay(names, priority='scheduled')

    return {'status': 'success', 'ingredients_queued': len(names)}
