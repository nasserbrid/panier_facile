"""
Vues pour la comparaison de prix entre supermarchés.

Flow utilisateur:
1. compare_prices - Page initiale avec géolocalisation
2. comparison_progress - Page de progression (polling AJAX)
3. comparison_results - Résultats avec tableau comparatif
"""
import json
import logging
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..models import Panier

logger = logging.getLogger(__name__)


@login_required
def compare_prices(request, panier_id):
    """
    Point d'entrée pour la comparaison de prix.

    GET: Affiche la page avec géolocalisation et liste des supermarchés
    POST: Lance la tâche Celery de comparaison et redirige vers la page de progression
    """
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

    # POST: Lancer la comparaison
    if request.method == 'POST':
        if not user_location:
            messages.error(request, "Veuillez d'abord renseigner votre localisation.")
            return redirect('compare_prices', panier_id=panier.id)

        # Lancer la tâche Celery
        from ..tasks import compare_supermarket_prices

        task = compare_supermarket_prices.delay(
            panier_id=panier.id,
            user_id=request.user.id,
            latitude=user_location['latitude'],
            longitude=user_location['longitude']
        )

        # Stocker le task_id en session
        request.session[f'comparison_task_{panier_id}'] = task.id

        messages.info(request, "Comparaison des prix en cours...")
        return redirect('comparison_progress', panier_id=panier.id, task_id=task.id)

    # GET: Afficher la page
    # Récupérer les magasins à proximité si localisation disponible
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

    context = {
        'panier': panier,
        'user_location': user_location,
        'nearby_stores': nearby_stores,
        'ingredients_count': sum(
            len([l for l in c.ingredient.split('\n') if l.strip()])
            for c in panier.courses.all() if c.ingredient
        ),
    }

    return render(request, 'supermarkets/compare_prices.html', context)


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
