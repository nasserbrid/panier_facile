from django.shortcuts import render, redirect
from authentication.forms import SignupForm
from django.contrib.auth import login
from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit
import json
from authentication.utils import OverpassAPI

# Create your views here.


"""
Vue pour la déconnexion personnalisée d'un utilisateur.
    
    Hérite de Django LogoutView et redirige vers la page de connexion
    après la déconnexion.
"""
class CustomLogoutView(LogoutView):
    next_page = 'login'
    

def signup_page(request):
    """
    Vue pour la page d'inscription d'un nouvel utilisateur.
    
    Cette vue gère l'affichage du formulaire d'inscription et la création
    de l'utilisateur lorsque le formulaire est soumis.

    Si le formulaire est valide, l'utilisateur est créé, connecté et redirigé
    vers la page définie par LOGIN_REDIRECT_URL dans settings.
"""
    
    form = SignupForm()
    
    if request.method == 'POST':
        form = SignupForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)
    
    return render(request, "authentication/signup.html", context={"form": form})


@login_required
def profile_page(request):
    """
    Vue pour la page de profil utilisateur avec géolocalisation.

    Affiche le profil de l'utilisateur connecté avec la possibilité
    de définir sa localisation (GPS ou adresse manuelle).
    """
    user = request.user

    # Récupérer les coordonnées existantes si disponibles
    location_data = None
    if user.location:
        location_data = {
            'latitude': user.location.y,
            'longitude': user.location.x,
            'address': user.address or ''
        }

    return render(request, "authentication/profile.html", {
        'user': user,
        'location_data': location_data
    })


@ratelimit(key='user', rate='10/m', method='POST')
@login_required
@require_http_methods(["POST"])
def save_location(request):
    """
    API endpoint pour sauvegarder la localisation de l'utilisateur.

    Accepte soit:
    - latitude et longitude (géolocalisation GPS)
    - address (adresse à géocoder)

    Retourne un JSON avec le statut de l'opération.
    Rate limit: 10 requêtes par minute par utilisateur.
    """
    # Vérifier si rate limit dépassé
    if getattr(request, 'limited', False):
        return JsonResponse({
            'success': False,
            'message': 'Trop de requêtes. Veuillez réessayer dans quelques instants.'
        }, status=429)

    try:
        data = json.loads(request.body)
        user = request.user

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        address = data.get('address', '')

        if latitude and longitude:
            # Validation des coordonnées GPS
            try:
                lat = float(latitude)
                lon = float(longitude)
            except (TypeError, ValueError):
                return JsonResponse({
                    'success': False,
                    'message': 'Coordonnées GPS invalides'
                }, status=400)

            if not (-90 <= lat <= 90):
                return JsonResponse({
                    'success': False,
                    'message': 'Latitude doit être entre -90 et 90'
                }, status=400)

            if not (-180 <= lon <= 180):
                return JsonResponse({
                    'success': False,
                    'message': 'Longitude doit être entre -180 et 180'
                }, status=400)
            # Importer Point uniquement si GeoDjango est disponible
            try:
                from django.contrib.gis.geos import Point
                user.location = Point(float(longitude), float(latitude), srid=4326)
                user.address = address
                user.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Localisation enregistrée avec succès',
                    'latitude': latitude,
                    'longitude': longitude
                })
            except ImportError:
                return JsonResponse({
                    'success': False,
                    'message': 'GeoDjango n\'est pas disponible (mode développement local)'
                }, status=400)
        else:
            return JsonResponse({
                'success': False,
                'message': 'Latitude et longitude requises'
            }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Format JSON invalide'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }, status=500)


@login_required
def nearby_stores(request):
    """
    Vue pour afficher les commerces à proximité de l'utilisateur.

    Nécessite que l'utilisateur ait défini sa localisation.
    """
    user = request.user

    if not user.location:
        return render(request, "authentication/nearby_stores.html", {
            'error': 'Vous devez d\'abord définir votre localisation dans votre profil.'
        })

    # Récupérer les paramètres de recherche
    radius = int(request.GET.get('radius', 2000))  # Par défaut 2km
    shop_type_filter = request.GET.get('type', 'all')

    # Types de commerces à rechercher
    shop_types = None
    if shop_type_filter != 'all':
        shop_types = [shop_type_filter]

    # Récupérer les commerces via Overpass API
    latitude = user.location.y
    longitude = user.location.x

    stores = OverpassAPI.find_nearby_stores(
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        shop_types=shop_types
    )

    # Statistiques
    stats = {
        'total': len(stores),
        'by_type': {}
    }
    for store in stores:
        store_type = store['type']
        stats['by_type'][store_type] = stats['by_type'].get(store_type, 0) + 1

    return render(request, "authentication/nearby_stores.html", {
        'stores': stores,
        'stats': stats,
        'user_location': {
            'latitude': latitude,
            'longitude': longitude,
            'address': user.address
        },
        'radius': radius,
        'shop_types': OverpassAPI.SHOP_TYPES,
        'selected_type': shop_type_filter
    })