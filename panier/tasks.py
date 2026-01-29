"""
Tâches Celery pour l'application panier.

Ce module contient les tâches asynchrones, notamment l'envoi
de notifications pour les paniers anciens et la comparaison de prix.
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
    logger.info("Celery fonctionne correctement!")
    return "Celery is working!"


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    name='panier.tasks.match_carrefour_products'
)
def match_carrefour_products(self, panier_id, store_id='scraping'):
    """
    Tâche Celery pour matcher les ingrédients d'un panier avec les produits Carrefour.

    Optimisations:
    - Réutilise le même navigateur Playwright pour tous les ingrédients (gain de ~3-5s par ingrédient)
    - Cache 24h pour éviter de rescraper les mêmes produits
    - Timeout réduit à 20s par recherche

    Args:
        panier_id: ID du panier
        store_id: ID du magasin Carrefour (par défaut 'scraping')

    Returns:
        dict: Statistiques de matching (matched, total, errors)
    """
    from .models import Ingredient, IngredientPanier
    from supermarkets.models import CarrefourProductMatch
    from .carrefour_scraper import CarrefourScraper

    logger.info(f"Démarrage matching Carrefour pour panier #{panier_id}")

    try:
        # Récupérer le panier
        panier = Panier.objects.get(id=panier_id)

        # Récupérer toutes les courses du panier avec leurs ingrédients
        courses_with_ingredients = panier.courses.filter(ingredient__isnull=False).exclude(ingredient='')

        if not courses_with_ingredients:
            logger.warning(f"Panier {panier_id} ne contient aucun ingrédient")
            return {
                'status': 'error',
                'message': 'Panier ne contient aucun ingrédient',
                'matched': 0,
                'total': 0
            }

        # Convertir les courses en objets Ingredient et IngredientPanier
        ingredient_paniers = []
        for course in courses_with_ingredients:
            ingredient_lines = [line.strip() for line in course.ingredient.split('\n') if line.strip()]

            for ingredient_text in ingredient_lines:
                ingredient, _ = Ingredient.objects.get_or_create(
                    nom=ingredient_text,
                    defaults={'quantite': '1', 'unite': ''}
                )

                ing_panier, _ = IngredientPanier.objects.get_or_create(
                    panier=panier,
                    ingredient=ingredient,
                    defaults={'quantite': 1}
                )
                ingredient_paniers.append(ing_panier)

        total_ingredients = len(ingredient_paniers)
        logger.info(f"{total_ingredients} ingrédients à matcher pour le panier #{panier_id}")

        # Matcher chaque ingrédient
        matched_count = 0
        error_count = 0

        # PHASE 1: Vérifier le cache AVANT de démarrer le navigateur
        cache_duration = timedelta(hours=24)
        ingredients_to_scrape = []

        for ing_panier in ingredient_paniers:
            ingredient = ing_panier.ingredient
            existing_match = CarrefourProductMatch.objects.filter(
                ingredient=ingredient,
                store_id=store_id,
                last_updated__gte=timezone.now() - cache_duration
            ).first()

            if existing_match and existing_match.product_name:
                logger.info(f"Cache trouvé pour '{ingredient.nom}': {existing_match.product_name} - {existing_match.price}EUR")
                matched_count += 1
            else:
                ingredients_to_scrape.append(ing_panier)

        # PHASE 2: Scraper uniquement les ingrédients non cachés
        if ingredients_to_scrape:
            logger.info(f"Démarrage du navigateur Playwright Carrefour pour {len(ingredients_to_scrape)} ingrédients...")
            with CarrefourScraper(headless=True, timeout=20000) as scraper:
                for index, ing_panier in enumerate(ingredients_to_scrape, 1):
                    try:
                        ingredient = ing_panier.ingredient
                        logger.info(f"[{index}/{len(ingredients_to_scrape)}] Recherche Carrefour de '{ingredient.nom}'...")

                        # Scraper les produits Carrefour (en réutilisant le même navigateur)
                        products = scraper.search_product(ingredient.nom)

                        if not products:
                            logger.warning(f"Aucun produit Carrefour trouvé pour '{ingredient.nom}'")
                            error_count += 1
                            continue

                        # Prendre le premier produit (le plus pertinent)
                        best_product = products[0]

                        # Créer ou mettre à jour le match
                        match, created = CarrefourProductMatch.objects.update_or_create(
                            ingredient=ingredient,
                            store_id=store_id,
                            defaults={
                                'product_name': best_product.get('name', ''),
                                'price': best_product.get('price'),
                                'is_available': best_product.get('is_available', True),
                                'product_url': best_product.get('url', ''),
                                'match_score': 0.8,
                                'last_updated': timezone.now()
                            }
                        )

                        matched_count += 1
                        action = "Créé" if created else "Mis à jour"
                        logger.info(
                            f"{action} match Carrefour pour '{ingredient.nom}': "
                            f"{best_product.get('name')} - {best_product.get('price')}EUR"
                        )

                    except Exception as e:
                        error_count += 1
                        logger.error(f"Erreur Carrefour pour '{ingredient.nom}': {e}")
                        continue
        else:
            logger.info("Tous les ingrédients étaient déjà en cache, pas besoin de scraper")

        # Résultats finaux
        success_rate = (matched_count / total_ingredients * 100) if total_ingredients > 0 else 0

        logger.info(
            f"Matching Carrefour terminé pour panier #{panier_id}: "
            f"{matched_count}/{total_ingredients} matchés ({success_rate:.1f}%), "
            f"{error_count} erreurs"
        )

        return {
            'status': 'success',
            'panier_id': panier_id,
            'matched': matched_count,
            'total': total_ingredients,
            'errors': error_count,
            'success_rate': success_rate
        }

    except Panier.DoesNotExist:
        logger.error(f"Panier {panier_id} non trouvé")
        return {
            'status': 'error',
            'message': f'Panier {panier_id} non trouvé'
        }

    except Exception as e:
        logger.error(f"Erreur globale Carrefour pour panier {panier_id}: {e}")
        # Retry avec backoff exponentiel
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        else:
            return {
                'status': 'error',
                'message': str(e),
                'matched': 0,
                'total': 0
            }


@shared_task(bind=True, max_retries=2, name='panier.tasks.compare_supermarket_prices')
def compare_supermarket_prices(self, panier_id: int, user_id: int, latitude: float, longitude: float):
    """
    Tâche Celery pour comparer les prix d'un panier sur Carrefour et Auchan.

    Flow:
    1. Récupère les ingrédients du panier
    2. Lance le matching Carrefour et Auchan (cache 24h)
    3. Calcule les totaux par supermarché
    4. Crée un PriceComparison avec les résultats

    Args:
        panier_id: ID du panier à comparer
        user_id: ID de l'utilisateur
        latitude: Latitude de l'utilisateur
        longitude: Longitude de l'utilisateur

    Returns:
        dict avec status, comparison_id et statistiques
    """
    from supermarkets.models import PriceComparison, CarrefourProductMatch, AuchanProductMatch
    from .models import Ingredient, IngredientPanier
    from .carrefour_scraper import CarrefourScraper
    from .auchan_scraper import AuchanScraper
    from decimal import Decimal

    try:
        logger.info(f"Démarrage comparaison de prix pour panier #{panier_id}")

        # Récupérer le panier et l'utilisateur
        panier = Panier.objects.get(id=panier_id)
        user = User.objects.get(id=user_id)

        # Récupérer/créer les ingrédients du panier
        courses_with_ingredients = panier.courses.filter(ingredient__isnull=False).exclude(ingredient='')

        if not courses_with_ingredients:
            logger.warning(f"Panier {panier_id} ne contient aucun ingrédient")
            return {
                'status': 'error',
                'message': 'Panier ne contient aucun ingrédient'
            }

        # Convertir les courses en IngredientPanier
        ingredient_paniers = []
        for course in courses_with_ingredients:
            ingredient_lines = [line.strip() for line in course.ingredient.split('\n') if line.strip()]
            for ingredient_text in ingredient_lines:
                ingredient, _ = Ingredient.objects.get_or_create(
                    nom=ingredient_text,
                    defaults={'quantite': '1', 'unite': ''}
                )
                ing_panier, _ = IngredientPanier.objects.get_or_create(
                    panier=panier,
                    ingredient=ingredient,
                    defaults={'quantite': 1}
                )
                ingredient_paniers.append(ing_panier)

        total_ingredients = len(ingredient_paniers)
        logger.info(f"{total_ingredients} ingrédients à comparer")

        # Progress update
        self.update_state(state='PROGRESS', meta={
            'current': 0,
            'total': total_ingredients * 2,
            'supermarket': 'initialisation',
            'message': 'Préparation de la comparaison...'
        })

        # Phase 1: Carrefour
        carrefour_total = Decimal('0.00')
        carrefour_found = 0
        cache_duration = timedelta(hours=24)
        store_id = 'scraping'

        # Vérifier le cache Carrefour
        carrefour_to_scrape = []
        for ing_panier in ingredient_paniers:
            ingredient = ing_panier.ingredient
            existing_match = CarrefourProductMatch.objects.filter(
                ingredient=ingredient,
                store_id=store_id,
                last_updated__gte=timezone.now() - cache_duration
            ).first()

            if existing_match and existing_match.product_name and existing_match.price:
                carrefour_total += Decimal(str(existing_match.price))
                carrefour_found += 1
            else:
                carrefour_to_scrape.append(ing_panier)

        # Scraper Carrefour si nécessaire
        if carrefour_to_scrape:
            logger.info(f"Scraping {len(carrefour_to_scrape)} produits Carrefour...")
            self.update_state(state='PROGRESS', meta={
                'current': carrefour_found,
                'total': total_ingredients * 2,
                'supermarket': 'carrefour',
                'message': f'Recherche Carrefour ({len(carrefour_to_scrape)} produits)...'
            })

            try:
                with CarrefourScraper(headless=True, timeout=20000) as scraper:
                    for idx, ing_panier in enumerate(carrefour_to_scrape):
                        try:
                            ingredient = ing_panier.ingredient
                            products = scraper.search_product(ingredient.nom)

                            if products:
                                best = products[0]
                                match, _ = CarrefourProductMatch.objects.update_or_create(
                                    ingredient=ingredient,
                                    store_id=store_id,
                                    defaults={
                                        'product_name': best.get('name', ''),
                                        'price': best.get('price'),
                                        'is_available': best.get('is_available', True),
                                        'product_url': best.get('url', ''),
                                        'match_score': 0.8,
                                        'last_updated': timezone.now()
                                    }
                                )
                                if match.price:
                                    carrefour_total += Decimal(str(match.price))
                                    carrefour_found += 1

                            self.update_state(state='PROGRESS', meta={
                                'current': carrefour_found + idx,
                                'total': total_ingredients * 2,
                                'supermarket': 'carrefour',
                                'message': f'Carrefour: {ingredient.nom}'
                            })
                        except Exception as e:
                            logger.error(f"Erreur Carrefour pour {ingredient.nom}: {e}")
            except Exception as e:
                logger.error(f"Erreur scraper Carrefour: {e}")

        # Phase 2: Auchan
        auchan_total = Decimal('0.00')
        auchan_found = 0

        # Vérifier le cache Auchan
        auchan_to_scrape = []
        for ing_panier in ingredient_paniers:
            ingredient = ing_panier.ingredient
            existing_match = AuchanProductMatch.objects.filter(
                ingredient=ingredient,
                store_id=store_id,
                last_updated__gte=timezone.now() - cache_duration
            ).first()

            if existing_match and existing_match.product_name and existing_match.price:
                auchan_total += Decimal(str(existing_match.price))
                auchan_found += 1
            else:
                auchan_to_scrape.append(ing_panier)

        # Scraper Auchan si nécessaire
        if auchan_to_scrape:
            logger.info(f"Scraping {len(auchan_to_scrape)} produits Auchan...")
            self.update_state(state='PROGRESS', meta={
                'current': total_ingredients + auchan_found,
                'total': total_ingredients * 2,
                'supermarket': 'auchan',
                'message': f'Recherche Auchan ({len(auchan_to_scrape)} produits)...'
            })

            try:
                with AuchanScraper(headless=True, timeout=20000) as scraper:
                    for idx, ing_panier in enumerate(auchan_to_scrape):
                        try:
                            ingredient = ing_panier.ingredient
                            products = scraper.search_product(ingredient.nom)

                            if products:
                                best = products[0]
                                match, _ = AuchanProductMatch.objects.update_or_create(
                                    ingredient=ingredient,
                                    store_id=store_id,
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
                                    auchan_total += Decimal(str(match.price))
                                    auchan_found += 1

                            self.update_state(state='PROGRESS', meta={
                                'current': total_ingredients + auchan_found + idx,
                                'total': total_ingredients * 2,
                                'supermarket': 'auchan',
                                'message': f'Auchan: {ingredient.nom}'
                            })
                        except Exception as e:
                            logger.error(f"Erreur Auchan pour {ingredient.nom}: {e}")
            except Exception as e:
                logger.error(f"Erreur scraper Auchan: {e}")

        # Créer la comparaison
        comparison = PriceComparison.objects.create(
            user=user,
            panier=panier,
            latitude=latitude,
            longitude=longitude,
            carrefour_total=carrefour_total if carrefour_found > 0 else None,
            auchan_total=auchan_total if auchan_found > 0 else None,
            carrefour_found=carrefour_found,
            auchan_found=auchan_found,
            total_ingredients=total_ingredients,
        )

        logger.info(
            f"Comparaison terminée: Carrefour={carrefour_total}EUR ({carrefour_found} produits), "
            f"Auchan={auchan_total}EUR ({auchan_found} produits), "
            f"Moins cher: {comparison.cheapest_supermarket}"
        )

        return {
            'status': 'success',
            'comparison_id': comparison.id,
            'carrefour_total': float(carrefour_total),
            'auchan_total': float(auchan_total),
            'carrefour_found': carrefour_found,
            'auchan_found': auchan_found,
            'cheapest': comparison.cheapest_supermarket,
        }

    except Panier.DoesNotExist:
        logger.error(f"Panier {panier_id} non trouvé")
        return {'status': 'error', 'message': f'Panier {panier_id} non trouvé'}

    except Exception as e:
        logger.error(f"Erreur comparaison panier {panier_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True, max_retries=2, name='panier.tasks.scrape_ingredient_prices')
def scrape_ingredient_prices(self, ingredient_names: list, priority: str = 'normal'):
    """
    Tâche Celery pour scraper les prix d'ingrédients spécifiques (Cache Proactif).

    Cette tâche est déclenchée:
    - Par un signal Django quand une Course est créée/modifiée
    - Par Celery Beat quotidiennement pour rafraîchir les ingrédients populaires

    Args:
        ingredient_names: Liste des noms d'ingrédients à scraper
        priority: 'high' (signal) ou 'normal' (scheduled)

    Returns:
        dict: Statistiques de scraping
    """
    from supermarkets.models import CarrefourProductMatch, AuchanProductMatch
    from .models import Ingredient
    from .carrefour_scraper import CarrefourScraper
    from .auchan_scraper import AuchanScraper

    if not ingredient_names:
        return {'status': 'success', 'scraped': 0, 'message': 'Aucun ingrédient à scraper'}

    logger.info(f"[Cache Proactif] Démarrage scraping {len(ingredient_names)} ingrédients (priorité: {priority})")

    cache_duration = timedelta(hours=24)
    store_id = 'scraping'
    stats = {
        'total': len(ingredient_names),
        'carrefour_scraped': 0,
        'auchan_scraped': 0,
        'already_cached': 0,
        'errors': 0
    }

    # Filtrer les ingrédients déjà en cache (moins de 24h)
    ingredients_to_scrape = []
    for name in ingredient_names:
        ingredient, _ = Ingredient.objects.get_or_create(
            nom=name.strip(),
            defaults={'quantite': '1', 'unite': ''}
        )

        carrefour_cached = CarrefourProductMatch.objects.filter(
            ingredient=ingredient,
            store_id=store_id,
            last_updated__gte=timezone.now() - cache_duration
        ).exists()

        auchan_cached = AuchanProductMatch.objects.filter(
            ingredient=ingredient,
            store_id=store_id,
            last_updated__gte=timezone.now() - cache_duration
        ).exists()

        if carrefour_cached and auchan_cached:
            stats['already_cached'] += 1
            logger.debug(f"[Cache Proactif] '{name}' déjà en cache, skip")
        else:
            ingredients_to_scrape.append({
                'name': name,
                'ingredient': ingredient,
                'need_carrefour': not carrefour_cached,
                'need_auchan': not auchan_cached
            })

    if not ingredients_to_scrape:
        logger.info(f"[Cache Proactif] Tous les {stats['total']} ingrédients sont déjà en cache")
        return {'status': 'success', **stats}

    logger.info(f"[Cache Proactif] {len(ingredients_to_scrape)} ingrédients à scraper")

    # Scraping Carrefour
    carrefour_to_scrape = [i for i in ingredients_to_scrape if i['need_carrefour']]
    if carrefour_to_scrape:
        logger.info(f"[Cache Proactif] Scraping Carrefour ({len(carrefour_to_scrape)} produits)...")
        try:
            with CarrefourScraper(headless=True, timeout=20000) as scraper:
                for item in carrefour_to_scrape:
                    try:
                        products = scraper.search_product(item['name'])
                        if products:
                            best = products[0]
                            CarrefourProductMatch.objects.update_or_create(
                                ingredient=item['ingredient'],
                                store_id=store_id,
                                defaults={
                                    'product_name': best.get('name', ''),
                                    'price': best.get('price'),
                                    'is_available': best.get('is_available', True),
                                    'product_url': best.get('url', ''),
                                    'match_score': 0.8,
                                    'last_updated': timezone.now()
                                }
                            )
                            stats['carrefour_scraped'] += 1
                            logger.debug(f"[Cache Proactif] Carrefour '{item['name']}': {best.get('price')}€")
                    except Exception as e:
                        logger.error(f"[Cache Proactif] Erreur Carrefour '{item['name']}': {e}")
                        stats['errors'] += 1
        except Exception as e:
            logger.error(f"[Cache Proactif] Erreur scraper Carrefour: {e}")

    # Scraping Auchan
    auchan_to_scrape = [i for i in ingredients_to_scrape if i['need_auchan']]
    if auchan_to_scrape:
        logger.info(f"[Cache Proactif] Scraping Auchan ({len(auchan_to_scrape)} produits)...")
        try:
            with AuchanScraper(headless=True, timeout=20000) as scraper:
                for item in auchan_to_scrape:
                    try:
                        products = scraper.search_product(item['name'])
                        if products:
                            best = products[0]
                            AuchanProductMatch.objects.update_or_create(
                                ingredient=item['ingredient'],
                                store_id=store_id,
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
                            stats['auchan_scraped'] += 1
                            logger.debug(f"[Cache Proactif] Auchan '{item['name']}': {best.get('price')}€")
                    except Exception as e:
                        logger.error(f"[Cache Proactif] Erreur Auchan '{item['name']}': {e}")
                        stats['errors'] += 1
        except Exception as e:
            logger.error(f"[Cache Proactif] Erreur scraper Auchan: {e}")

    logger.info(
        f"[Cache Proactif] Terminé: {stats['carrefour_scraped']} Carrefour, "
        f"{stats['auchan_scraped']} Auchan, {stats['already_cached']} en cache, "
        f"{stats['errors']} erreurs"
    )

    return {'status': 'success', **stats}


@shared_task(name='panier.tasks.refresh_popular_ingredients')
def refresh_popular_ingredients():
    """
    Tâche planifiée quotidienne pour rafraîchir le cache des ingrédients populaires.

    Sélectionne les ingrédients les plus utilisés dans les paniers récents
    et lance leur scraping proactif.
    """
    from .models import IngredientPanier
    from django.db.models import Count

    logger.info("[Cache Proactif] Démarrage rafraîchissement des ingrédients populaires")

    # Récupérer les 50 ingrédients les plus utilisés
    popular_ingredients = (
        IngredientPanier.objects
        .values('ingredient__nom')
        .annotate(usage_count=Count('id'))
        .order_by('-usage_count')[:50]
    )

    ingredient_names = [item['ingredient__nom'] for item in popular_ingredients]

    if ingredient_names:
        logger.info(f"[Cache Proactif] Rafraîchissement de {len(ingredient_names)} ingrédients populaires")
        # Lancer le scraping en background
        scrape_ingredient_prices.delay(ingredient_names, priority='scheduled')
    else:
        logger.info("[Cache Proactif] Aucun ingrédient populaire à rafraîchir")

    return {'status': 'success', 'ingredients_queued': len(ingredient_names)}


@shared_task(bind=True, max_retries=3, name='panier.tasks.match_auchan_products')
def match_auchan_products(self, panier_id: int, store_id: str = 'scraping'):
    """
    Tâche Celery pour matcher les ingrédients d'un panier avec les produits Auchan Drive.

    Architecture:
    - Phase 1 (sync): Vérifie le cache (24h) pour éviter les requêtes inutiles
    - Phase 2 (async): Scrape uniquement les produits non cachés avec un seul navigateur
    - Retry automatique en cas d'erreur (3 fois max avec backoff exponentiel)

    Args:
        panier_id: ID du panier à traiter
        store_id: ID du magasin Auchan cible (ou 'scraping' pour recherche générale)

    Returns:
        Dictionnaire avec les statistiques de matching
    """
    from supermarkets.models import AuchanProductMatch
    from .auchan_scraper import AuchanScraper

    try:
        logger.info(f"Démarrage matching Auchan pour panier #{panier_id} (magasin: {store_id})")

        # Récupérer le panier
        panier = Panier.objects.get(id=panier_id)
        ingredient_paniers = panier.ingredient_paniers.all()
        total_ingredients = ingredient_paniers.count()

        if total_ingredients == 0:
            logger.warning(f"Panier {panier_id} vide, aucun ingrédient à matcher")
            return {'status': 'success', 'matched': 0, 'total': 0}

        matched_count = 0
        error_count = 0

        # PHASE 1: Vérifier le cache AVANT de démarrer le navigateur
        cache_duration = timedelta(hours=24)
        ingredients_to_scrape = []

        for ing_panier in ingredient_paniers:
            ingredient = ing_panier.ingredient
            existing_match = AuchanProductMatch.objects.filter(
                ingredient=ingredient,
                store_id=store_id,
                last_updated__gte=timezone.now() - cache_duration
            ).first()

            if existing_match and existing_match.product_name:
                logger.info(f"Cache trouvé pour '{ingredient.nom}': {existing_match.product_name} - {existing_match.price}EUR")
                matched_count += 1
            else:
                ingredients_to_scrape.append(ing_panier)

        # PHASE 2: Scraper uniquement les ingrédients non cachés
        if ingredients_to_scrape:
            logger.info(f"Démarrage du navigateur Playwright Auchan pour {len(ingredients_to_scrape)} ingrédients...")
            with AuchanScraper(headless=True, timeout=20000) as scraper:
                for index, ing_panier in enumerate(ingredients_to_scrape, 1):
                    try:
                        ingredient = ing_panier.ingredient
                        logger.info(f"[{index}/{len(ingredients_to_scrape)}] Recherche Auchan de '{ingredient.nom}'...")

                        # Scraper les produits Auchan
                        products = scraper.search_product(ingredient.nom)

                        if not products:
                            logger.warning(f"Aucun produit Auchan trouvé pour '{ingredient.nom}'")
                            error_count += 1
                            continue

                        # Prendre le premier produit (le plus pertinent)
                        best_product = products[0]

                        # Créer ou mettre à jour le match
                        match, created = AuchanProductMatch.objects.update_or_create(
                            ingredient=ingredient,
                            store_id=store_id,
                            defaults={
                                'product_name': best_product.get('product_name', ''),
                                'price': best_product.get('price'),
                                'is_available': best_product.get('is_available', True),
                                'product_url': best_product.get('product_url', ''),
                                'image_url': best_product.get('image_url', ''),
                                'match_score': 0.8,
                                'last_updated': timezone.now()
                            }
                        )

                        matched_count += 1
                        action = "Créé" if created else "Mis à jour"
                        logger.info(
                            f"{action} match Auchan pour '{ingredient.nom}': "
                            f"{best_product.get('product_name')} - {best_product.get('price')}EUR"
                        )

                    except Exception as e:
                        error_count += 1
                        logger.error(f"Erreur Auchan pour '{ingredient.nom}': {e}")
                        continue
        else:
            logger.info("Tous les ingrédients étaient déjà en cache")

        # Résultats finaux
        success_rate = (matched_count / total_ingredients * 100) if total_ingredients > 0 else 0

        logger.info(
            f"Matching Auchan terminé pour panier #{panier_id}: "
            f"{matched_count}/{total_ingredients} matchés ({success_rate:.1f}%), "
            f"{error_count} erreurs"
        )

        return {
            'status': 'success',
            'panier_id': panier_id,
            'matched': matched_count,
            'total': total_ingredients,
            'errors': error_count,
            'success_rate': success_rate
        }

    except Panier.DoesNotExist:
        logger.error(f"Panier {panier_id} non trouvé")
        return {
            'status': 'error',
            'message': f'Panier {panier_id} non trouvé'
        }

    except Exception as e:
        logger.error(f"Erreur globale Auchan pour panier {panier_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        else:
            return {
                'status': 'error',
                'message': str(e),
                'matched': 0,
                'total': 0
            }
