"""
Vues pour la comparaison de prix entre supermarchés.

Architecture "Cache Proactif":
- Les prix sont scrapés en background quand les courses sont créées/modifiées
- La comparaison lit directement le cache pour des résultats instantanés
- Si des prix manquent, ils sont affichés comme "non disponibles" et un scraping est lancé en background

Flow utilisateur:
1. compare_prices - Lecture cache directe + résultats instantanés
2. comparison_results - Résultats avec tableau comparatif (utilisé pour les comparaisons historiques)
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils import timezone

from ..models import Panier, Ingredient, IngredientPanier

logger = logging.getLogger(__name__)


@login_required
def compare_prices(request, panier_id):
    """
    Comparaison de prix instantanée via lecture du cache.

    GET: Affiche la page avec géolocalisation
    POST: Lit le cache, crée la comparaison et affiche les résultats immédiatement
    """
    from supermarkets.models import PriceComparison, CarrefourProductMatch, AuchanProductMatch

    panier = get_object_or_404(Panier, id=panier_id)

    # Vérifier l'accès au panier
    user_has_family = bool(request.user.last_name)
    is_same_family = (panier.user.last_name.lower() == request.user.last_name.lower()
                      if user_has_family and panier.user.last_name else False)
    is_own_basket = panier.user == request.user

    if not (is_same_family or is_own_basket):
        messages.error(request, "Vous n'avez pas accès à ce panier.")
        return redirect('liste_paniers')

    # Vérifier que le panier contient des ingrédients
    courses_count = panier.courses.count()
    has_ingredients = any(
        course.ingredient and course.ingredient.strip()
        for course in panier.courses.all()
    )

    if courses_count == 0 or not has_ingredients:
        messages.warning(
            request,
            "Ce panier ne contient aucun ingrédient. "
            "Veuillez d'abord ajouter des ingrédients aux courses."
        )
        return redirect('detail_panier', panier_id=panier.id)

    # Récupérer la localisation
    user_location = None
    if 'temp_location' in request.session:
        temp_loc = request.session['temp_location']
        user_location = {
            'latitude': temp_loc['latitude'],
            'longitude': temp_loc['longitude'],
            'address': temp_loc.get('address', '')
        }
    elif request.user.location:
        user_location = {
            'latitude': request.user.location.y,
            'longitude': request.user.location.x,
            'address': request.user.address or ''
        }

    # POST: Lecture cache directe et résultats instantanés
    if request.method == 'POST':
        if not user_location:
            messages.error(request, "Veuillez d'abord renseigner votre localisation.")
            return redirect('compare_prices', panier_id=panier.id)

        # Extraire et créer les ingrédients
        ingredient_paniers = []
        for course in panier.courses.filter(ingredient__isnull=False).exclude(ingredient=''):
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

        if total_ingredients == 0:
            messages.warning(request, "Aucun ingrédient trouvé dans ce panier.")
            return redirect('detail_panier', panier_id=panier.id)

        # Lecture du cache (24h)
        cache_duration = timedelta(hours=24)
        store_id = 'scraping'

        carrefour_total = Decimal('0.00')
        carrefour_found = 0
        auchan_total = Decimal('0.00')
        auchan_found = 0
        missing_ingredients = []

        comparison_data = []

        for ing_panier in ingredient_paniers:
            ingredient = ing_panier.ingredient

            # Chercher dans le cache Carrefour
            carrefour_match = CarrefourProductMatch.objects.filter(
                ingredient=ingredient,
                store_id=store_id,
                last_updated__gte=timezone.now() - cache_duration
            ).first()

            # Chercher dans le cache Auchan
            auchan_match = AuchanProductMatch.objects.filter(
                ingredient=ingredient,
                store_id=store_id,
                last_updated__gte=timezone.now() - cache_duration
            ).first()

            carrefour_price = None
            auchan_price = None

            if carrefour_match and carrefour_match.price:
                carrefour_price = Decimal(str(carrefour_match.price))
                carrefour_total += carrefour_price
                carrefour_found += 1

            if auchan_match and auchan_match.price:
                auchan_price = Decimal(str(auchan_match.price))
                auchan_total += auchan_price
                auchan_found += 1

            # Tracker les ingrédients manquants
            if not carrefour_match or not auchan_match:
                missing_ingredients.append(ingredient.nom)

            # Déterminer le moins cher
            cheapest = None
            if carrefour_price and auchan_price:
                cheapest = 'carrefour' if carrefour_price <= auchan_price else 'auchan'
            elif carrefour_price:
                cheapest = 'carrefour'
            elif auchan_price:
                cheapest = 'auchan'

            comparison_data.append({
                'ingredient': ingredient,
                'carrefour': {
                    'match': carrefour_match,
                    'price': carrefour_price,
                    'name': carrefour_match.product_name if carrefour_match else None,
                },
                'auchan': {
                    'match': auchan_match,
                    'price': auchan_price,
                    'name': auchan_match.product_name if auchan_match else None,
                },
                'cheapest': cheapest,
            })

        # Si des ingrédients manquent, lancer le scraping en background
        if missing_ingredients:
            logger.info(f"[Cache Proactif] {len(missing_ingredients)} ingrédients manquants, lancement scraping background")
            try:
                from ..tasks import scrape_ingredient_prices
                scrape_ingredient_prices.delay(missing_ingredients, priority='high')
            except Exception as e:
                logger.error(f"Erreur lancement scraping background: {e}")

        # Créer la comparaison
        comparison = PriceComparison.objects.create(
            user=request.user,
            panier=panier,
            latitude=user_location['latitude'],
            longitude=user_location['longitude'],
            carrefour_total=carrefour_total if carrefour_found > 0 else None,
            auchan_total=auchan_total if auchan_found > 0 else None,
            carrefour_found=carrefour_found,
            auchan_found=auchan_found,
            total_ingredients=total_ingredients,
        )

        logger.info(
            f"[Cache Proactif] Comparaison instantanée créée: "
            f"Carrefour={carrefour_total}EUR ({carrefour_found}/{total_ingredients}), "
            f"Auchan={auchan_total}EUR ({auchan_found}/{total_ingredients})"
        )

        # Calculer les produits manquants par supermarché
        missing_carrefour = [d['ingredient'].nom for d in comparison_data if not d['carrefour']['match']]
        missing_auchan = [d['ingredient'].nom for d in comparison_data if not d['auchan']['match']]

        # Afficher directement les résultats
        context = {
            'panier': panier,
            'comparison': comparison,
            'comparison_data': comparison_data,
            'missing_carrefour': missing_carrefour,
            'missing_auchan': missing_auchan,
            'savings': comparison.savings,
            'is_instant': True,  # Indique que c'est une comparaison instantanée
            'missing_count': len(missing_ingredients),
        }

        return render(request, 'supermarkets/comparison_results.html', context)

    # GET: Afficher la page de démarrage
    nearby_stores = {'carrefour': [], 'auchan': []}

    if user_location:
        try:
            from authentication.utils import OverpassAPI
            overpass = OverpassAPI()

            nearby_stores['carrefour'] = overpass.find_carrefour_stores(
                latitude=user_location['latitude'],
                longitude=user_location['longitude'],
                radius=5000
            )[:5]

            nearby_stores['auchan'] = overpass.find_auchan_stores(
                latitude=user_location['latitude'],
                longitude=user_location['longitude'],
                radius=5000
            )[:5]
        except Exception as e:
            logger.error(f"Erreur récupération magasins: {e}")

    # Calculer la couverture du cache pour afficher un indicateur
    cache_coverage = _get_cache_coverage(panier)

    context = {
        'panier': panier,
        'user_location': user_location,
        'nearby_stores': nearby_stores,
        'ingredients_count': sum(
            len([line for line in c.ingredient.split('\n') if line.strip()])
            for c in panier.courses.all() if c.ingredient
        ),
        'cache_coverage': cache_coverage,
    }

    return render(request, 'supermarkets/compare_prices.html', context)


def _get_cache_coverage(panier):
    """
    Calcule le pourcentage de couverture du cache pour un panier.

    Returns:
        dict: {carrefour: %, auchan: %, total_ingredients: int}
    """
    from supermarkets.models import CarrefourProductMatch, AuchanProductMatch

    cache_duration = timedelta(hours=24)
    store_id = 'scraping'

    ingredient_names = []
    for course in panier.courses.filter(ingredient__isnull=False).exclude(ingredient=''):
        ingredient_lines = [line.strip() for line in course.ingredient.split('\n') if line.strip()]
        ingredient_names.extend(ingredient_lines)

    total = len(ingredient_names)
    if total == 0:
        return {'carrefour': 0, 'auchan': 0, 'total_ingredients': 0}

    carrefour_cached = 0
    auchan_cached = 0

    for name in ingredient_names:
        try:
            ingredient = Ingredient.objects.get(nom=name)

            if CarrefourProductMatch.objects.filter(
                ingredient=ingredient,
                store_id=store_id,
                last_updated__gte=timezone.now() - cache_duration
            ).exists():
                carrefour_cached += 1

            if AuchanProductMatch.objects.filter(
                ingredient=ingredient,
                store_id=store_id,
                last_updated__gte=timezone.now() - cache_duration
            ).exists():
                auchan_cached += 1
        except Ingredient.DoesNotExist:
            pass

    return {
        'carrefour': int((carrefour_cached / total) * 100) if total > 0 else 0,
        'auchan': int((auchan_cached / total) * 100) if total > 0 else 0,
        'total_ingredients': total,
    }


@login_required
def comparison_progress(request, panier_id, task_id):
    """
    Page de progression de la comparaison avec auto-refresh.

    Affiche l'état de la tâche Celery et redirige vers les résultats
    une fois terminée.
    """
    from celery.result import AsyncResult

    panier = get_object_or_404(Panier, id=panier_id)

    # Vérifier l'accès
    if panier.user != request.user:
        user_has_family = bool(request.user.last_name)
        is_same_family = (panier.user.last_name.lower() == request.user.last_name.lower()
                          if user_has_family and panier.user.last_name else False)
        if not is_same_family:
            messages.error(request, "Vous n'avez pas accès à ce panier.")
            return redirect('liste_paniers')

    # Vérifier l'état de la tâche
    task_result = AsyncResult(task_id)

    context = {
        'panier': panier,
        'task_id': task_id,
        'task_state': task_result.state,
    }

    # Si terminée avec succès, récupérer les résultats
    if task_result.ready() and task_result.successful():
        result = task_result.result
        if result and result.get('status') == 'success':
            comparison_id = result.get('comparison_id')
            if comparison_id:
                # Nettoyer la session
                if f'comparison_task_{panier_id}' in request.session:
                    del request.session[f'comparison_task_{panier_id}']
                return redirect('comparison_results', panier_id=panier.id, comparison_id=comparison_id)

    # Si échec
    if task_result.failed():
        messages.error(request, "La comparaison a échoué. Veuillez réessayer.")
        return redirect('compare_prices', panier_id=panier.id)

    return render(request, 'supermarkets/comparison_progress.html', context)


@login_required
@require_GET
def comparison_status_api(request, task_id):
    """
    API JSON pour le polling de l'état de la tâche.

    Retourne:
    - state: PENDING, STARTED, PROGRESS, SUCCESS, FAILURE
    - progress: {current, total, supermarket} si en cours
    - result: {comparison_id} si terminé
    """
    from celery.result import AsyncResult

    task_result = AsyncResult(task_id)

    response = {
        'state': task_result.state,
    }

    if task_result.state == 'PROGRESS':
        response['progress'] = task_result.info
    elif task_result.ready():
        if task_result.successful():
            result = task_result.result
            response['result'] = result
        else:
            response['error'] = str(task_result.info)

    return JsonResponse(response)


@login_required
def comparison_results(request, panier_id, comparison_id):
    """
    Page des résultats de la comparaison.

    Affiche:
    - Cartes résumé par supermarché avec totaux
    - Badge sur le moins cher
    - Tableau comparatif par ingrédient
    - Produits non trouvés
    """
    from supermarkets.models import PriceComparison, CarrefourProductMatch, AuchanProductMatch

    panier = get_object_or_404(Panier, id=panier_id)
    comparison = get_object_or_404(PriceComparison, id=comparison_id, panier=panier)

    # Vérifier l'accès
    if comparison.user != request.user:
        messages.error(request, "Vous n'avez pas accès à cette comparaison.")
        return redirect('liste_paniers')

    # Récupérer les ingrédients et leurs matches
    ingredient_paniers = panier.ingredient_paniers.select_related('ingredient').all()

    comparison_data = []
    missing_carrefour = []
    missing_auchan = []

    for ing_panier in ingredient_paniers:
        ingredient = ing_panier.ingredient

        # Chercher les matches
        carrefour_match = CarrefourProductMatch.objects.filter(
            ingredient=ingredient,
            store_id='scraping'
        ).first()

        auchan_match = AuchanProductMatch.objects.filter(
            ingredient=ingredient,
            store_id='scraping'
        ).first()

        carrefour_price = carrefour_match.price if carrefour_match and carrefour_match.price else None
        auchan_price = auchan_match.price if auchan_match and auchan_match.price else None

        # Déterminer le moins cher pour cet ingrédient
        cheapest = None
        if carrefour_price and auchan_price:
            cheapest = 'carrefour' if carrefour_price <= auchan_price else 'auchan'
        elif carrefour_price:
            cheapest = 'carrefour'
        elif auchan_price:
            cheapest = 'auchan'

        comparison_data.append({
            'ingredient': ingredient,
            'carrefour': {
                'match': carrefour_match,
                'price': carrefour_price,
                'name': carrefour_match.product_name if carrefour_match else None,
            },
            'auchan': {
                'match': auchan_match,
                'price': auchan_price,
                'name': auchan_match.product_name if auchan_match else None,
            },
            'cheapest': cheapest,
        })

        if not carrefour_match or not carrefour_match.product_name:
            missing_carrefour.append(ingredient.nom)
        if not auchan_match or not auchan_match.product_name:
            missing_auchan.append(ingredient.nom)

    context = {
        'panier': panier,
        'comparison': comparison,
        'comparison_data': comparison_data,
        'missing_carrefour': missing_carrefour,
        'missing_auchan': missing_auchan,
        'savings': comparison.savings,
    }

    return render(request, 'supermarkets/comparison_results.html', context)
